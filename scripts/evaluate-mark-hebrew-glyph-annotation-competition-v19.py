#!/usr/bin/env python3
import os
from pathlib import Path
from mark_hebrew_glyph_annotation_competition_v19_core import read_json,read_jsonl,pairing_lane,map_lane,adjudicate,write_json,sha256_json
protocol=read_json(os.environ["MARK_V19_PROTOCOL"]); freeze=read_json(Path(os.environ["MARK_V19_FREEZE"])/"freeze.json"); hd=Path(os.environ["MARK_V19_HEBREW_EVAL"]); gd=Path(os.environ["MARK_V19_GLYPH_EVAL"]); out=Path(os.environ["MARK_V19_RESULT_OUT"])
if freeze.get("freezeAdjudication")!="FEASIBLE":
    result={"schema":"mark_hebrew_glyph_annotation_competition_result_v19","adjudication":"INSUFFICIENT_SONG_COVERED_PANEL","freezeSha256":freeze.get("freezeSha256")}
else:
    pairing={}; maps={m:{} for m in ("song","conventional","blind")}
    for lane in ("holdout","control"):
        hr=read_jsonl(hd/f"{lane}.jsonl"); gr=read_jsonl(gd/f"{lane}.jsonl"); pairing[lane]=pairing_lane(hr,gr,freeze,protocol,lane)
        for m in maps: maps[m][lane]=map_lane(gr,freeze,protocol,lane,m)
    result={"schema":"mark_hebrew_glyph_annotation_competition_result_v19","freezeSha256":freeze["freezeSha256"],"pairing":pairing,"maps":maps,"adjudication":adjudicate(pairing,maps)}
result["resultSha256"]=sha256_json({k:v for k,v in result.items() if k!="resultSha256"}); write_json(out/"result.json",result)
lines=["# Mark Hebrew ↔ glyph annotation competition v19","",f'Adjudication: **{result["adjudication"]}**',""]
if "pairing" in result:
    lines += ["## Label-blind common-panel transfer","","| lane | evaluable | mean | p | rank | pass |","|---|---:|---:|---:|---:|---|"]
    for lane in ("holdout","control"):
        x=result["pairing"][lane]; lines.append(f'| {lane} | {x["evaluablePairs"]}/{x["frozenPairs"]} | {x["meanSimilarity"]:+.4f} | {x["permutationP"]:.4f} | {x["medianRankPercentile"]:.3f} | {x["pass"]} |')
    lines += ["","## Competing annotation maps","","| map | holdout effect | holdout p | holdout z | holdout pass | control effect | control p | control z | control pass |","|---|---:|---:|---:|---|---:|---:|---:|---|"]
    for m in ("song","conventional","blind"):
        a=result["maps"][m]["holdout"]; b=result["maps"][m]["control"]; lines.append(f'| {m} | {a["operatorBalancedAdvantage"]:+.4f} | {a["permutationP"]:.4f} | {a["permutationZ"]:+.2f} | {a["pass"]} | {b["operatorBalancedAdvantage"]:+.4f} | {b["permutationP"]:.4f} | {b["permutationZ"]:+.2f} | {b["pass"]} |')
lines += ["",f'Result SHA-256: `{result["resultSha256"]}`']
(out/"summary.md").write_text("\n".join(lines)+"\n",encoding="utf-8"); print("\n".join(lines))
