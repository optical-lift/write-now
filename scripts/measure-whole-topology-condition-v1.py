#!/usr/bin/env python3
"""Measure blinded topology and matching lifts for one untouched source."""
from __future__ import annotations
import argparse, json, pathlib, sqlite3, statistics

ap=argparse.ArgumentParser()
ap.add_argument("--compiler-out",required=True)
ap.add_argument("--source-id",required=True)
ap.add_argument("--lane",choices=["train","holdout","control"],required=True)
ap.add_argument("--local-input-sha",required=True)
ap.add_argument("--protocol",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
null_n=int(protocol["compiler"]["null_iterations"])
min_context=int(protocol["source_metric"]["eligibility_per_context"].split(">=")[1].strip())
compiler=pathlib.Path(args.compiler_out)
summary=json.loads((compiler/"summary.json").read_text())
if summary["sources"] != 1:
    raise SystemExit("source metric received multi-source compiler output")
if summary["nullIterations"] != null_n:
    raise SystemExit("null iteration mismatch")
if summary["sourceBlindInputSha256"] != args.local_input_sha:
    raise SystemExit("local input SHA mismatch")

con=sqlite3.connect(f"file:{compiler/'grammar-stats.sqlite'}?mode=ro",uri=True)
def count(iteration,context,outcome=None):
    if outcome is None:
        row=con.execute(
          "select coalesce(sum(count),0) from grammar_stats where iteration=? and lane='train' and context=?",
          (iteration,context)).fetchone()
    else:
        row=con.execute(
          "select coalesce(sum(count),0) from grammar_stats where iteration=? and lane='train' and context=? and outcome=?",
          (iteration,context,outcome)).fetchone()
    return int(row[0] or 0)

def metric(context,match_outcome):
    obs_context=count(-1,context)
    obs_match=count(-1,context,match_outcome)
    obs_acc=(obs_match/obs_context) if obs_context else None
    null_acc=[]
    null_context=[]
    null_match=[]
    for i in range(null_n):
        c=count(i,context)
        m=count(i,context,match_outcome)
        null_context.append(c); null_match.append(m)
        null_acc.append((m/c) if c else 0.0)
    mean_null=statistics.fmean(null_acc) if null_acc else None
    return {
      "eligible":obs_context>=min_context,
      "observedContextCount":obs_context,
      "observedMatchCount":obs_match,
      "observedAccuracy":obs_acc,
      "nullMeanAccuracy":mean_null,
      "nullMinAccuracy":min(null_acc) if null_acc else None,
      "nullMaxAccuracy":max(null_acc) if null_acc else None,
      "matchingLift":(obs_acc-mean_null) if obs_acc is not None and mean_null is not None else None,
      "nullContextMean":statistics.fmean(null_context) if null_context else None,
      "nullMatchMean":statistics.fmean(null_match) if null_match else None
    }

centers=int(summary["centers"])
pair_weight=int(summary["observedPairWeight"])
junction=metric(protocol["hypothesis"]["primary_context"],protocol["hypothesis"]["primary_match_outcome"])
endpoint=metric(protocol["hypothesis"]["secondary_context"],protocol["hypothesis"]["secondary_match_outcome"])

row={
 "schema":"whole_topology_condition_v1_source_metric",
 "sourceGroupId":args.source_id,
 "originalBlindLane":args.lane,
 "localBlindInputSha256":args.local_input_sha,
 "centers":centers,
 "observedPairWeight":pair_weight,
 "pairDensity":(pair_weight/centers) if centers else None,
 "junction":junction,
 "endpoint":endpoint,
 "provenanceOpened":False
}
print(json.dumps(row,separators=(",",":")))
con.close()
