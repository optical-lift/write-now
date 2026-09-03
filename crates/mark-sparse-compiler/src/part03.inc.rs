#[derive(Clone)]
struct Cluster {
    label: u32,
    kind: &'static str,
    pixels: Vec<usize>,
    cx: f64,
    cy: f64,
}

fn critical_clusters(skeleton: &[u8], w: usize, h: usize) -> (Vec<u32>, Vec<Cluster>) {
    let mut kind = vec![0u8; skeleton.len()];
    for i in 0..skeleton.len() {
        if skeleton[i] == 0 { continue; }
        let d=degree8(skeleton,i,w,h);
        if d<=1 { kind[i]=1; } else if d>=3 { kind[i]=2; }
    }
    let mut labels=vec![0u32;skeleton.len()]; let mut queue=vec![0usize;skeleton.len()]; let mut clusters=Vec::new();
    for start in 0..skeleton.len() {
        if kind[start]==0 || labels[start]!=0 { continue; }
        let label=clusters.len() as u32+1; let target_kind=kind[start]; let mut head=0usize; let mut tail=0usize;
        queue[tail]=start; tail+=1; labels[start]=label; let mut members=Vec::new(); let mut sx=0u64; let mut sy=0u64;
        while head<tail {
            let cur=queue[head]; head+=1; members.push(cur); sx+=(cur%w) as u64; sy+=(cur/w) as u64;
            for d in 0..8 { if let Some(ni)=neighbor_index(cur,d,w,h) { if labels[ni]==0 && kind[ni]==target_kind { labels[ni]=label; queue[tail]=ni; tail+=1; } } }
        }
        let n=members.len().max(1) as f64;
        clusters.push(Cluster { label, kind: if target_kind==1 {"ENDPOINT"} else {"JUNCTION"}, pixels:members, cx:sx as f64/n, cy:sy as f64/n });
    }
    (labels,clusters)
}

fn inverse_dir(d:usize)->usize { [7,6,5,4,3,2,1,0][d] }

fn trace_center_arms(skeleton:&[u8],labels:&[u32],clusters:&[Cluster],w:usize,h:usize)->HashMap<u32,Vec<String>> {
    let mut visited=vec![0u8;skeleton.len()]; let mut arms:HashMap<u32,Vec<String>>=HashMap::new();
    let kind_by_label:HashMap<u32,&'static str>=clusters.iter().map(|c|(c.label,c.kind)).collect();
    fn mark_edge(visited:&mut [u8],a:usize,d:usize,b:usize){ visited[a]|=1u8<<d; visited[b]|=1u8<<inverse_dir(d); }
    for cluster in clusters {
        for &p in &cluster.pixels {
            for d in 0..8 {
                let Some(ni)=neighbor_index(p,d,w,h) else {continue;};
                if skeleton[ni]==0 || labels[ni]==cluster.label || visited[p]&(1u8<<d)!=0 {continue;}
                mark_edge(&mut visited,p,d,ni); let mut prev=p; let mut cur=ni; let mut target=None::<u32>; let mut unresolved=false; let mut guard=0usize;
                loop {
                    guard+=1; if guard>skeleton.len()+4 { unresolved=true; break; }
                    let owner=labels[cur]; if owner!=0 && owner!=cluster.label { target=Some(owner); break; }
                    let x=cur%w; let y=cur/w; if x==0 || y==0 || x+1==w || y+1==h { unresolved=true; break; }
                    let mut next=None;
                    for nd in 0..8 {
                        let Some(candidate)=neighbor_index(cur,nd,w,h) else {continue;};
                        if candidate==prev || skeleton[candidate]==0 || visited[cur]&(1u8<<nd)!=0 {continue;}
                        next=Some((candidate,nd)); break;
                    }
                    let Some((candidate,nd))=next else { unresolved=true; break; };
                    mark_edge(&mut visited,cur,nd,candidate); prev=cur; cur=candidate;
                }
                if let Some(target_label)=target {
                    let target_kind=kind_by_label.get(&target_label).copied().unwrap_or("CRITICAL");
                    arms.entry(cluster.label).or_default().push(format!("PATH_TO_{target_kind}"));
                    if target_label!=cluster.label { arms.entry(target_label).or_default().push(format!("PATH_TO_{}",cluster.kind)); }
                } else if unresolved { arms.entry(cluster.label).or_default().push("UNRESOLVED".into()); }
            }
        }
    }
    arms
}

fn point_in_core(cluster:&Cluster,tile:Tile)->bool {
    let x=cluster.cx; let y=cluster.cy; let left=(tile.core_x-tile.ext_x) as f64; let top=(tile.core_y-tile.ext_y) as f64;
    x>=left && y>=top && x<left+tile.core_w as f64 && y<top+tile.core_h as f64
}

fn emit_continuation_stubs(ledger:&mut ChunkedLedger,skeleton:&[u8],observation:&Observation,tile:Tile,w:usize,h:usize)->Result<u64>{
    let core_left=(tile.core_x-tile.ext_x) as usize; let core_top=(tile.core_y-tile.ext_y) as usize;
    let core_right=core_left+tile.core_w as usize; let core_bottom=core_top+tile.core_h as usize; let mut count=0u64;
    for y in core_top..core_bottom { for x in core_left..core_right {
        let i=y*w+x; if skeleton[i]==0 {continue;}
        for d in 0..8 {
            let Some(j)=neighbor_index(i,d,w,h) else {continue;}; if skeleton[j]==0 {continue;}
            let nx=j%w; let ny=j/w; let neighbor_in_core=nx>=core_left&&nx<core_right&&ny>=core_top&&ny<core_bottom; if neighbor_in_core {continue;}
            let gx1=observation.region.x+tile.ext_x+x as u32; let gy1=observation.region.y+tile.ext_y+y as u32;
            let gx2=observation.region.x+tile.ext_x+nx as u32; let gy2=observation.region.y+tile.ext_y+ny as u32;
            if gx2>=observation.region.x+observation.region.width || gy2>=observation.region.y+observation.region.height {continue;}
            let a=(gx1,gy1); let b=(gx2,gy2); if a>=b {continue;}
            let stitch_key=sha256_hex(format!("{}|{}|{},{}|{},{}",observation.source_group_id,observation.id,a.0,a.1,b.0,b.1).as_bytes());
            ledger.write_json(&json!({"schema":"mark_sparse_event_v1","sourceGroupId":observation.source_group_id,"observationId":observation.id,"lane":observation.lane,"kind":"CONTINUATION_STUB","stitchKey":stitch_key,"a":{"x":a.0,"y":a.1},"b":{"x":b.0,"y":b.1}}))?;
            count+=1;
        }
    }}
    Ok(count)
}
