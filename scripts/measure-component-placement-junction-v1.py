#!/usr/bin/env python3
"""Extract source-local degree + masked-placement junction law states."""
from __future__ import annotations
import argparse, json, pathlib, re, sqlite3, statistics

ap=argparse.ArgumentParser()
ap.add_argument("--compiler-out",required=True)
ap.add_argument("--source-id",required=True)
ap.add_argument("--lane",required=True)
ap.add_argument("--local-input-sha",required=True)
ap.add_argument("--protocol",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
null_n=int(protocol["measurement"]["nullIterations"])
min_context=30
compiler=pathlib.Path(args.compiler_out)
summary=json.loads((compiler/"summary.json").read_text())
if summary.get("degreeConditionedGrammar") is not True:
    raise SystemExit("compiler output is not degree-conditioned")
if summary.get("placementConditionedGrammar") is not True:
    raise SystemExit("compiler output is not placement-conditioned")
if summary["sources"]!=1:
    raise SystemExit("expected one-source compiler output")
if summary["nullIterations"]!=null_n:
    raise SystemExit("null iteration mismatch")
if summary["sourceBlindInputSha256"]!=args.local_input_sha:
    raise SystemExit("local blind input SHA mismatch")

con=sqlite3.connect(f"file:{compiler/'grammar-stats.sqlite'}?mode=ro",uri=True)
pat=re.compile(r"^CENTER:JUNCTION\|DEGREE:(\d+)\|PLACEMENT:(P[0-9a-f]{16}|UNPLACED)\|ARM:(PATH_TO_(?:ENDPOINT|JUNCTION))$")

contexts=[r[0] for r in con.execute(
  "select distinct context from grammar_stats where iteration=-1 and lane='train' and context like 'CENTER:JUNCTION|DEGREE:%|PLACEMENT:%|ARM:PATH_TO_%' order by context"
)]

def one(q,p):
    row=con.execute(q,p).fetchone()
    return int((row[0] if row else 0) or 0)

rows=[]
for context in contexts:
    m=pat.match(context)
    if not m:
        continue
    degree=int(m.group(1)); placement=m.group(2); arm=m.group(3)
    obs_context=one(
      "select coalesce(sum(count),0) from grammar_stats where iteration=-1 and lane='train' and context=?",
      (context,))
    obs_match=one(
      "select coalesce(count,0) from grammar_stats where iteration=-1 and lane='train' and context=? and outcome=?",
      (context,arm))
    obs_acc=(obs_match/obs_context) if obs_context else 0.0
    null_acc=[]
    for i in range(null_n):
        nc=one(
          "select coalesce(sum(count),0) from grammar_stats where iteration=? and lane='train' and context=?",
          (i,context))
        nm=one(
          "select coalesce(count,0) from grammar_stats where iteration=? and lane='train' and context=? and outcome=?",
          (i,context,arm))
        null_acc.append((nm/nc) if nc else 0.0)
    eligible=(placement!="UNPLACED" and obs_context>=min_context)
    if eligible and all(obs_acc>x for x in null_acc):
        state="STRICT_MATCH"
    elif eligible and all(obs_acc<x for x in null_acc):
        state="STRICT_REVERSE"
    elif eligible:
        state="UNRESOLVED"
    else:
        state="INELIGIBLE"
    rows.append({
      "sourceGroupId":args.source_id,
      "originalBlindLane":args.lane,
      "degree":degree,
      "placementToken":placement,
      "contextArm":arm,
      "observedContextCount":obs_context,
      "observedMatchCount":obs_match,
      "observedAccuracy":obs_acc,
      "nullMeanAccuracy":statistics.fmean(null_acc) if null_acc else 0.0,
      "nullMinAccuracy":min(null_acc) if null_acc else 0.0,
      "nullMaxAccuracy":max(null_acc) if null_acc else 0.0,
      "matchingLift":obs_acc-(statistics.fmean(null_acc) if null_acc else 0.0),
      "state":state
    })

print(json.dumps({
  "schema":"component_placement_junction_source_metrics_v1",
  "sourceGroupId":args.source_id,
  "originalBlindLane":args.lane,
  "centers":summary["centers"],
  "observedPairWeight":int(summary["observedPairWeight"]),
  "placementMapSha256":summary.get("placementMapSha256"),
  "rows":rows,
  "provenanceOpened":False
},separators=(",",":")))
con.close()
