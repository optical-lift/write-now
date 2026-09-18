#!/usr/bin/env python3
"""No-refit validation for the frozen V46 R3 K=5 anonymous regime atlas."""
from __future__ import annotations
import argparse, hashlib, json, math
from collections import Counter
from pathlib import Path
from typing import Any
import numpy as np

DISCOVERY_SHA="0d45b335f8b468bed999d2455b4385b32bb742d7f1c7cf542a54b147ac976caf"
VALIDATION_SHA="915a156ae27b9bc1d1539246c2ef554bf5e82d1da56c905c9e3fa934f3d13562"
MODEL_SHA="5a0a430f8e127f46f31b207fd0be554d8cf622d11550dcb4b0987a5bd1705a5a"
EXPECTED_VALIDATION_ROWS=4372
EXPECTED_VALIDATION_SOURCES=137

FEATURES=[
"mean_degree","component_per_1k_skeleton","cycle_per_1k_skeleton",
"endpoint_per_1k_skeleton","junction_per_1k_skeleton",
"topology_type_token","topology_norm_entropy","topology_top_fraction","topology_simpson","topology_repeated_fraction",
"critical_type_token","critical_norm_entropy","critical_top_fraction","critical_simpson","critical_repeated_fraction",
"path_count_per_1k_skeleton",
]+[f"degree_p{i}" for i in range(9)]+[
"pathbin_1","pathbin_2_3","pathbin_4_7","pathbin_8_15","pathbin_16_31","pathbin_32_63","pathbin_64_plus"
]

def sha(path:Path)->str:
 h=hashlib.sha256()
 with path.open("rb") as f:
  for c in iter(lambda:f.read(1024*1024),b""): h.update(c)
 return h.hexdigest()

def ratio(n,d): return float(n/d) if d else 0.0

def row_features(row:dict[str,Any])->dict[str,float]:
 g=row["graphMorphology"]; e=row["v46LocalTopologyEcology"]; c=e["critical"]; p=row["degree2PathSegments"]; degree=g["degreeHistogram"]
 sk=float(g["skeletonPixelCount"]); degree_total=sum(float(degree[str(i)]) for i in range(9)); path_count=float(p["count"]); lb=p["lengthBins"]; length_total=sum(float(v) for v in lb.values())
 out={
  "mean_degree":float(g["meanSkeletonDegree"]),
  "component_per_1k_skeleton":1000.0*ratio(float(g["connectedComponents"]),sk),
  "cycle_per_1k_skeleton":1000.0*ratio(float(g["cycleRank8"]),sk),
  "endpoint_per_1k_skeleton":1000.0*ratio(float(g["endpointPixels"]),sk),
  "junction_per_1k_skeleton":1000.0*ratio(float(g["junctionPixels"]),sk),
  "topology_type_token":float(e["typeTokenRatio"]),
  "topology_norm_entropy":float(e["normalizedEntropy"]),
  "topology_top_fraction":float(e["topTypeFraction"]),
  "topology_simpson":float(e["simpsonConcentration"]),
  "topology_repeated_fraction":float(e["repeatedTokenFraction"]),
  "critical_type_token":float(c["typeTokenRatio"]),
  "critical_norm_entropy":float(c["normalizedEntropy"]),
  "critical_top_fraction":float(c["topTypeFraction"]),
  "critical_simpson":float(c["simpsonConcentration"]),
  "critical_repeated_fraction":float(c["repeatedTokenFraction"]),
  "path_count_per_1k_skeleton":1000.0*ratio(path_count,sk),
 }
 for i in range(9): out[f"degree_p{i}"]=ratio(float(degree[str(i)]),degree_total)
 for name in ["1","2_3","4_7","8_15","16_31","32_63","64_plus"]: out[f"pathbin_{name}"]=ratio(float(lb[name]),length_total)
 return out

def load(path:Path, lane:str):
 rows=[]; sources=[]; ids=[]
 with path.open() as f:
  for line in f:
   r=json.loads(line)
   if r["schema"]!="mark_structural_feature_row_v46_v1" or r["v46Lane"]!=lane: raise RuntimeError("wrong lane/schema")
   feat=row_features(r)
   rows.append([feat[n] for n in FEATURES]); sources.append(r["sourceGroupId"]); ids.append(r["observationId"])
 X=np.asarray(rows,dtype=np.float64)
 if not np.isfinite(X).all(): raise RuntimeError("non-finite features")
 return X,np.asarray(sources),np.asarray(ids)

def transform(X,model):
 mean=np.asarray(model["scaler"]["mean"],dtype=float); scale=np.asarray(model["scaler"]["scale"],dtype=float)
 pmean=np.asarray(model["pca"]["mean"],dtype=float); comps=np.asarray(model["pca"]["components"],dtype=float)
 return ((X-mean)/scale-pmean)@comps.T

def assign(P,model):
 centers=np.asarray(model["kmeans"]["centers"],dtype=float)
 d=((P[:,None,:]-centers[None,:,:])**2).sum(axis=2)
 raw=d.argmin(axis=1); first=d[np.arange(len(P)),raw]
 second=np.partition(d,1,axis=1)[:,1]
 mapping={int(k):v for k,v in model["labelIdentity"]["rawToRegime"].items()}
 regime=np.asarray([mapping[int(x)] for x in raw])
 margin=(second-first)/np.maximum(second,1e-12)
 return raw,regime,first,margin

