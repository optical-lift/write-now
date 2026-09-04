#!/usr/bin/env python3
import json, os
from pathlib import Path
from mark_state_operator_separation_v12_core import canonical_sha, history_before, mapped_stream, read_jsonl
from mark_matched_direct_pair_residual_v13_core import thaw_v12, build_history_pair, select_panel, encode_history, panel_lookup

PROTOCOL=Path(os.environ.get("MARK_V13_PROTOCOL","research/mark/discovery-experiments/matched-direct-pair-residual-v13.protocol.json"))
V12_FREEZE=Path(os.environ.get("MARK_V12_FREEZE","artifacts/v12-freeze/state-operator-freeze.json"))
TRAIN=Path(os.environ.get("MARK_V10_TRAIN","artifact-staging/v10-train/train.jsonl"))
OUT=Path(os.environ.get("MARK_V13_FREEZE","artifacts/mark-matched-direct-pair-residual-v13-freeze"))


def main():
    protocol=json.loads(PROTOCOL.read_text(encoding="utf-8")); v12=json.loads(V12_FREEZE.read_text(encoding="utf-8"))
    if protocol.get("schema")!="mark_matched_direct_pair_residual_protocol_v13": raise RuntimeError("bad V13 protocol")
    if v12.get("schema")!="mark_state_operator_separation_freeze_v12": raise RuntimeError("bad V12 freeze schema")
    if v12.get("freezeSha256")!=protocol["parent"]["expectedV12FreezeSha256"]: raise RuntimeError("V12 freeze drift")
    check=dict(v12); expected=check.pop("freezeSha256")
    if canonical_sha(check)!=expected: raise RuntimeError("V12 freeze hash mismatch")
    rows=read_jsonl(TRAIN,"train"); common=set(v12["commonStates"]); eligible=set(v12["eligibleGlyphs"]); L=int(v12["historyLength"])
    space,m=thaw_v12(v12,protocol); hcounts,htotals,hdocs=build_history_pair(rows,common,eligible,m,L); panel=select_panel(m,protocol); lookup=panel_lookup(panel)
    matched_events=0; matched_docs=set()
    for row in rows:
        raw,s=mapped_stream(row["words"],common); doc=row["anonymousInscriptionId"]
        for i in range(1,len(s)-2):
            a,b=raw[i],raw[i+1]
            if a not in eligible or b not in eligible: continue
            H=history_before(s,i,L); S=m["state"](H)
            if (S,a,b) in lookup: matched_events+=1; matched_docs.add(doc)
    packet={
        "schema":"mark_matched_direct_pair_residual_freeze_v13",
        "experimentId":protocol["experimentId"],
        "protocolSha256":canonical_sha(protocol),
        "parentV12FreezeSha256":v12["freezeSha256"],
        "parentV12ResultSha256":protocol["parent"]["expectedV12ResultSha256"],
        "historyLength":L,
        "selectedStateCount":int(v12["selectedStateCount"]),
        "matchedPanel":panel,
        "historyPairRows":encode_history(hcounts),
        "trainHistoryPairCells":len(htotals),
        "matchedTrainEvents":matched_events,
        "matchedTrainInscriptions":len(matched_docs)
    }
    packet["freezeSha256"]=canonical_sha(packet)
    OUT.mkdir(parents=True,exist_ok=True)
    (OUT/"matched-pair-freeze.json").write_text(json.dumps(packet,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    lines=[
        "Mark matched direct-pair residual v13 — pre-evaluation freeze",
        f"protocolSha256={packet['protocolSha256']}",
        f"freezeSha256={packet['freezeSha256']}",
        f"parentV12FreezeSha256={packet['parentV12FreezeSha256']}",
        f"matchedMappings={len(panel)}",
        f"matchedTrainEvents={matched_events}",
        f"matchedTrainInscriptions={len(matched_docs)}",
        f"historyPairCells={len(htotals)}",
        "evaluationOpenedByThisJob=false"
    ]
    (OUT/"summary.txt").write_text("\n".join(lines)+"\n",encoding="utf-8"); print("\n".join(lines))

if __name__=="__main__": main()
