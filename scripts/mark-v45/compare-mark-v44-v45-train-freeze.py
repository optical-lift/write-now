#!/usr/bin/env python3
"""Require exact V44/V45 train-freeze identity before V45 holdout opens."""
import hashlib, json, os, subprocess, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SPLIT=Path(os.environ["MARK_V45_SPLIT"])
WORK=Path(os.environ["MARK_V45_EQ_WORK"])
PRIMARY=Path(os.environ["MARK_V45_PRIMARY_PROTOCOL"])
TOPOLOGY=Path(os.environ["MARK_V45_TOPOLOGY_PROTOCOL"])

def run(script_dir, protocol, out):
    out.mkdir(parents=True,exist_ok=True)
    env={**os.environ,
      "MARK_V9_PROTOCOL":str(protocol),
      "MARK_V9_SPLIT_MANIFEST":str(SPLIT/"split-manifest.json"),
      "MARK_V9_TRAIN":str(SPLIT/"train.jsonl"),
      "MARK_V9_FREEZE":str(out)}
    subprocess.run([sys.executable,str(ROOT/"scripts"/script_dir/"induce-mark-operator-algebra-v9.py")],check=True,env=env)
    return (out/"operator-algebra-freeze.json").read_bytes()

for label,protocol in (("primary",PRIMARY),("topology",TOPOLOGY)):
    b44=run("mark-v44",protocol,WORK/label/"v44")
    b45=run("mark-v45",protocol,WORK/label/"v45")
    if b44!=b45:
        raise RuntimeError(f"V45 train freeze differs from V44 for {label}")
    print(f"V45 {label} train-freeze equivalence PASS sha256={hashlib.sha256(b45).hexdigest()}")