def js_bits(p,q):
 p=np.asarray(p,dtype=float);q=np.asarray(q,dtype=float);p=p/p.sum();q=q/q.sum();m=(p+q)/2
 def kl(a,b):
  mask=a>0
  return float((a[mask]*np.log2(a[mask]/b[mask])).sum())
 return .5*kl(p,m)+.5*kl(q,m)

def main():
 ap=argparse.ArgumentParser(); ap.add_argument("--discovery",type=Path,required=True);ap.add_argument("--validation",type=Path,required=True);ap.add_argument("--model",type=Path,required=True);ap.add_argument("--out",type=Path,required=True);args=ap.parse_args()
 if sha(args.discovery)!=DISCOVERY_SHA or sha(args.validation)!=VALIDATION_SHA or sha(args.model)!=MODEL_SHA: raise RuntimeError("frozen input hash drift")
 model=json.load(args.model.open())
 if model["selection"]!="R3_TOPOLOGY_ECOLOGY:K5" or model["featureNames"]!=FEATURES: raise RuntimeError("model definition drift")
 Xd,sd,idd=load(args.discovery,"discovery"); Xv,sv,idv=load(args.validation,"validation")
 if len(idv)!=EXPECTED_VALIDATION_ROWS or len(set(sv.tolist()))!=EXPECTED_VALIDATION_SOURCES: raise RuntimeError("validation inventory drift")
 Pd=transform(Xd,model); Pv=transform(Xv,model)
 _,rd,dd,md=assign(Pd,model); _,rv,dv,mv=assign(Pv,model)
 regimes=[f"RG-{i:03d}" for i in range(1,6)]
 radii={}; discovery_counts=[]; validation_counts=[]; rows=[]; criteria_regime=True
 for rg in regimes:
  dx=dd[rd==rg]; vx=dv[rv==rg]; vs=sv[rv==rg]
  if len(dx)==0 or len(vx)==0:
   radius=float(np.quantile(dx,.99)) if len(dx) else 0.0; ind=0.0
  else:
   radius=float(np.quantile(dx,.99)); ind=float((vx<=radius).mean())
  radii[rg]=radius; discovery_counts.append(int((rd==rg).sum())); validation_counts.append(int((rv==rg).sum()))
  sources=int(len(set(vs.tolist())))
  rows.append({"regimeId":rg,"discoveryObservations":int((rd==rg).sum()),"validationObservations":int((rv==rg).sum()),"validationFraction":float((rv==rg).mean()),"distinctValidationSources":sources,"discoveryQ99SquaredDistance":radius,"validationInDistributionFraction":ind,"validationMedianSquaredDistance":float(np.median(vx)) if len(vx) else None,"validationP95SquaredDistance":float(np.quantile(vx,.95)) if len(vx) else None,"validationMedianCentroidMargin":float(np.median(mv[rv==rg])) if len(vx) else None})
  criteria_regime &= ind>=.80 and sources>=20 and len(vx)>0
 in_dist=np.asarray([dv[i]<=radii[rv[i]] for i in range(len(rv))])
 overall=float(in_dist.mean()); js=js_bits(discovery_counts,validation_counts)
 passed=bool(overall>=.90 and criteria_regime and js<=.10)
 out={"schema":"mark_structural_regime_validation_v46_v1","experimentId":"mark:structural-regime-atlas:v46","modelSha256":MODEL_SHA,"discoveryFeatureSha256":DISCOVERY_SHA,"validationFeatureSha256":VALIDATION_SHA,"assignmentRule":"frozen discovery scaler -> frozen discovery PCA -> nearest frozen K=5 centroid","supportRule":"assigned-regime discovery-only 99th percentile squared centroid distance","regimes":rows,"overallValidationInDistributionFraction":overall,"occupancyJensenShannonBits":js,"overallMedianCentroidMargin":float(np.median(mv)),"criteria":{"overallInDistributionAtLeast":.90,"eachRegimeInDistributionAtLeast":.80,"eachRegimeDistinctSourcesAtLeast":20,"occupancyJensenShannonBitsAtMost":.10,"everyRegimePresent":True},"status":"VALIDATION_SUPPORTED" if passed else "VALIDATION_RESIDUAL","validationSupported":passed,"refitPerformed":False,"provenanceOpened":False,"confirmationOpened":False}
 args.out.mkdir(parents=True,exist_ok=True)
 (args.out/"validation-result.json").write_text(json.dumps(out,indent=2)+"\n")
 with (args.out/"validation-assignments.jsonl").open("w") as f:
  for oid,src,rg,dist,inside,margin in zip(idv,sv,rv,dv,in_dist,mv):
   f.write(json.dumps({"observationId":str(oid),"sourceGroupId":str(src),"regimeId":str(rg),"squaredCentroidDistance":float(dist),"inDiscoveryQ99Support":bool(inside),"centroidMargin":float(margin)},separators=(",",":"))+"\n")
 print(json.dumps(out,indent=2))
if __name__=="__main__": main()
