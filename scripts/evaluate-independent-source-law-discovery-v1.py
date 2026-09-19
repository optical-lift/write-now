#!/usr/bin/env python3
"""Evaluate one isolated source against its own 64 null worlds."""
from __future__ import annotations
import argparse, hashlib, json, pathlib, sqlite3, statistics

ap=argparse.ArgumentParser()
ap.add_argument("--compiler-out",required=True)
ap.add_argument("--source-id",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--out",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
null_n=int(protocol["compiler"]["null_iterations"])
min_context=int(protocol["gates"]["minimum_observed_context_count"])
min_enrich=int(protocol["gates"]["enrichment_minimum_observed_outcome_count"])
min_exclude=float(protocol["gates"]["exclusion_minimum_mean_null_outcome_count"])

compiler=pathlib.Path(args.compiler_out)
summary=json.loads((compiler/"summary.json").read_text())
custody=json.loads((compiler/"custody.json").read_text())
if summary["sources"] != 1:
    raise SystemExit("local evaluator received multi-source compiler output")
if summary["nullIterations"] != null_n:
    raise SystemExit("null iteration mismatch")

con=sqlite3.connect(f"file:{compiler/'grammar-stats.sqlite'}?mode=ro",uri=True)
def one(q,p=()):
    r=con.execute(q,p).fetchone()
    return 0 if r is None or r[0] is None else r[0]

contexts=[r[0] for r in con.execute(
 "select distinct context from grammar_stats where iteration=-1 and lane='train' order by context"
)]
diagnostics=[]
admitted=[]
for context in contexts:
    obs_context=int(one("select coalesce(sum(count),0) from grammar_stats where iteration=-1 and lane='train' and context=?",(context,)))
    outcomes=[r[0] for r in con.execute(
      "select distinct outcome from grammar_stats where lane='train' and context=? order by outcome",(context,)
    )]
    null_context=[]
    for i in range(null_n):
        null_context.append(int(one(
          "select coalesce(sum(count),0) from grammar_stats where iteration=? and lane='train' and context=?",(i,context)
        )))
    for outcome in outcomes:
        obs_out=int(one(
          "select coalesce(count,0) from grammar_stats where iteration=-1 and lane='train' and context=? and outcome=?",(context,outcome)
        ))
        obs_acc=(obs_out/obs_context) if obs_context else 0.0
        null_out=[]; null_acc=[]
        for i,total in enumerate(null_context):
            n=int(one(
              "select coalesce(count,0) from grammar_stats where iteration=? and lane='train' and context=? and outcome=?",(i,context,outcome)
            ))
            null_out.append(n)
            null_acc.append((n/total) if total else 0.0)
        null_mean_acc=statistics.fmean(null_acc) if null_acc else 0.0
        null_mean_out=statistics.fmean(null_out) if null_out else 0.0
        lift=obs_acc-null_mean_acc
        enrich=(obs_context>=min_context and obs_out>=min_enrich and lift>0 and all(obs_acc>x for x in null_acc))
        exclude=(obs_context>=min_context and null_mean_out>=min_exclude and lift<0 and all(obs_acc<x for x in null_acc))
        kind="RELATIONAL_ENRICHMENT" if enrich else ("RELATIONAL_EXCLUSION" if exclude else None)
        row={
          "context":context,"outcome":outcome,
          "observedContextCount":obs_context,
          "observedOutcomeCount":obs_out,
          "observedAccuracy":obs_acc,
          "nullMeanAccuracy":null_mean_acc,
          "nullMinAccuracy":min(null_acc) if null_acc else 0.0,
          "nullMaxAccuracy":max(null_acc) if null_acc else 0.0,
          "signedLift":lift,
          "nullExceedances":sum(1 for x in null_acc if x>=obs_acc),
          "nullUnderruns":sum(1 for x in null_acc if x<=obs_acc),
          "meanNullOutcomeCount":null_mean_out,
          "comparisonMass":obs_out if lift>=0 else null_mean_out,
          "admittedKind":kind
        }
        diagnostics.append(row)
        if kind:
            admitted.append(row)

admitted.sort(key=lambda x:(-abs(x["signedLift"]),-x["observedContextCount"],-x["comparisonMass"],x["context"],x["outcome"]))
laws=[]
for rank,row in enumerate(admitted,1):
    local_id=f"ISLD-{args.source_id}-L{rank:03d}"
    direction=row["admittedKind"]
    if direction=="RELATIONAL_ENRICHMENT":
        statement=f"Under local condition {row['context']}, outcome {row['outcome']} is constrained toward occurrence relative to source-local rearrangement."
    else:
        statement=f"Under local condition {row['context']}, outcome {row['outcome']} cannot be treated as freely occurring at the source-local rearrangement rate."
    laws.append({
      "localLawId":local_id,
      "rank":rank,
      "kind":direction,
      "surfaceMeasurement":{"context":row["context"],"outcome":row["outcome"]},
      "relationalStatement":statement,
      "statistics":{k:row[k] for k in [
        "observedContextCount","observedOutcomeCount","observedAccuracy","nullMeanAccuracy",
        "nullMinAccuracy","nullMaxAccuracy","signedLift","nullExceedances","nullUnderruns",
        "meanNullOutcomeCount","comparisonMass"
      ]}
    })

core={
 "schema":"independent_source_local_law_catalogue_v1",
 "sourceGroupId":args.source_id,
 "independenceClass":"INDEPENDENT_LOCAL_DISCOVERY",
 "protocolStatus":"frozen_before_outcome",
 "localBlindInputSha256":summary["sourceBlindInputSha256"],
 "physicalLedgerMerkleRoot":summary.get("physicalLedgerMerkleRoot"),
 "grammarContributionMerkleRoot":summary.get("grammarContributionMerkleRoot"),
 "compilerSummary":{
   "observations":summary["observations"],"centers":summary["centers"],"events":summary["events"],
   "observedPairWeight":summary["observedPairWeight"],"unresolvedArms":summary["unresolvedArms"],
   "nullIterations":summary["nullIterations"]
 },
 "candidatePairsEvaluated":len(diagnostics),
 "admittedLocalLaws":len(laws),
 "laws":laws,
 "crossSourceMatchingPerformed":False,
 "globalLawLabelsAssigned":False,
 "provenanceOpened":False
}
payload=json.dumps(core,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()
catalogue={**core,"catalogueSha256":hashlib.sha256(payload).hexdigest()}
out=pathlib.Path(args.out); out.mkdir(parents=True,exist_ok=True)
(out/"catalogue.json").write_text(json.dumps(catalogue,indent=2,ensure_ascii=False)+"\n")
(out/"diagnostics.jsonl").write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in diagnostics))
(out/"summary.txt").write_text(
 f"source={args.source_id}\nobservations={summary['observations']}\ncenters={summary['centers']}\n"
 f"candidate_pairs={len(diagnostics)}\nadmitted_local_laws={len(laws)}\ncatalogue_sha256={catalogue['catalogueSha256']}\n"
)
con.close()
print(json.dumps({"source":args.source_id,"laws":len(laws),"catalogueSha256":catalogue["catalogueSha256"]}))
