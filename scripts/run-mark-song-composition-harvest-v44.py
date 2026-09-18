#!/usr/bin/env python3
"""Execute Mark V44 Phase A without opening Song semantics.

This runner intentionally reuses the frozen V9 anonymous operator engine as a
narrow measurement carrier. It adds only V44 custody, a topology-only
surface-invariance rerun, physical witness provenance, and candidate-accounting.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REF = ROOT / "scripts" / "mark-v44"
PRIMARY_PROTOCOL = ROOT / "research" / "mark" / "discovery-experiments" / "song-composition-harvest-v44.operator-reference.v9.json"
TOPOLOGY_PROTOCOL = ROOT / "research" / "mark" / "discovery-experiments" / "song-composition-harvest-v44.operator-reference-topology.v9.json"
sys.path.insert(0, str(REF))
import mark_operator_algebra_v9_core as core

def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def sha_file(path):
    h=hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda:f.read(1<<20),b""):
            h.update(block)
    return h.hexdigest()

def canonical_sha(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode("utf-8")).hexdigest()

def git_blob_sha1(path):
    data=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode("ascii")+b"\0"+data).hexdigest()

def run_cmd(script, env):
    subprocess.run([sys.executable, str(script)], check=True, env={**os.environ, **env})

def copy_lane(src, dst, name):
    dst.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src/name, dst/name)

def run_engine(tag, protocol, split_dir, work):
    freeze_dir=work/tag/"freeze"; result_dir=work/tag/"result"
    freeze_dir.mkdir(parents=True,exist_ok=True); result_dir.mkdir(parents=True,exist_ok=True)
    common={
        "MARK_V9_PROTOCOL":str(protocol),
        "MARK_V9_SPLIT_MANIFEST":str(split_dir/"split-manifest.json"),
        "MARK_V9_TRAIN":str(split_dir/"train.jsonl"),
        "MARK_V9_FREEZE":str(freeze_dir),
    }
    run_cmd(REF/"induce-mark-operator-algebra-v9.py",common)
    freeze_file=freeze_dir/"operator-algebra-freeze.json"
    freeze_bytes_sha=sha_file(freeze_file)
    eval_env={
        **common,
        "MARK_V9_FREEZE_FILE":str(freeze_file),
        "MARK_V9_HOLDOUT":str(split_dir/"holdout.jsonl"),
        "MARK_V9_CONTROL":str(split_dir/"control.jsonl"),
        "MARK_V9_OUT":str(result_dir),
    }
    run_cmd(REF/"evaluate-mark-operator-algebra-v9.py",eval_env)
    result_file=result_dir/"operator-composition-algebra.json"
    return {
        "freeze":load(freeze_file),
        "result":load(result_file),
        "freeze_file_sha256":freeze_bytes_sha,
        "result_file_sha256":sha_file(result_file),
    }

def iter_paths(graph, cfg):
    for v in sorted(graph["adjacency"]):
        for u in sorted(graph["adjacency"][v]):
            for w in sorted(graph["adjacency"][v]):
                if u==w:
                    continue
                A=core.operator_occurrence(graph,u,v,w,cfg)
                for x in sorted(graph["adjacency"].get(w,{})):
                    if x in (u,v,w):
                        continue
                    B=core.operator_occurrence(graph,v,w,x,cfg)
                    yield u,v,w,x,A,B

def prov(row,u,v,w,x,A,B,i,o):
    return {
        "source_group_id":row["sourceGroupId"],
        "observation_id":row["observationId"],
        "lane":row["lane"],
        "region":row["region"],
        "center_event_ids":[u,v,w,x],
        "operator_a":A["operatorId"],
        "operator_b":B["operatorId"],
        "state_in":i,
        "state_mid":A["outputState"],
        "state_out":o,
    }

def add_sample(bucket, item, max_n, distinct_source=False):
    if len(bucket)>=max_n:
        return
    if distinct_source and any(x["source_group_id"]==item["source_group_id"] for x in bucket):
        return
    bucket.append(item)

def scan_witnesses(holdout_path, protocol, freeze, result, max_witnesses, max_near):
    cfg=protocol["primitiveGraph"]
    model=freeze["variants"][protocol["primitiveGraph"]["primaryVariant"]]
    probs=core.build_probability_functions(model)
    common=set(model["states"])-{"OTHER"}
    eligible={r["operatorId"] for r in model["operators"]}
    laws=model.get("candidateLaws",{})
    ev=result["laneResults"]["holdout"]["variants"][protocol["primitiveGraph"]["primaryVariant"]].get("lawEvaluation",{})
    transferred={
        "idempotence":{r["operatorA"] for r in ev.get("idempotence",[]) if r["transfers"]},
        "cancellation":{(r["operatorA"],r["operatorB"]) for r in ev.get("cancellation",[]) if r["transfers"]},
        "orderSensitivity":{(r["operatorA"],r["operatorB"]) for r in ev.get("orderSensitivity",[]) if r["transfers"]},
        "conditionalComposition":{(r["operatorA"],r["operatorB"]):{m["inputState"]:m["dominantOutputState"] for m in r["frozenInputOutcomes"]} for r in ev.get("conditionalComposition",[]) if r["transfers"]},
    }
    frozen={
        "idempotence":{r["operatorA"] for r in laws.get("idempotence",[])},
        "cancellation":{(r["operatorA"],r["operatorB"]) for r in laws.get("cancellation",[])},
        "orderSensitivity":{(r["operatorA"],r["operatorB"]) for r in laws.get("orderSensitivity",[])},
        "conditionalComposition":{(r["operatorA"],r["operatorB"]) for r in laws.get("conditionalComposition",[])},
    }
    pair_out=defaultdict(Counter)
    for r in model["counts"]["directPairTwoStep"]:
        pair_out[(r["operatorA"],r["operatorB"])][r["outputState"]]+=int(r["count"])
    collapsed={p:max(c.items(),key=lambda kv:(kv[1],kv[0]))[0] for p,c in pair_out.items() if c}
    out={rid:{"positive":[],"near":[]} for rid in ("CR-001","CR-002","CR-003","CR-004","CR-005")}
    cond=Counter()
    with Path(holdout_path).open("r",encoding="utf-8") as f:
        for raw in f:
            row=json.loads(raw)
            if row.get("lane")!="holdout":
                raise RuntimeError("witness scanner received non-holdout row")
            graph=core.build_graph(row,cfg,protocol["primitiveGraph"]["primaryVariant"])
            for u,v,w,x,A,B in iter_paths(graph,cfg):
                aid,bid=A["operatorId"],B["operatorId"]
                if aid not in eligible or bid not in eligible:
                    continue
                i=core.map_state(A["inputState"],common); o=core.map_state(B["outputState"],common)
                p=prov(row,u,v,w,x,A,B,i,o)
                if probs["pcomp"](aid,bid,i,o)>probs["p2"](i,o):
                    add_sample(out["CR-001"]["positive"],p,max_witnesses,True)
                else:
                    add_sample(out["CR-001"]["near"],p,max_near,False)
                if aid==bid and aid in frozen["idempotence"]:
                    aa=core.safe_log2_probability(probs["pcomp"](aid,aid,i,o))
                    one=core.safe_log2_probability(probs["pop"](aid,i,o))
                    q={**p,"absolute_path_logloss_difference_bits":abs(aa-one)}
                    if aid in transferred["idempotence"] and abs(aa-one)<=float(protocol["lawDiscovery"]["idempotence"]["transferMaximumAbsoluteLogLossDifferenceBitsPerPath"]):
                        add_sample(out["CR-002"]["positive"],q,max_witnesses,True)
                    else:
                        add_sample(out["CR-002"]["near"],q,max_near,False)
                pair=(aid,bid)
                if pair in frozen["cancellation"]:
                    q={**p,"returns_to_input_state":i==o}
                    if pair in transferred["cancellation"] and i==o:
                        add_sample(out["CR-003"]["positive"],q,max_witnesses,True)
                    else:
                        add_sample(out["CR-003"]["near"],q,max_near,False)
                for a0,b0 in frozen["orderSensitivity"]:
                    if pair not in ((a0,b0),(b0,a0)):
                        continue
                    own=probs["pcomp"](aid,bid,i,o); swapped=probs["pcomp"](bid,aid,i,o)
                    q={**p,"own_order_probability":own,"swapped_order_probability":swapped}
                    if (a0,b0) in transferred["orderSensitivity"] and own>swapped:
                        add_sample(out["CR-004"]["positive"],q,max_witnesses,True)
                    else:
                        add_sample(out["CR-004"]["near"],q,max_near,False)
                    break
                if pair in frozen["conditionalComposition"]:
                    mapping=transferred["conditionalComposition"].get(pair)
                    if mapping and i in mapping:
                        expected=mapping[i]
                        cond["specific_n"]+=1; cond["specific_correct"]+=int(o==expected)
                        cond["collapsed_correct"]+=int(o==collapsed.get(pair))
                        q={**p,"frozen_input_specific_output":expected,"collapsed_pair_output":collapsed.get(pair)}
                        if o==expected:
                            add_sample(out["CR-005"]["positive"],q,max_witnesses,True)
                        else:
                            add_sample(out["CR-005"]["near"],q,max_near,False)
                    elif pair in frozen["conditionalComposition"]:
                        add_sample(out["CR-005"]["near"],p,max_near,False)
    out["CR-005"]["conditional_ablation"]={
        "occurrences":cond["specific_n"],
        "input_specific_accuracy":cond["specific_correct"]/max(1,cond["specific_n"]),
        "collapsed_pair_accuracy":cond["collapsed_correct"]/max(1,cond["specific_n"]),
    }
    return out

def law_counts(engine, variant):
    freeze=engine["freeze"]["variants"][variant]
    result=engine["result"]
    rows=result["laneResults"]["holdout"]["variants"][variant].get("lawEvaluation",{})
    control=result["laneResults"]["control"]["variants"][variant].get("lawEvaluation",{})
    return {
        "train_frozen":{k:len(freeze.get("candidateLaws",{}).get(k,[])) for k in ("idempotence","cancellation","orderSensitivity","conditionalComposition")},
        "holdout_transferred":{k:sum(bool(x.get("transfers")) for x in rows.get(k,[])) for k in ("idempotence","cancellation","orderSensitivity","conditionalComposition")},
        "control_transferred":{k:sum(bool(x.get("transfers")) for x in control.get(k,[])) for k in ("idempotence","cancellation","orderSensitivity","conditionalComposition")},
        "holdout_details":rows,
        "control_details":control,
    }

def status_for_law(train_n, holdout_n, topology_n, witnesses):
    if train_n==0:
        return "INSUFFICIENT_CONTRAST"
    if holdout_n==0:
        return "REJECTED_RULE"
    if len({x["source_group_id"] for x in witnesses})<2:
        return "OPEN_RULE"
    if topology_n==0:
        return "SURFACE_ONLY"
    return "HARVESTED_RULE"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--config",required=True)
    ap.add_argument("--v5-packet",required=True)
    ap.add_argument("--work",required=True)
    ap.add_argument("--out-candidates",required=True)
    ap.add_argument("--out-summary",required=True)
    args=ap.parse_args()
    config=load(args.config)
    if not config.get("implementation_sha") or config.get("preexecution_freeze_sha") in (None,"","PENDING"):
        raise RuntimeError("V44 refuses to execute before implementation and preexecution freeze SHAs are recorded")
    if git_blob_sha1(__file__)!=config["runner_blob_sha1"]:
        raise RuntimeError("V44 runner bytes differ from frozen config")
    for path,key in ((PRIMARY_PROTOCOL,"primary_protocol_blob_sha1"),(TOPOLOGY_PROTOCOL,"topology_protocol_blob_sha1")):
        if git_blob_sha1(path)!=config[key]:
            raise RuntimeError("V44 operator reference protocol drift")
    engine_paths={
        "core":REF/"mark_operator_algebra_v9_core.py",
        "split":REF/"split-mark-operator-algebra-v9.py",
        "induce":REF/"induce-mark-operator-algebra-v9.py",
        "evaluate":REF/"evaluate-mark-operator-algebra-v9.py",
        "tests":REF/"test-mark-operator-algebra-v9.py",
    }
    for key,path in engine_paths.items():
        if git_blob_sha1(path)!=config["reference_engine_blobs"][key]:
            raise RuntimeError(f"V44 engine blob drift: {key}")
    eq=REF/"test-mark-v44-bounded-equivalence.py"
    if git_blob_sha1(eq)!=config["bounded_equivalence_blob_sha1"]:
        raise RuntimeError("V44 bounded-equivalence test blob drift")
    subprocess.run([sys.executable,str(eq)],check=True,cwd=str(ROOT))
    subprocess.run([sys.executable,str(REF/"test-mark-operator-algebra-v9.py")],check=True,cwd=str(REF))
    work=Path(args.work); split_dir=work/"split"; split_dir.mkdir(parents=True,exist_ok=True)
    run_cmd(REF/"split-mark-operator-algebra-v9.py",{
        "MARK_V9_PROTOCOL":str(PRIMARY_PROTOCOL),
        "MARK_V5_PACKET":str(Path(args.v5_packet)),
        "MARK_V9_SPLIT":str(split_dir),
    })
    manifest=load(split_dir/"split-manifest.json")
    if manifest["eligibleObservations"]!=config["inputs"]["pair_eligible_observations"]:
        raise RuntimeError("V44 split observation count drift")
    for lane,expected in config["inputs"]["lane_inventory"].items():
        if manifest["lanes"][lane]["observations"]!=expected["observations"]:
            raise RuntimeError("V44 lane inventory drift")
    primary=run_engine("primary",PRIMARY_PROTOCOL,split_dir,work)
    topology=run_engine("topology-ablation",TOPOLOGY_PROTOCOL,split_dir,work)
    pproto=load(PRIMARY_PROTOCOL); tproto=load(TOPOLOGY_PROTOCOL)
    witnesses=scan_witnesses(split_dir/"holdout.jsonl",pproto,primary["freeze"],primary["result"],config["max_witnesses_per_candidate"],config["max_near_counterexamples_per_candidate"])
    pcounts=law_counts(primary,pproto["primitiveGraph"]["primaryVariant"])
    tcounts=law_counts(topology,tproto["primitiveGraph"]["ablationVariant"])
    candidates=[]
    for spec in config["candidate_specs"]:
        rid=spec["rule_id"]; law=spec["engine_law"]
        if law=="composition":
            h=primary["result"]["laneResults"]["holdout"]["variants"]["lengthAware"]
            c=primary["result"]["laneResults"]["control"]["variants"]["lengthAware"]
            a=primary["result"]["adjudication"]
            g=h["gainsBitsPerPath"]
            if not a["coverageGate"]:
                status="INSUFFICIENT_CONTRAST"
            elif g["compositionOverInputOnly"] is None or g["compositionOverInputOnly"]<=0:
                status="REJECTED_RULE"
            elif a["lengthAwareFullGate"] and a["topologyFullGate"] and len({x["source_group_id"] for x in witnesses[rid]["positive"]})>=2:
                status="HARVESTED_RULE"
            elif a["lengthAwareFullGate"] and not a["topologyFullGate"]:
                status="SURFACE_ONLY"
            else:
                status="OPEN_RULE"
            ablation={"status":"RUN","result":h["gainsBitsPerPath"],"method":"remove operator identity entirely (input-only) and separately remove one side (A-only or B-only)"}
            invariance={"status":"RUN","result":{"lengthAwareFullGate":a["lengthAwareFullGate"],"topologyFullGate":a["topologyFullGate"]},"method":"repeat the identical frozen composition gate with normalized path length removed"}
            matched={"status":"RUN","result":h["bitsPerPath"],"method":"input-only, A-only, B-only, and direct A,B pair controls"}
            held={"status":"RUN","result":{"holdout":h,"control":c}}
            downstream={"status":"RUN","result":{"direct_pair_advantage_bits":g["directPairAdvantageOverComposition"]}}
            failures=[] if status=="HARVESTED_RULE" else ["factorized composition did not clear every frozen V44 transfer/invariance gate"]
        else:
            pn=pcounts["train_frozen"][law]; ph=pcounts["holdout_transferred"][law]; pc=pcounts["control_transferred"][law]; th=tcounts["holdout_transferred"][law]
            status=status_for_law(pn,ph,th,witnesses[rid]["positive"])
            if law=="idempotence":
                method="remove the second A and compare A∘A against the frozen one-step A kernel"
            elif law=="cancellation":
                method="compare composite identity return against either single operator and the input-only expected identity return"
            elif law=="orderSensitivity":
                method="swap A,B order while preserving the same frozen operators and incoming interface state"
            else:
                method="collapse the incoming-state distinction and compare against one pair-level dominant output"
            ablation={"status":"RUN","method":method,"result":witnesses[rid].get("conditional_ablation") if law=="conditionalComposition" else pcounts["holdout_details"].get(law,[])}
            invariance={"status":"RUN","method":"rerun the identical frozen law discovery/evaluation with topology-only boundary states","result":{"primary_holdout_transferred":ph,"topology_holdout_transferred":th}}
            matched={"status":"RUN","method":method,"result":pcounts["holdout_details"].get(law,[])}
            held={"status":"RUN","result":{"train_frozen_candidates":pn,"holdout_transferred":ph,"control_transferred":pc,"topology_holdout_transferred":th}}
            downstream={"status":"RUN","result":"the same frozen boundary-state consequence criterion is evaluated on holdout without refit"}
            failures=[] if status=="HARVESTED_RULE" else ["candidate family did not clear every frozen holdout and topology-invariance gate"]
        candidates.append({
            "rule_id":rid,
            "feature_family":spec["feature_family"],
            "feature_definition":spec["feature_definition"],
            "preconditions":spec["preconditions"],
            "operational_delta":spec["operational_delta"],
            "positive_witnesses":witnesses[rid]["positive"],
            "near_counterexamples":witnesses[rid]["near"],
            "ablation":ablation,
            "invariance_control":invariance,
            "matched_or_null_control":matched,
            "held_out_transfer":held,
            "downstream_preservation":downstream,
            "known_failures":failures,
            "residual_unexplained_features":spec.get("residual_unexplained_features",[]),
            "provenance":[{
                "v5_run_id":config["inputs"]["v5_run_id"],
                "v5_artifact":config["inputs"]["v5_artifact"],
                "projector_rows_sha256":config["inputs"]["projector_rows_sha256"],
                "critical_edge_world_sha256":config["inputs"]["critical_edge_world_canonical_sha256"],
                "primary_engine_freeze_file_sha256":primary["freeze_file_sha256"],
                "primary_engine_result_file_sha256":primary["result_file_sha256"],
            }],
            "status":status,
        })
    packet={
        "schema":"mark_song_composition_harvest_v44_phase_a_candidates_v1",
        "experiment_id":"mark:song-composition-harvest:v44",
        "phase":"A",
        "implementation_sha":config["implementation_sha"],
        "preexecution_freeze_sha":config["preexecution_freeze_sha"],
        "runner_blob_sha1":config["runner_blob_sha1"],
        "candidate_construction_sha256":canonical_sha(config["candidate_specs"]),
        "inputs":config["inputs"],
        "engine_custody":{
            "primary_freeze_file_sha256":primary["freeze_file_sha256"],
            "primary_result_file_sha256":primary["result_file_sha256"],
            "topology_freeze_file_sha256":topology["freeze_file_sha256"],
            "topology_result_file_sha256":topology["result_file_sha256"],
            "song_semantics_opened":False,
            "role_labels_opened":False,
            "new_source_acquisition":False,
        },
        "candidates":candidates,
    }
    Path(args.out_candidates).write_text(json.dumps(packet,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    summary={
        "candidate_count":len(candidates),
        "status_counts":dict(Counter(x["status"] for x in candidates)),
        "candidates":[{"rule_id":x["rule_id"],"family":x["feature_family"],"status":x["status"],"positive_witnesses":len(x["positive_witnesses"]),"near_counterexamples":len(x["near_counterexamples"])} for x in candidates],
        "candidate_file_sha256":sha_file(args.out_candidates),
    }
    Path(args.out_summary).write_text(json.dumps(summary,indent=2)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
