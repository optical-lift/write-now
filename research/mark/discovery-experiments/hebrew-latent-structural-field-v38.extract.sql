-- V38 Hebrew-only latent structural field extractor
-- Reads no Masoretic table and no lemma/morph/Strong/translation fields.
-- Output: supported-state inventory, top-64 destination dimensions, and 5-NN graph.

with blocks as materialized (
  select distinct book, ((chapter-1)/5)::int block_index
  from draft.ot_canonical_tokens_stage
),
ranked_blocks as materialized (
  select book,block_index,
         row_number() over(order by md5('v38-hebrew-blind-holdout|'||book||':'||block_index),book,block_index) r
  from blocks
),
skeleton_types as materialized (
  select distinct regexp_replace(hebrew_surface,'[^\u05D0-\u05EA]','','g') skel
  from draft.ot_canonical_tokens_stage
),
chars as materialized (
  select s.skel,c.ch,c.pos,min(c.pos) over(partition by s.skel,c.ch) firstpos
  from skeleton_types s
  cross join lateral regexp_split_to_table(s.skel,'') with ordinality c(ch,pos)
),
ranked_chars as materialized (
  select skel,ch,pos,dense_rank() over(partition by skel order by firstpos) lab
  from chars
),
state_map as materialized (
  select s.skel,
         char_length(s.skel)::int len,
         string_agg(r.lab::text,'.' order by r.pos) eqpat,
         (right(s.skel,1) ~ '[ךםןףץ]') final_form
  from skeleton_types s
  join ranked_chars r using(skel)
  group by s.skel
),
tok as materialized (
  select t.id,t.book,((t.chapter-1)/5)::int block_index,(rb.r<=41) holdout,
         (sm.len::text||'|'||sm.eqpat||'|'||sm.final_form::text) raw_state
  from draft.ot_canonical_tokens_stage t
  join state_map sm
    on sm.skel=regexp_replace(t.hebrew_surface,'[^\u05D0-\u05EA]','','g')
  join ranked_blocks rb
    on rb.book=t.book and rb.block_index=((t.chapter-1)/5)::int
),
train_state_counts as materialized (
  select raw_state,count(*) n
  from tok where not holdout
  group by raw_state
),
supported as materialized (
  select raw_state,n from train_state_counts where n>=100
),
top64 as materialized (
  select raw_state,n,row_number() over(order by n desc,raw_state) rank
  from supported
  order by n desc,raw_state
  limit 64
),
dims as materialized (
  select raw_state d from top64
  union all select 'OTHER'
),
mapped as materialized (
  select id,book,block_index,holdout,
         case when s.raw_state is not null then tok.raw_state else 'OTHER' end src_state,
         case when d.raw_state is not null then tok.raw_state else 'OTHER' end dim_state
  from tok
  left join supported s using(raw_state)
  left join top64 d using(raw_state)
),
pairs as materialized (
  select a.src_state prev_src,a.dim_state prev_dim,
         b.src_state next_src,b.dim_state next_dim
  from mapped a
  join mapped b
    on b.id=a.id+1 and b.book=a.book
   and b.block_index=a.block_index and b.holdout=a.holdout
  where not a.holdout
),
out_counts as materialized (
  select prev_src node,next_dim d,count(*) n from pairs group by prev_src,next_dim
),
out_totals as materialized (
  select node,sum(n)::float8 n from out_counts group by node
),
in_counts as materialized (
  select next_src node,prev_dim d,count(*) n from pairs group by next_src,prev_dim
),
in_totals as materialized (
  select node,sum(n)::float8 n from in_counts group by node
),
nodes as materialized (
  select raw_state node from supported
),
probs as materialized (
  select n.node,d.d,
         (coalesce(o.n,0)+0.5)/(coalesce(ot.n,0)+0.5*65) p_out,
         (coalesce(i.n,0)+0.5)/(coalesce(it.n,0)+0.5*65) p_in
  from nodes n cross join dims d
  left join out_counts o on o.node=n.node and o.d=d.d
  left join out_totals ot on ot.node=n.node
  left join in_counts i on i.node=n.node and i.d=d.d
  left join in_totals it on it.node=n.node
),
distances as materialized (
  select a.node node_a,b.node node_b,
         0.5*sum(0.5*(a.p_out*ln(a.p_out/((a.p_out+b.p_out)/2.0))+
                      b.p_out*ln(b.p_out/((a.p_out+b.p_out)/2.0))))
       + 0.5*sum(0.5*(a.p_in*ln(a.p_in/((a.p_in+b.p_in)/2.0))+
                      b.p_in*ln(b.p_in/((a.p_in+b.p_in)/2.0)))) distance
  from probs a
  join probs b on a.d=b.d and a.node<>b.node
  group by a.node,b.node
),
knn as materialized (
  select node_a,node_b,distance,
         row_number() over(partition by node_a order by distance,node_b) neighbor_rank
  from distances
),
edges as materialized (
  select node_a,node_b,distance,neighbor_rank from knn where neighbor_rank<=5
)
select json_build_object(
  'supported_inventory_md5',
    (select md5(string_agg(raw_state||':'||n,E'\n' order by raw_state)) from supported),
  'top64_md5',
    (select md5(string_agg(rank||':'||raw_state||':'||n,E'\n' order by rank)) from top64),
  'graph_md5',
    (select md5(string_agg(node_a||'→'||node_b||':'||round(distance::numeric,12)::text,E'\n' order by node_a,distance,node_b)) from edges),
  'supported_states',
    (select json_agg(json_build_object('state',raw_state,'training_n',n) order by raw_state) from supported),
  'profile_dimensions',
    (select json_agg(raw_state order by rank) from top64),
  'graph_edges',
    (select json_agg(json_build_object('from',node_a,'to',node_b,'distance',distance,'rank',neighbor_rank) order by node_a,neighbor_rank) from edges)
) as v38_frozen_artifact;
