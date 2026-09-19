#!/usr/bin/env python3
"""Extract source-local degree + placement + containing-parent-state law states."""
from __future__ import annotations
import argparse, json, pathlib, re, sqlite3, statistics, hashlib

ap=argparse.ArgumentParser()
ap.add_argument("--compiler-out",required=True)
ap.add_argument("--source-id",required=True)
ap.add_argument("--lane",required=True)
ap.add_argument("--local-input-sha",required=True)
ap.add_argument("--protocol",required=True)
ap.add_argument("--target-set",required=True)
args=ap.parse_args()

protocol=json.loads(pathlib.Path(args.protocol).read_text())
targets=json.loads(pathlib.Path(args.target_set).read_text())
if targets.get("schema")!="parent_state_conditioned_target_set_v1":
    raise SystemExit("invalid target set schema")
core={k:v for k,v in targets.items() if k!="targetSetSha256"}
calc=hashlib.sha256(json.dumps(core,sort_keys=True,separators=(",",":")).encode()).hexdigest()
if calc!=targets.get("targetSetSha256"):
    raise SystemExit("target set SHA mismatch")
target_keys={(int(x["degree"]),x["placementToken"],x["contextArm"]) for x in targets["targets"]}

null_n=int(protocol["measurement"]["nullIterations"])
min_context=30
compiler=pathlib.Path(args.compiler_out)
summary=json.loads((compiler/"summary.json").read_text())
if summary.get("degreeConditionedGrammar") is not True:
    raise SystemExit("compiler output is not degree-conditioned")
if summary.get("placementConditionedGrammar") is not True:
    raise SystemExit("compiler output is not placement-conditioned")
if summary.get("parentStateConditionedGrammar") is not True:
    raise SystemExit("compiler output is not parent-state-conditioned")
if summary["sources"]!=1:
    raise SystemExit("expected one-source compiler output")
if summary["nullIterations"]!=null_n:
    raise SystemExit("null iteration mismatch")
if summary["sourceBlindInputSha256"]!=args.local_input_sha:
    raise SystemExit("local blind input SHA mismatch")

con=sqlite3.connect(f"file:{compiler/'grammar-stats.sqlite'}?mode=ro",uri=True)
pat=re.compile(
 r"^CENTER:JUNCTION\|DEGREE:(\d+)\|PLACEMENT:(P[0-9a-f]{16}|UNPLACED)"
 r"\|PARENT_STATE:(S[123]|UNPARENTED_STATE)\|ARM:(PATH_TO_(?:ENDPOINT|JUNCTION))$"
)
contexts=[r[0] for r in con.execute(
  "select distinct context from grammar_stats where iteration=-1 and lane='train' "
  "and context like 'CENTER:JUNCTION|DEGREE:%|PLACEMENT:%|PARENT_STATE:%|ARM:PATH_TO_%' order by context"
)]

def one(q,p):
    row=con.execute(q,p).fetchone()
    return int((row[0] if row else 0) or 0)

rows=[]
for context in contexts:
    m=pat.match(context)
    if not m:
        continue
    degree=int(m.group(1)); placement=m.group(2); parent_state=m.group(3); arm=m.group(4)
    if (degree,placement,arm) not in target_keys:
        continue
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
    eligible=(placement!="UNPLACED" and parent_state!="UNPARENTED_STATE" and obs_context>=min_context)
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
      "parentStateToken":parent_state,
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
  "schema":"parent_state_conditioned_junction_source_metrics_v1",
  "sourceGroupId":args.source_id,
  "originalBlindLane":args.lane,
  "centers":summary["centers"],
  "observedPairWeight":int(summary["observedPairWeight"]),
  "placementMapSha256":summary.get("placementMapSha256"),
  "parentStateMapSha256":summary.get("parentStateMapSha256"),
  "targetSetSha256":targets["targetSetSha256"],
  "rows":rows,
  "provenanceOpened":False
},separators=(",",":")))
con.close()
