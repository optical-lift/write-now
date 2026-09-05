#!/usr/bin/env python3
import hashlib,math
from collections import Counter,defaultdict
from mark_hebrew_glyph_annotation_competition_v19_io import canonical_json
START="<START>";OUTCOMES=("SAME_CURRENT","REPEAT_H1","REPEAT_H2","REPEAT_H3","REPEAT_H4","SEEN_EARLIER_SEGMENT","NEW_SEGMENT","END")
def glyph_segments(rows):
 for r in rows:
  seg=[];j=0
  for w in r["words"]:
   if w=="\n":
    if seg:yield f'{r["anonymousInscriptionId"]}:{j}',seg;j+=1;seg=[]
   else:seg.extend(list(w))
  if seg:yield f'{r["anonymousInscriptionId"]}:{j}',seg
def hist(seq,i):
 h=[START]*max(0,4-i)+seq[max(0,i-4):i];seen={};out=[]
 for x in h:
  if x==START:out.append(x)
  else:
   if x not in seen:seen[x]=f"A{len(seen)}"
   out.append(seen[x])
 return canonical_json(out)
def consequence(seq,i):
 if i+1>=len(seq):return "END"
 y=seq[i+1]
 if y==seq[i]:return "SAME_CURRENT"
 for k in range(1,5):
  if i-k>=0 and y==seq[i-k]:return f"REPEAT_H{k}"
 return "SEEN_EARLIER_SEGMENT" if y in seq[:max(0,i-4)] else "NEW_SEGMENT"
def event_rows(rows,kind):
 segs=((r["anonymousUnitId"],r["tokens"]) for r in rows) if kind=="hebrew" else glyph_segments(rows);out=[]
 for unit,seq in segs:
  for i in range(len(seq)):out.append({"unit":unit,"state":hist(seq,i),"operator":seq[i],"outcome":consequence(seq,i)})
 return out
def tables(ev):
 state=defaultdict(Counter);sop=defaultdict(Counter);sn=Counter();sopn=Counter();opn=Counter()
 for e in ev:
  S,o,y=e["state"],e["operator"],e["outcome"];state[S][y]+=1;sn[S]+=1;sop[(S,o)][y]+=1;sopn[(S,o)]+=1;opn[o]+=1
 return state,sop,sn,sopn,opn
def shared_states(he,ge,cfg):
 ht=tables(he);gt=tables(ge);mn=int(cfg["minimumSharedStateEventsPerCorpus"]);states=sorted(S for S in set(ht[2])&set(gt[2]) if ht[2][S]>=mn and gt[2][S]>=mn);HN=sum(ht[2][S] for S in states);GN=sum(gt[2][S] for S in states);raw={S:math.sqrt((ht[2][S]/max(1,HN))*(gt[2][S]/max(1,GN))) for S in states};z=sum(raw.values()) or 1.
 return states,{S:raw[S]/z for S in states},ht,gt
def eligible_ops(tab,states,cfg,allowed=None,max_ops=None):
 out=[]
 for op,n in tab[4].items():
  if allowed is not None and op not in allowed:continue
  cov=sum(tab[3][(S,op)]>=int(cfg["minimumOperatorStateEventsForCoverage"]) for S in states)
  if n>=int(cfg["minimumOperatorEvents"]) and cov>=int(cfg["minimumCoveredSharedStates"]):out.append((op,int(n),int(cov)))
 out.sort(key=lambda x:(-x[1],x[0]));return out[:max_ops] if max_ops else out
def build_fingerprints(tab,states,weights,ops,cfg):
 a=float(cfg["globalAdditiveAlpha"]);lam=float(cfg["backoffPseudoCount"]);clip=float(cfg["residualLog2Clip"]);out={}
 for op in ops:
  vals=[];ws=[]
  for S in states:
   b={y:(tab[0][S][y]+a)/(tab[2][S]+a*len(OUTCOMES)) for y in OUTCOMES};n=tab[3][(S,op)];q={y:(tab[1][(S,op)][y]+lam*b[y])/(n+lam) if n else b[y] for y in OUTCOMES}
   for y in OUTCOMES:vals.append(max(-clip,min(clip,math.log2(max(q[y],1e-300)/max(b[y],1e-300)))));ws.append(weights[S])
  out[op]={"vector":vals,"norm":math.sqrt(sum(w*x*x for w,x in zip(ws,vals)))}
 return out
def vector_weights(states,weights):return [weights[S] for S in states for _ in OUTCOMES]
def cosine(a,b,weights):
 na=math.sqrt(sum(w*x*x for w,x in zip(weights,a)));nb=math.sqrt(sum(w*y*y for w,y in zip(weights,b)));return sum(w*x*y for w,x,y in zip(weights,a,b))/(na*nb) if na and nb else 0.
def greedy_one_to_one(H,G,hfp,gfp,vw):
 edges=sorted(((cosine(hfp[h]["vector"],gfp[g]["vector"],vw),h,g) for h in H for g in G),key=lambda x:(-x[0],x[1],x[2]));uh=set();ug=set();pairs=[]
 for s,h,g in edges:
  if h in uh or g in ug:continue
  uh.add(h);ug.add(g);pairs.append({"hebrew":h,"glyph":g,"trainSimilarity":s})
  if len(uh)==len(H):break
 pairs.sort(key=lambda r:r["hebrew"]);return pairs
def song_labels(manifest):
 out=defaultdict(set)
 for lab,ids in manifest["groups"].items():
  for o in ids:out[o].add(lab)
 return {o:sorted(v) for o,v in out.items()}
