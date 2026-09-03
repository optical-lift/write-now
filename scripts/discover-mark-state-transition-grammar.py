#!/usr/bin/env python3
import hashlib, itertools, json, math, os, random
from collections import Counter, defaultdict
from pathlib import Path

field_dir = Path(os.environ.get("MARK_LOCAL_STATE_FIELD", "artifact-staging/local-state-field"))
parent_state_dir = Path(os.environ.get("MARK_PARENT_RELATIONAL_STATE", "artifact-staging/parent-state"))
protocol_path = Path(os.environ.get("MARK_TRANSITION_PROTOCOL", "research/mark/discovery-experiments/state-transition-grammar-v1.protocol.json"))
out_dir = Path(os.environ.get("MARK_TRANSITION_OUT", "artifacts/mark-state-transition-grammar-v1"))

def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
def canonical_bytes(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
def canonical_sha(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()
def mean(xs):
    return sum(xs)/len(xs) if xs else 0.0
def distance(a,b):
    return math.sqrt(sum((x-y)**2 for x,y in zip(a,b)))
def stdev(xs):
    if not xs: return 0.0
    m=mean(xs)
    return math.sqrt(mean([(x-m)**2 for x in xs]))
def contains(parent, child):
    pa=parent["width"]*parent["height"]; ca=child["width"]*child["height"]
    return pa>ca and parent["x"]<=child["x"] and parent["y"]<=child["y"] and parent["x"]+parent["width"]>=child["x"]+child["width"] and parent["y"]+parent["height"]>=child["y"]+child["height"]

protocol=load_json(protocol_path)
if protocol.get("schema")!="mark_state_transition_grammar_protocol_v1":
    raise RuntimeError("unexpected transition protocol")
field=load_json(field_dir/"local-state-field-discovery.json")
if field.get("schema")!="mark_local_state_field_discovery_v1":
    raise RuntimeError("unexpected local-state field")
if field.get("localStateFieldDiscoverySha256")!=protocol["parentEvidence"]["localStateFieldDiscoverySha256"]:
    raise RuntimeError("wrong frozen local-state parent")
if field.get("provenanceAvailableDuringDiscovery"):
    raise RuntimeError("parent field was not blind")

rows=[]
with (field_dir/"observation-local-states.jsonl").open(encoding="utf-8") as h:
    for line in h:
        if line.strip(): rows.append(json.loads(line))
if not rows: raise RuntimeError("empty local-state field")
by_id={r["observationId"]:r for r in rows}
by_source=defaultdict(list)
for r in rows: by_source[r["sourceGroupId"]].append(r)
state_ids=sorted(set(int(r["stateId"]) for r in rows))
if state_ids!=protocol["stateIds"]:
    raise RuntimeError(f"unexpected state ids {state_ids}")

# Physical direction is imposed only by strict containment: smallest larger containing region -> child.
parent={}
for source, items in by_source.items():
    for child in items:
        candidates=[p for p in items if p["observationId"]!=child["observationId"] and contains(p["region"],child["region"])]
        if candidates:
            p=min(candidates,key=lambda x:(x["region"]["width"]*x["region"]["height"],x["observationId"]))
            parent[child["observationId"]]=p["observationId"]
edges=sorted((p,c) for c,p in parent.items())
chains=sorted((parent[p],p,c) for c,p in parent.items() if p in parent)
states={r["observationId"]:int(r["stateId"]) for r in rows}
lanes={r["observationId"]:r["lane"] for r in rows}
sources={r["observationId"]:r["sourceGroupId"] for r in rows}

# Primary null preserves source, proposal scale, and deterministic area quartile.
quartile={}
for source,items in by_source.items():
    groups=defaultdict(list)
    for r in items: groups[r.get("proposalScale","")].append(r)
    for scale,group in groups.items():
        ordered=sorted(group,key=lambda r:(r["region"]["width"]*r["region"]["height"],r["observationId"]))
        n=len(ordered)
        for i,r in enumerate(ordered):
            quartile[r["observationId"]]=min(3,(i*4)//n)
strata=defaultdict(list)
for r in rows:
    strata[(r["sourceGroupId"],r.get("proposalScale",""),quartile[r["observationId"]])].append(r["observationId"])

edge_motifs=list(itertools.product(state_ids,repeat=2))
chain_motifs=list(itertools.product(state_ids,repeat=3))
lane_ids=["train","holdout","control"]

def count(assign):
    ec=Counter(); cc=Counter(); es=defaultdict(set); cs=defaultdict(set); el=defaultdict(Counter); cl=defaultdict(Counter)
    source_ec=defaultdict(Counter); source_cc=defaultdict(Counter)
    for a,b in edges:
        m=(assign[a],assign[b]); s=sources[b]; l=lanes[b]
        ec[m]+=1; es[m].add(s); el[m][l]+=1; source_ec[s][m]+=1
    for a,b,c in chains:
        m=(assign[a],assign[b],assign[c]); s=sources[c]; l=lanes[c]
        cc[m]+=1; cs[m].add(s); cl[m][l]+=1; source_cc[s][m]+=1
    return ec,cc,es,cs,el,cl,source_ec,source_cc

obs_ec,obs_cc,obs_es,obs_cs,obs_el,obs_cl,source_ec,source_cc=count(states)
iters=int(protocol["nullModel"]["iterations"])
null_ec={m:[] for m in edge_motifs}; null_cc={m:[] for m in chain_motifs}
null_el={m:{l:[] for l in lane_ids} for m in edge_motifs}; null_cl={m:{l:[] for l in lane_ids} for m in chain_motifs}
for iteration in range(iters):
    assign=dict(states)
    for key,ids in strata.items():
        labels=[states[x] for x in ids]
        seed=int(hashlib.sha256(f"mark-state-transition|{iteration}|{key}".encode()).hexdigest()[:16],16)
        rnd=random.Random(seed); rnd.shuffle(labels)
        for oid,label in zip(ids,labels): assign[oid]=label
    ec,cc,_,_,el,cl,_,_=count(assign)
    for m in edge_motifs:
        null_ec[m].append(ec[m])
        for l in lane_ids: null_el[m][l].append(el[m][l])
    for m in chain_motifs:
        null_cc[m].append(cc[m])
        for l in lane_ids: null_cl[m][l].append(cl[m][l])

def metric(obs, vals):
    mu=mean(vals); direction="enrichment" if obs>mu else "suppression" if obs<mu else "neutral"
    beyond=obs>max(vals) if direction=="enrichment" else obs<min(vals) if direction=="suppression" else False
    sd=stdev(vals)
    return {"observed":obs,"nullMean":mu,"nullStandardDeviation":sd,"nullMinimum":min(vals),"nullMaximum":max(vals),
            "signedLift":obs-mu,"standardizedDeviation":(obs-mu)/(sd or 1.0),"relativeLift":(obs-mu)/(mu+1.0),"direction":direction,
            "observedBeyondAllNulls":beyond,
            "nullAtLeastAsExtreme":sum((v>=obs if direction=="enrichment" else v<=obs if direction=="suppression" else True) for v in vals)}
def lane_metrics(m, observed, null):
    out={}
    for l in lane_ids: out[l]=metric(observed[m][l],null[m][l])
    return out
def same_nonzero_sign(ms):
    signs=[]
    for l in lane_ids:
        x=ms[l]["signedLift"]; signs.append(1 if x>0 else -1 if x<0 else 0)
    return 0 not in signs and len(set(signs))==1

edge_rows=[]
for m in edge_motifs:
    x=metric(obs_ec[m],null_ec[m]); lm=lane_metrics(m,obs_el,null_el)
    edge_rows.append({"schema":"mark_state_transition_edge_v1","motif":"->".join(map(str,m)),"fromState":m[0],"toState":m[1],
                      **x,"distinctSourceSupport":len(obs_es[m]),"laneObservedCounts":{l:obs_el[m][l] for l in lane_ids},
                      "laneMetrics":lm,"sameDirectionAcrossAllLanes":same_nonzero_sign(lm)})
chain_rows=[]
for m in chain_motifs:
    x=metric(obs_cc[m],null_cc[m]); lm=lane_metrics(m,obs_cl,null_cl)
    chain_rows.append({"schema":"mark_state_transition_program_v1","motif":"->".join(map(str,m)),"states":list(m),
                       **x,"distinctSourceSupport":len(obs_cs[m]),"laneObservedCounts":{l:obs_cl[m][l] for l in lane_ids},
                       "laneMetrics":lm,"sameDirectionAcrossAllLanes":same_nonzero_sign(lm)})
rank_key=lambda r:(-int(r["observedBeyondAllNulls"]),-int(r["sameDirectionAcrossAllLanes"]),-abs(r["standardizedDeviation"]),-r["distinctSourceSupport"],r["motif"])
edge_rows.sort(key=rank_key); chain_rows.sort(key=rank_key)
for i,r in enumerate(edge_rows,1): r["transitionRank"]=i
for i,r in enumerate(chain_rows,1): r["programRank"]=i

# Theory-specific but separately reported: once State 2 resolves into 1 or 3, does it persist rather than return?
def c3(m): return obs_cc[tuple(m)]
commit_obs=c3((2,1,1))+c3((2,3,3))
return_obs=c3((2,1,2))+c3((2,3,2))
commit_null=[]; return_null=[]
for i in range(iters):
    commit_null.append(null_cc[(2,1,1)][i]+null_cc[(2,3,3)][i])
    return_null.append(null_cc[(2,1,2)][i]+null_cc[(2,3,2)][i])
hysteresis={
  "schema":"mark_state_commitment_hysteresis_v1",
  "commitmentPrograms":["2->1->1","2->3->3"],"returnPrograms":["2->1->2","2->3->2"],
  "commitment":metric(commit_obs,commit_null),"return":metric(return_obs,return_null),
  "observedCommitmentToReturnRatio":commit_obs/(return_obs+1.0),
  "nullMeanCommitmentToReturnRatio":mean([a/(b+1.0) for a,b in zip(commit_null,return_null)])
}

# Source transition vectors; ask whether prior whole-source regimes are recoverable from dynamics.
profile_rows=[]; profiles={}
for source in sorted(set(source_ec)|set(source_cc)):
    ec=source_ec[source]; cc=source_cc[source]; et=sum(ec.values()); ct=sum(cc.values())
    if et<2: continue
    vec=[ec[m]/et for m in edge_motifs]+[(cc[m]/ct if ct else 0.0) for m in chain_motifs]
    profiles[source]=vec
    profile_rows.append({"schema":"mark_source_transition_profile_v1","sourceGroupId":source,"lane":by_source[source][0]["lane"],
                         "containmentEdges":et,"containmentChains":ct,
                         "edgeCounts":{"->".join(map(str,m)):ec[m] for m in edge_motifs},
                         "programCounts":{"->".join(map(str,m)):cc[m] for m in chain_motifs},
                         "edgeProportions":{"->".join(map(str,m)):ec[m]/et for m in edge_motifs},
                         "programProportions":{"->".join(map(str,m)):(cc[m]/ct if ct else 0.0) for m in chain_motifs},
                         "commitmentCount":cc[(2,1,1)]+cc[(2,3,3)],
                         "returnToState2Count":cc[(2,1,2)]+cc[(2,3,2)]})
regime={}
regime_path=parent_state_dir/"source-construction-regimes.jsonl"
if regime_path.exists():
    with regime_path.open(encoding="utf-8") as h:
        for line in h:
            if line.strip():
                r=json.loads(line); regime[r["sourceGroupId"]]=int(r["regimeId"])
common=sorted(set(profiles)&set(regime))
regime_test=None
if common:
    rids=sorted(set(regime[s] for s in common)); correct=0
    for source in common:
        cents={}
        for rid in rids:
            members=[s for s in common if s!=source and regime[s]==rid]
            cents[rid]=[mean([profiles[s][d] for s in members]) for d in range(len(profiles[source]))]
        pred=min(rids,key=lambda rid:(distance(profiles[source],cents[rid]),rid))
        correct+=int(pred==regime[source])
    regime_test={"sourcesCompared":len(common),"leaveOneOutNearestTransitionCentroidAccuracy":correct/len(common)}

twin_test=None; twins_path=parent_state_dir/"structural-twins.jsonl"
if twins_path.exists():
    twins=[]
    with twins_path.open(encoding="utf-8") as h:
        for line in h:
            if line.strip(): twins.append(json.loads(line))
    td=[]
    for t in twins:
        a,b=t["leftSourceGroupId"],t["rightSourceGroupId"]
        if a in profiles and b in profiles: td.append(distance(profiles[a],profiles[b]))
    srcs=sorted(profiles); bg=[]
    lanes_by_source={s:by_source[s][0]["lane"] for s in profiles}
    for i,a in enumerate(srcs):
        for b in srcs[i+1:]:
            if lanes_by_source[a]!=lanes_by_source[b]: bg.append(distance(profiles[a],profiles[b]))
    if td and bg:
        med=sorted(td)[len(td)//2]
        twin_test={"frozenTwinsWithTransitionProfiles":len(td),"medianTwinTransitionDistance":med,
                   "backgroundCrossLanePairs":len(bg),"backgroundMedianTransitionDistance":sorted(bg)[len(bg)//2],
                   "medianTwinDistancePercentile":sum(x<=med for x in bg)/len(bg)}

out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/"transition-edges.json").write_text(json.dumps(edge_rows,indent=2)+"\n")
(out_dir/"transition-programs.json").write_text(json.dumps(chain_rows,indent=2)+"\n")
with (out_dir/"source-transition-profiles.jsonl").open("w",encoding="utf-8") as h:
    for r in profile_rows: h.write(json.dumps(r,separators=(",",":"))+"\n")
core={
 "schema":"mark_state_transition_grammar_discovery_v1","experimentId":protocol["experimentId"],
 "parentLocalStateFieldDiscoverySha256":field["localStateFieldDiscoverySha256"],
 "provenanceAvailableDuringDiscovery":False,
 "directionBasis":"smallest strictly larger wholly-containing observation region -> contained observation region",
 "primaryNull":"shuffle state labels within source + proposalScale + deterministic within-scale region-area quartile; geometry and lane fixed",
 "stateIds":state_ids,"observations":len(rows),"containmentEdges":len(edges),"containmentChains":len(chains),
 "transitionEdges":edge_rows,"transitionPrograms":chain_rows,"commitmentHysteresis":hysteresis,
 "sourceTransitionDynamics":{"profiles":len(profiles),"sourceRegimeRecovery":regime_test,"structuralTwinDepth":twin_test},
 "contract":{"allNineStateEdgesRetained":True,"allTwentySevenLengthThreeProgramsRetained":True,
             "positiveAndNegativeDeviationsTreatedSymmetrically":True,"provenanceUnavailableUntilFreeze":True,
             "geometryPreservedByPrimaryNull":True,"sourceScaleAndAreaStrataPreservedByPrimaryNull":True,
             "theoryGeneratingExperiment":True}
}
sha=canonical_sha(core); packet={**core,"stateTransitionGrammarDiscoverySha256":sha}
(out_dir/"state-transition-grammar-discovery.json").write_text(json.dumps(packet,indent=2)+"\n")
(out_dir/"summary.txt").write_text("\n".join([
 f"state_transition_grammar_sha256={sha}",
 f"containment_edges={len(edges)}",
 f"containment_chains={len(chains)}",
 f"top_edge={edge_rows[0]['motif']} {edge_rows[0]['direction']} standardized_deviation={edge_rows[0]['standardizedDeviation']}",
 f"top_program={chain_rows[0]['motif']} {chain_rows[0]['direction']} standardized_deviation={chain_rows[0]['standardizedDeviation']}",
 f"commitment_to_return_ratio={hysteresis['observedCommitmentToReturnRatio']}",
 f"null_commitment_to_return_ratio={hysteresis['nullMeanCommitmentToReturnRatio']}",
 f"source_regime_from_transition_accuracy={regime_test['leaveOneOutNearestTransitionCentroidAccuracy'] if regime_test else 'NA'}",
 f"twin_transition_distance_percentile={twin_test['medianTwinDistancePercentile'] if twin_test else 'NA'}"
])+"\n")
print(json.dumps(packet,indent=2))
