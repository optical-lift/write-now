#!/usr/bin/env python3
import math,random
from mark_hebrew_glyph_annotation_competition_v19_freeze_model import relation
from mark_hebrew_glyph_annotation_competition_v19_projector import cosine
from mark_hebrew_glyph_annotation_competition_v19_eval_pairing import eval_fp
def effect(panel,labels,name,sims):
 per=[];rel=[];un=[]
 for i,a in enumerate(panel):
  R=[];U=[]
  for b in panel:
   if b==a:continue
   v=sims[tuple(sorted((a,b)))];(R if relation(labels,a,b,name) else U).append(v)
  if R and U:per.append(sum(R)/len(R)-sum(U)/len(U))
  for b in panel[i+1:]:
   v=sims[(a,b)];(rel if relation(labels,a,b,name) else un).append(v)
 return {"operatorBalancedAdvantage":sum(per)/len(per) if per else 0.,"pairwiseAdvantage":((sum(rel)/len(rel) if rel else 0.)-(sum(un)/len(un) if un else 0.)),"balancedOperatorCount":len(per),"relatedPairCount":len(rel),"unrelatedPairCount":len(un)}
def permute_labels(panel,labels,name,rng):
 bundles=[labels.get(x) if name=="blind" else tuple(labels.get(x,[])) for x in panel];rng.shuffle(bundles);return {x:(b if name=="blind" else list(b)) for x,b in zip(panel,bundles)}
def map_lane(grows,freeze,protocol,lane,name):
 byh={p["hebrew"]:p for p in freeze["pairs"]};full=list(freeze["panelOperators"]);paired=[h for h in full if h in byh];G=[byh[h]["glyph"] for h in paired];gt,gfp,vw=eval_fp(grows,"glyph",G,freeze,protocol);ec=protocol["evaluation"];mn=int(ec["minimumEvaluationEventsPerMatchedOperator"]);panel=[h for h in paired if gt[4][byh[h]["glyph"]]>=mn];sims={}
 for i,a in enumerate(panel):
  for b in panel[i+1:]:sims[(a,b)]=cosine(gfp[byh[a]["glyph"]]["vector"],gfp[byh[b]["glyph"]]["vector"],vw)
 labels=freeze["annotationMaps"][name];obs=effect(panel,labels,name,sims);N=int(ec["permutationCount"]);rng=random.Random(ec["mapPermutationSeed"]+":"+name+":"+lane);null=[]
 if len(panel)>=2:
  for _ in range(N):null.append(effect(panel,permute_labels(full,labels,name,rng),name,sims)["operatorBalancedAdvantage"])
 x=obs["operatorBalancedAdvantage"]
 if null:
  p=(sum(v>=x-1e-15 for v in null)+1)/(len(null)+1);mu=sum(null)/len(null);sd=math.sqrt(sum((v-mu)**2 for v in null)/len(null));z=(x-mu)/sd if sd else 0.
 else:p=1.;mu=sd=z=0.
 frac=len(panel)/len(full) if full else 0.;g=ec["mapGatesPerLane"];passed=len(panel)>=int(ec["minimumEvaluableOperatorCount"]) and frac>=float(ec["minimumEvaluableOperatorFraction"]) and x>float(g["operatorBalancedRelatedAdvantageGreaterThan"]) and p<=float(g["annotationPermutationPAtMost"]) and obs["relatedPairCount"]>=int(g["minimumRelatedPairCount"]) and obs["unrelatedPairCount"]>=int(g["minimumUnrelatedPairCount"])
 return {"frozenOperators":len(full),"evaluableOperators":len(panel),"evaluableFraction":frac,**obs,"permutationP":p,"permutationZ":z,"nullMean":mu,"nullSd":sd,"pass":passed}
def adjudicate(pairing,maps):
 if not pairing["holdout"]["pass"] or not pairing["control"]["pass"]:return "SONG_COVERED_PAIRING_DOES_NOT_TRANSFER"
 wins=[n for n in ("song","conventional","blind") if maps[n]["holdout"]["pass"] and maps[n]["control"]["pass"]]
 if not wins:return "NO_ANNOTATION_MAP_TRANSFERS"
 if len(wins)>1:return "MULTIPLE_MAPSK_TRANSFER_WITHOUT_CLEAR_WINNER"
 return {"song":"SONG_FUNCTIONAL_MAP_PREDICTS_GLYPH_STRUCTURE","conventional":"CONVENTIONAL_MAP_PREDICTS_GLYPH_STRUCTURE","blind":"BLIND_HEBREW_STRUCTURE_SUFFICIENT"}[wins[0]]
