#!/usr/bin/env python3
from collections import defaultdict
from mark_hebrew_glyph_annotation_competition_v19_projector import *
def _dist(a,b,fp,vw):return 1.-cosine(fp[a]["vector"],fp[b]["vector"],vw)
def complete_linkage_labels(items,fp,vw,k):
 items=sorted(items)
 if not 1<=k<=len(items):raise ValueError(f"invalid complete-linkage k={k} for n={len(items)}")
 cl=[(x,) for x in items]
 while len(cl)>k:
  opts=[]
  for i in range(len(cl)):
   for j in range(i+1,len(cl)):
    merged=tuple(sorted(cl[i]+cl[j]));d=max(_dist(a,b,fp,vw) for a in cl[i] for b in cl[j]);opts.append((d,merged,i,j))
  _,merged,i,j=min(opts,key=lambda x:(x[0],x[1]));cl=[c for n,c in enumerate(cl) if n not in (i,j)]+[merged];cl.sort()
 return {x:f"C{n}" for n,c in enumerate(sorted(cl),1) for x in c}
def mean_silhouette(items,labels,fp,vw):
 groups=defaultdict(list)
 for x in items:groups[labels[x]].append(x)
 scores=[]
 for x in sorted(items):
  own=groups[labels[x]]
  if len(own)<=1:scores.append(0.);continue
  a=sum(_dist(x,y,fp,vw) for y in own if y!=x)/(len(own)-1);b=min(sum(_dist(x,y,fp,vw) for y in ys)/len(ys) for lab,ys in groups.items() if lab!=labels[x]);den=max(a,b);scores.append((b-a)/den if den else 0.)
 return sum(scores)/len(scores) if scores else 0.
def choose_blind_clustering(items,fp,vw,ks):
 cand=[]
 for k in sorted(set(map(int,ks))):
  if k<2 or k>len(items):continue
  labels=complete_linkage_labels(items,fp,vw,k);cand.append({"k":k,"meanSilhouette":mean_silhouette(items,labels,fp,vw),"labels":labels})
 if not cand:raise ValueError("no feasible blind-clustering K")
 win=max(cand,key=lambda r:(r["meanSilhouette"],-r["k"]));return win["labels"],{"k":win["k"],"meanSilhouette":win["meanSilhouette"],"candidates":[{"k":r["k"],"meanSilhouette":r["meanSilhouette"]} for r in cand]}
def relation(labels,a,b,name):return labels.get(a) is not None and labels.get(a)==labels.get(b) if name=="blind" else bool(set(labels.get(a,[]))&set(labels.get(b,[])))
def relation_counts(panel,labels,name):
 rel=un=0
 for i,a in enumerate(panel):
  for b in panel[i+1:]:
   if relation(labels,a,b,name):rel+=1
   else:un+=1
 return {"relatedPairs":rel,"unrelatedPairs":un}
def freeze_model(hrows,grows,conv,song,protocol):
 cfg=protocol["exactV15"]["training"];he=event_rows(hrows,"hebrew");ge=event_rows(grows,"glyph");states,weights,ht,gt=shared_states(he,ge,cfg);sl=song_labels(song);hr=eligible_ops(ht,states,cfg,allowed=set(sl));gr=eligible_ops(gt,states,cfg,max_ops=int(cfg["maximumGlyphOperators"]));H=[x[0] for x in hr];G=[x[0] for x in gr];hfp=build_fingerprints(ht,states,weights,H,cfg);gfp=build_fingerprints(gt,states,weights,G,cfg);floor=float(cfg["minimumFingerprintNorm"]);panel=sorted(x for x in H if hfp[x]["norm"]>=floor);G=sorted(x for x in G if gfp[x]["norm"]>=floor);vw=vector_weights(states,weights);pairs=greedy_one_to_one(panel,G,hfp,gfp,vw);mn=float(protocol["commonPanel"]["minimumTrainPairSimilarity"]);pairs=[p for p in pairs if p["trainSimilarity"]>=mn]
 songmap={x:sl.get(x,[]) for x in panel};conmap={x:sorted(conv.get(x,{}).get("families",[])) for x in panel}
 if len(panel)>=2:blind,meta=choose_blind_clustering(panel,hfp,vw,protocol["annotationMaps"]["blind"]["candidateK"])
 elif len(panel)==1:blind={panel[0]:"C1"};meta={"k":1,"meanSilhouette":0.,"candidates":[]}
 else:blind={};meta={"k":0,"meanSilhouette":0.,"candidates":[]}
 maps={"song":songmap,"conventional":conmap,"blind":blind};counts={n:relation_counts(panel,l,n) for n,l in maps.items()}
 return {"outcomes":list(OUTCOMES),"sharedStates":states,"sharedStateWeights":weights,"panelOperators":panel,"glyphOperators":G,"hebrewOperatorSupport":{x:int(ht[4][x]) for x in panel},"glyphOperatorSupport":{x:int(gt[4][x]) for x in G},"pairs":pairs,"annotationMaps":maps,"blindMetadata":meta,"relationCounts":counts,"trainEventCounts":{"hebrew":len(he),"glyph":len(ge)}}
