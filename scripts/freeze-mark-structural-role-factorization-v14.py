#!/usr/bin/env python3
import json, os
from pathlib import Path
from mark_structural_role_factorization_v14_core import *

PROTOCOL=Path(os.environ.get("MARK_V14_PROTOCOL","research/mark/discovery-experiments/structural-role-factorization-v14.protocol.json"))
V12_FREEZE=Path(os.environ.get("MARK_V12_FREEZE","artifacts/v12-freeze/state-operator-freeze.json"))
TRAIN=Path(os.environ.get("MARK_V10_TRAIN","artifact-staging/v10-train/train.jsonl"))
OUT=Path(os.environ.get("MARK_V14_FREEZE","artifacts/mark-structural-role-factorization-v14-freeze"))

def main():
    protocol=json.loads(PROTOCOL.read_text()); v12=json.loads(V12_FREEZE.read_text())
    if v12.get("freezeSha256")!=protocol["lineage"]["v12StateParent"]["expectedFreezeSha256"]: raise RuntimeError("V12 freeze drift")
    check=dict(v12); expected=check.pop("freezeSha256")
    if canonical_sha(check)!=expected: raise RuntimeError("V12 hash mismatch")
    rows=read_jsonl(TRAIN,"train"); events=build_prediction_events(rows,v12,protocol); roles,role_counts,role_glyphs=eligible_roles(events,protocol); mask_rows=select_mask(events,roles,protocol); masked=mask_set(mask_rows)
    if len(mask_rows)!=27 or sum(r["trainOccurrences"] for r in mask_rows)!=387: raise RuntimeError(f"frozen feasibility drift: {len(mask_rows)} / {sum(r['trainOccurrences'] for r in mask_rows)}")
    vocab=sorted(set(v12["space"]["tokens"]))
    model=build_model(events,roles,masked,vocab,protocol); switches=select_role_switches(model,roles,protocol)
    common=set(v12["commonStates"]); eligible=set(v12["eligibleGlyphs"]); best_ng,cv=choose_ngram_order(rows,common,eligible,roles,masked,protocol); ntokens,ntabs,ntotals=build_ngram_tables(rows,common,eligible,roles,masked,protocol,max(protocol["models"]["ngramOrders"]))
    packet={"schema":"mark_structural_role_factorization_freeze_v14","experimentId":protocol["experimentId"],"protocolSha256":canonical_sha(protocol),"parentV12FreezeSha256":v12["freezeSha256"],"trainInscriptionCount":len(rows),"trainPredictionEvents":len(events),"eligibleRoles":sorted(roles),"eligibleRoleCount":len(roles),"eligibleRoleEventCoverage":sum(role_counts[r] for r in roles),"maskedGlyphRoleCells":mask_rows,"maskedTrainEvents":sum(r["trainOccurrences"] for r in mask_rows),"maskedDistinctGlyphs":len(set(r["glyph"] for r in mask_rows)),"maskedDistinctRoles":len(set(r["role"] for r in mask_rows)),"model":encode_model(model),"roleSwitches":switches,"selectedNgramOrder":best_ng,"ngramCrossValidation":cv,"ngram":encode_ngram(ntokens,ntabs)}
    packet["freezeSha256"]=canonical_sha(packet); OUT.mkdir(parents=True,exist_ok=True); (OUT/"structural-role-freeze.json").write_text(json.dumps(packet,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
    lines=["Mark structural role factorization v14 — pre-evaluation freeze",f"protocolSha256={packet['protocolSha256']}",f"freezeSha256={packet['freezeSha256']}",f"eligibleRoles={packet['eligibleRoleCount']}",f"eligibleRoleEventCoverage={packet['eligibleRoleEventCoverage']}",f"maskedGlyphRoleCells={len(mask_rows)}",f"maskedTrainEvents={packet['maskedTrainEvents']}",f"maskedDistinctGlyphs={packet['maskedDistinctGlyphs']}",f"maskedDistinctRoles={packet['maskedDistinctRoles']}",f"roleSwitchMappings={len(switches)}",f"selectedNgramOrder={best_ng}","evaluationOpenedByThisJob=false"]
    for r in cv: lines.append(f"ngramCV order={r['order']};bits={r['bitsPerEvent']:.6f};events={r['events']}")
    (OUT/"summary.txt").write_text("\n".join(lines)+"\n"); print("\n".join(lines))
if __name__=="__main__": main()
