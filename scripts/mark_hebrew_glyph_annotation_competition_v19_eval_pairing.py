#!/usr/bin/env python3
import random
from mark_hebrew_glyph_annotation_competition_v19_projector import *
def eval_fp(rows,kind,ops,freeze,protocol):
 ev=event_rows(rows,kind);tab=tables(ev);cfg=protocol["exactV15"]["training"];fp=build_fingerprints(tab,freeze["sharedStates"],freeze["sharedStateWeights"],ops,cfg);return tab,fp,vector_weights(freeze["sharedStates"],freeze["sharedStateWeights"])
def pairing_lane(hrows,grows,freeze,protocol,lane):
 pairs=freeze["pairs"];H=[p["hebrew"] for p in pairs];G=[p["glyph"] for p in pairs];ht,hfp,vw=eval_fp(hrows,"hebrew",H,freeze,protocol);gt,gfp,_=eval_fp(grows,"glyph",G,freeze,protocol);ec=protocol["evaluation"];mn=int(ec["minimumEvaluationEventsPerMatchedOperator"]);ok=[p for p in pairs if ht[4][p["hebrew"]]>=mn and gt[4][p["glyph"]]>=mn]
 def sim(h,g):return cosine(hfp[h]["vector"],gfp[g]["vector"],vw)
 obs=[sim(p["hebrew"],p["glyph"]) for p in ok];mean=sum(obs)/len(obs) if obs else 0.;pool=[p["glyph"] for p in ok];ranks=[]
 for p in ok:
  actual=sim(p["hebrew"],p["glyph"]);scores=[sim(p["hebrew"],g) for g in pool];ranks.append((sum(x<=actual for x in scores)-1)/max(1,len(scores)-1))
 med=sorted(ranks)[len(ranks)//2] if ranks else 0.;N=int(ec["permutationCount"]);rng=random.Random(ec["pairingPermutationSeed"]+":"+lane);geq=0
 if ok:
  vals=[p["glyph"] for p in ok]
  for _ in range(N):
   sh=list(vals);rng.shuffle(sh);v=sum(sim(p["hebrew"],g) for p,g in zip(ok,sh))/len(ok);geq+=v>=mean-1e-15
  pv=(geq+1)/(N+1)
 else:pv=1.
 frac=len(ok)/len(pairs) if pairs else 0.;g=ec["pairingGatesPerLane"];passed=len(ok)>=int(ec["minimumEvaluableOperatorCount"]) and frac>=float(ec["minimumEvaluableOperatorFraction"]) and mean>float(g["meanSimilarityGreaterThan"]) and pv<=float(g["unstratifiedPermutationPAtMost"]) and med>=float(g["medianRankPercentileAtLeast"])
 return {"frozenPairs":len(pairs),"evaluablePairs":len(ok),"evaluableFraction":frac,"meanSimilarity":mean,"permutationP":pv,"medianRankPercentile":med,"pass":passed,"pairSimilarities":[{"hebrew":p["hebrew"],"glyph":p["glyph"],"similarity":s} for p,s in zip(ok,obs)]}
