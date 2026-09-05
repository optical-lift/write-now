#!/usr/bin/env python3
import hashlib,json,re
import xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path
NS={"osis":"http://www.bibletechnologies.net/2003/OSIS/namespace"}

def canonical_json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha256_json(v): return hashlib.sha256(canonical_json(v).encode()).hexdigest()
def read_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write_json(p,v):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
def read_jsonl(p):
 with open(p,encoding="utf-8") as f:return [json.loads(x) for x in f if x.strip()]
def write_jsonl(p,rows):
 p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
 with open(p,"w",encoding="utf-8") as f:
  for r in rows:f.write(canonical_json(r)+"\n")
def bucket(s,m=10): return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8],"big")%m

def coarse_morph_family(m):
 x=(m or "").strip()
 if x.startswith("H"):x=x[1:]
 if not x:return None
 return x[:2] if x[0] in "NVAPTS" and len(x)>=2 else x[0]
def target_token_and_morph(w):
 lp=w.attrib.get("lemma","").split("/");mp=w.attrib.get("morph","").split("/");idx=num=None
 for i,p in enumerate(lp):
  z=re.search(r"\d+",p)
  if z:idx=i;num=z.group(0);break
 if num is None:return None,None
 mt=mp[idx] if idx is not None and idx<len(mp) else (mp[-1] if mp else "")
 return "H"+str(int(num)),coarse_morph_family(mt)

def parse_hebrew_wlc(wlc_dir,protocol):
 s=protocol["hebrewSplit"];lanes={k:[] for k in ("train","holdout","control")};sets={"train":set(s["trainBuckets"]),"holdout":set(s["holdoutBuckets"]),"control":set(s["controlBuckets"])};morph=defaultdict(Counter);counts=Counter()
 for p in sorted(Path(wlc_dir).glob("*.xml")):
  root=ET.parse(p).getroot()
  for verse in root.findall(".//osis:verse",NS):
   vid=verse.attrib.get("osisID")
   if not vid:continue
   b=bucket(vid,int(s["modulus"]));lane=next(k for k,v in sets.items() if b in v);toks=[]
   for w in verse.findall(".//osis:w",NS):
    tok,mf=target_token_and_morph(w)
    if not tok:continue
    toks.append(tok)
    if lane=="train" and mf:morph[tok][mf]+=1
   if not toks:continue
   lanes[lane].append({"anonymousUnitId":"V"+hashlib.sha256(vid.encode()).hexdigest()[:20],"lane":lane,"tokens":toks});counts[lane]+=len(toks)
 for k in lanes:lanes[k].sort(key=lambda r:r["anonymousUnitId"])
 cmap={o:{"families":sorted(c),"counts":dict(sorted(c.items()))} for o,c in sorted(morph.items())}
 manifest={"schema":"mark_hebrew_blind_split_v19","sourceCommit":protocol["hebrewSource"]["commit"],"unitCounts":{k:len(v) for k,v in lanes.items()},"tokenCounts":dict(counts)}
 return lanes,cmap,manifest
