#!/usr/bin/env python3
import hashlib, json, math, random, re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

NS={"osis":"http://www.bibletechnologies.net/2003/OSIS/namespace"}
START="<START>"
OUTCOMES=("SAME_CURRENT","REPEAT_H1","REPEAT_H2","REPEAT_H3","REPEAT_H4","SEEN_EARLIER_SEGMENT","NEW_SEGMENT","END")

def canonical_json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha256_json(v): return hashlib.sha256(canonical_json(v).encode()).hexdigest()
def read_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write_json(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
def read_jsonl(p):
    with open(p,encoding="utf-8") as f: return [json.loads(x) for x in f if x.strip()]
def write_jsonl(p,rows):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True)
    with open(p,"w",encoding="utf-8") as f:
        for r in rows: f.write(canonical_json(r)+"\n")
def bucket(s,m=10): return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8],"big")%m

def coarse_morph_family(m):
    x=(m or "").strip()
    if x.startswith("H"): x=x[1:]
    if not x: return None
    if x[0] in "NVAPT S".replace(" ","") and len(x)>=2: return x[:2]
    return x[0]

def target_token_and_morph(word):
    lemma=word.attrib.get("lemma",""); morph=word.attrib.get("morph","")
    lp=lemma.split("/") if lemma else [] ; mp=morph.split("/") if morph else []
    idx=None; num=None
    for i,p in enumerate(lp):
        m=re.search(r"\d+",p)
        if m: idx=i; num=m.group(0); break
    if num is None: return None,None
    mt=mp[idx] if idx is not None and idx<len(mp) else (mp[-1] if mp else "")
    return "H"+str(int(num)), coarse_morph_family(mt)

def parse_hebrew_wlc(wlc_dir,protocol):
    split=protocol["hebrewSplit"]; lanes={k:[] for k in ("train","holdout","control")}
    sets={"train":set(split["trainBuckets"]),"holdout":set(split["holdoutBuckets"]),"control":set(split["controlBuckets"])}
    train_morph=defaultdict(Counter); counts=Counter()
    for p in sorted(Path(wlc_dir).glob("*.xml")):
        root=ET.parse(p).getroot()
        for verse in root.findall(".//osis:verse",NS):
            vid=verse.attrib.get("osisID")
            if not vid: continue
            b=bucket(vid,int(split["modulus"])); lane=next(k for k,s in sets.items() if b in s)
            toks=[]
            for w in verse.findall(".//osis:w",NS):
                tok,mf=target_token_and_morph(w)
                if not tok: continue
                toks.append(tok)
                if lane=="train" and mf: train_morph[tok][mf]+=1
            if not toks: continue
            lanes[lane].append({"anonymousUnitId":"V"+hashlib.sha256(vid.encode()).hexdigest()[:20],"lane":lane,"tokens":toks})
            counts[lane]+=len(toks)
    for k in lanes: lanes[k].sort(key=lambda r:r["anonymousUnitId"])
    cmap={o:{"families":sorted(c.keys()),"counts":dict(sorted(c.items()))} for o,c in sorted(train_morph.items())}
    manifest={"schema":"mark_hebrew_blind_split_v19","sourceCommit":protocol["hebrewSource"]["commit"],"unitCounts":{k:len(v) for k,v in lanes.items()},"tokenCounts":dict(counts)}
    return lanes,cmap,manifest

def glyph_segments(rows):
    for r in rows:
        seg=[]; j=0
        for w in r["words"]:
            if w=="\n":
                if seg: yield f'{r["anonymousInscriptionId"]}:{j}',seg; j+=1; seg=[]
            else: seg.extend(list(w))
        if seg: yield f'{r["anonymousInscriptionId"]}:{j}',seg

def hist(seq,i):
    h=[START]*max(0,4-i)+seq[max(0,i-4):i]; seen={}; out=[]
    for x in h:
        if x==START: out.append(x)
        else:
            if x not in seen: seen[x]=f"A{len(seen)}"
            out.append(seen[x])
    return canonical_json(out)

def consequence(seq,i):
    if i+1>=len(seq): return "END"
    y=seq[i+1]
    if y==seq[i]: return "SAME_CURRENT"
    for k in range(1,5):
        if i-k>=0 and y==seq[i-k]: return f"REPEAT_H{k}"
    return "SEEN_EARLIER_SEGMENT" if y in seq[:max(0,i-4)] else "NEW_SEGMENT"

def event_rows(rows,kind):
    segs=((r["anonymousUnitId"],r["tokens"]) for r in rows) if kind=="hebrew" else glyph_segments(rows)
    out=[]
    for unit,seq in segs:
        for i in range(len(seq)): out.append({"unit":unit,"state":hist(seq,i),"operator":seq[i],"outcome":consequence(seq,i)})
    return out

def tables(ev):
    state=defaultdict(Counter); sop=defaultdict(Counter); sn=Counter(); sopn=Counter(); opn=Counter()
    for e in ev:
        S,o,y=e["state"],e["operator"],e["outcome"]; state[S][y]+=1; sn[S]+=1; sop[(S,o)][y]+=1; sopn[(S,o)]+=1; opn[o]+=1
    return state,sop,sn,sopn,opn

def shared_states(hev,gev,cfg):
    ht=tables(hev); gt=tables(gev); mn=int(cfg["minimumSharedStateEventsPerCorpus"])
    states=sorted(S for S in set(ht[2])&set(gt[2]) if ht[2][S]>=mn and gt[2][S]>=mn)
    HN=sum(ht[2][S] for S in states); GN=sum(gt[2][S] for S in states)
    raw={S:math.sqrt((ht[2][S]/max(1,HN))*(gt[2][S]/max(1,GN))) for S in states}; z=sum(raw.values()) or 1.0
    return states,{S:raw[S]/z for S in states},ht,gt

def eligible_ops(tab,states,cfg,allowed=None,max_ops=None):
    out=[]
    for op,n in tab[4].items():
        if allowed is not None and op not in allowed: continue
        cov=sum(tab[3][(S,op)]>=int(cfg["minimumOperatorStateEventsForCoverage"]) for S in states)
        if n>=int(cfg["minimumOperatorEvents"]) and cov>=int(cfg["minimumCoveredSharedStates"]): out.append((op,int(n),int(cov)))
    out.sort(key=lambda x:(-x[1],x[0]))
    return out[:max_ops] if max_ops else out

def build_fingerprints(tab,states,weights,operators,cfg):
    alpha=float(cfg["globalAdditiveAlpha"]); lam=float(cfg["backoffPseudoCount"]); clip=float(cfg["residualLog2Clip"])
    out={}
    for op in operators:
        vals=[]; ws=[]
        for S in states:
            b={y:(tab[0][S][y]+alpha)/(tab[2][S]+alpha*len(OUTCOMES)) for y in OUTCOMES}; n=tab[3][(S,op)]
            q={y:(tab[1][(S,op)][y]+lam*b[y])/(n+lam) if n else b[y] for y in OUTCOMES}
            for y in OUTCOMES:
                vals.append(max(-clip,min(clip,math.log2(max(q[y],1e-300)/max(b[y],1e-300))))); ws.append(weights[S])
        norm=math.sqrt(sum(w*x*x for w,x in zip(ws,vals))); out[op]={"vector":vals,"norm":norm}
    return out

def vector_weights(states,weights): return [weights[S] for S in states for _ in OUTCOMES]
def cosine(a,b,weights):
    na=math.sqrt(sum(w*x*x for w,x in zip(weights,a))); nb=math.sqrt(sum(w*y*y for w,y in zip(weights,b)))
    return sum(w*x*y for w,x,y in zip(weights,a,b))/(na*nb) if na and nb else 0.0

def greedy_one_to_one(H,G,hfp,gfp,vw):
    edges=[]
    for h in H:
        for g in G: edges.append((cosine(hfp[h]["vector"],gfp[g]["vector"],vw),h,g))
    edges.sort(key=lambda x:(-x[0],x[1],x[2])); uh=set(); ug=set(); pairs=[]
    for s,h,g in edges:
        if h in uh or g in ug: continue
        uh.add(h); ug.add(g); pairs.append({"hebrew":h,"glyph":g,"trainSimilarity":s})
        if len(uh)==len(H): break
    pairs.sort(key=lambda r:r["hebrew"]); return pairs

def song_labels(song_manifest):
    out=defaultdict(set)
    for lab,ids in song_manifest["groups"].items():
        for o in ids: out[o].add(lab)
    return {o:sorted(v) for o,v in out.items()}

def complete_linkage_labels(items,hfp,vw,k):
    def dist(a,b): return 1.0-cosine(hfp[a]["vector"],hfp[b]["vector"],vw)
    cl²È="25½¸¡±…‰•±Ì±„±ˆ¤èÉ•ÑÕÉ¸‰½½°¡Í•Ð¡±…‰•±Ì¹•Ð¡„±mt¤¤€˜Í•Ð¡±…‰•±Ì¹•Ð¡ˆ±mt¤¤¤()‘•˜ÍÕÁÁ½ÉÑ}ÍÑÉ…Ñ„¡Á…¥ÉÌ±}ÍÕÁÁ½ÉÐ±ÍÑÉ…Ñ„ôÈ¤è(€€€Ù…±ÌõÍ½ÉÑ•¡}ÍÕÁÁ½ÉÑmÉl‰±åÁ ‰ut™½ÈÈ¥¸Á…¥ÉÌ¤(€€€ÕÑÌõmt(€€€™½ÈÄ¥¸É…¹” Ä±ÍÑÉ…Ñ„¤èÕÑÌ¹…ÁÁ•¹¡Ù…±Ímµ¥¸¡±•¸¡Ù…±Ì¤´Ä±¥¹Ð ¡±•¸¡Ù…±Ì¤´Ä¤©Ä½ÍÑÉ…Ñ„¤¥t¤(€€€½ÕÐõíô(€€€™½ÈÈ¥¸Á…¥ÉÌè½ÕÑmÉl‰±åÁ ‰utõÍÕ´¡}ÍÕÁÁ½ÉÑmÉl‰±åÁ ‰utùŒ™½ÈŒ¥¸ÕÑÌ¤(€€€É•ÑÕÉ¸½ÕÐ()‘•˜™É••é•}µ½‘•°¡¡É½ÝÌ±É½ÝÌ±½¹Ù•¹Ñ¥½¹…±}µ…À±Í½¹}µ…¹¥™•ÍÐ±ÁÉ½Ñ½½°¤è(€€€™œõÁÉ½Ñ½½±l‰•á…ÑXÄÔ‰ul‰ÑÉ…¥¹¥¹œ‰tì¡•Øõ•Ù•¹Ñ}É½ÝÌ¡¡É½ÝÌ°‰¡•‰É•Üˆ¤ì•Øõ•Ù•¹Ñ}É½ÝÌ¡É½ÝÌ°‰±åÁ ˆ¤(€€€ÍÑ…Ñ•Ì±ÍÜ±¡Ð±ÐõÍ¡…É•‘}ÍÑ…Ñ•Ì¡¡•Ø±•Ø±™œ¤ìÙÜõÙ•Ñ½É}Ý•¥¡ÑÌ¡ÍÑ…Ñ•Ì±ÍÜ¤(€€€Í°õÍ½¹}±…‰•±Ì¡Í½¹}µ…¹¥™•ÍÐ¤ì…±±½Ý•õÍ•Ð¡Í°¤(€€€¡É½ÝÍ}•°õ•±¥¥‰±•}½ÁÌ¡¡Ð±ÍÑ…Ñ•Ì±™œ±…±±½Ý•õ…±±½Ý•±µ…á}½ÁÌõ9½¹”¤ìÉ½ÝÍ}•°õ•±¥¥‰±•}½ÁÌ¡Ð±ÍÑ…Ñ•Ì±™œ±…±±½Ý•õ9½¹”±µ…á}½ÁÌõ¥¹Ð¡™l‰µ…á¥µÕµ±åÁ¡=Á•É…Ñ½ÉÌ‰t¤¤(€€€ õmálÁt™½Èà¥¸¡É½ÝÍ}•±tìõmálÁt™½Èà¥¸É½ÝÍ}•±t(€€€¡™Àõ‰Õ¥±‘}™¥¹•ÉÁÉ¥¹ÑÌ¡¡Ð±ÍÑ…Ñ•Ì±ÍÜ± ±™œ¤ì™Àõ‰Õ¥±‘}™¥¹•ÉÁÉ¥¹ÑÌ¡Ð±ÍÑ…Ñ•Ì±ÍÜ±±™œ¤(€€€™±½½Èõ™±½…Ð¡™l‰µ¥¹¥µÕµ¥¹•ÉÁÉ¥¹Ñ9½É´‰t¤ì õm ™½È ¥¸ ¥˜¡™Ám¡ul‰¹½É´‰tøõ™±½½Étìõmœ™½Èœ¥¸¥˜™Ámul‰¹½É´‰tøõ™±½½Ét(€€€Á…¥ÉÌõÉ••‘å}½¹•}Ñ½}½¹”¡ ±±¡™À±™À±ÙÜ¤(€€€ÍÑÈõÍÕÁÁ½ÉÑ}ÍÑÉ…Ñ„¡Á…¥ÉÌ±ÑlÑt°È¤¥˜Á…¥ÉÌ•±Í”íô(€€€™½ÈÈ¥¸Á…¥ÉÌè(€€€€€€€Él‰¡•‰É•ÝQÉ…¥¹MÕÁÁ½ÉÐ‰tõ¥¹Ð¡¡ÑlÑumÉl‰¡•‰É•Ü‰ut¤ìÉl‰±åÁ¡QÉ…¥¹MÕÁÁ½ÉÐ‰tõ¥¹Ð¡ÑlÑumÉl‰±åÁ ‰ut¤ìÉl‰±åÁ¡MÕÁÁ½ÉÑMÑÉ…ÑÕ´‰tõÍÑÈ¹•Ð¡Él‰±åÁ ‰t°À¤(€€€½¹Øõí éÍ½ÉÑ•¡½¹Ù•¹Ñ¥½¹…±}µ…À¹•Ð¡ ±íô¤¹•Ð ‰™…µ¥±¥•Ìˆ±mt¤¤™½È ¥¸!ô(€€€Í½¹œõí éÍ°¹•Ð¡ ±mt¤™½È ¥¸!ô(€€€‰±¥¹±‰µ•Ñ„õ‰±¥¹‘}±…‰•±Ì¡ ±¡™À±ÙÜ±ÁÉ½Ñ½½±l‰…¹¹½Ñ…Ñ¥½¹5…ÁÌ‰ul‰‰±¥¹‰ul‰…¹‘¥‘…Ñ•,‰t¤(€€€µ…ÁÌõì‰Í½¹œˆéÍ½¹œ°‰½¹Ù•¹Ñ¥½¹…°ˆé½¹Ø°‰‰±¥¹ˆé‰±¥¹‘ô(€€€É•±½Õ¹ÑÌõíô(€€€™½È¹…µ”±±…‰Ì¥¸µ…ÁÌ¹¥Ñ•µÌ ¤è(€€€€€€€ÉÀõÍÕ´¡É•±…Ñ¥½¸¡±…‰Ì±„±ˆ¤™½È¤±„¥¸•¹Õµ•É…Ñ”¡ ¤™½Èˆ¥¸!m¤¬Äét¤ìÑ½Ñ…°õ±•¸¡ ¤¨¡±•¸¡ ¤´Ä¤¼¼È(€€€€€€€É•±½Õ¹ÑÍm¹…µ•tõì‰É•±…Ñ•‘A…¥ÉÌˆéÉÀ°‰Õ¹É•±…Ñ•‘A…¥ÉÌˆéÑ½Ñ…°µÉÁô(€€€É•ÑÕÉ¸ì‰Í¡…É•‘MÑ…Ñ•ÌˆéÍÑ…Ñ•Ì°‰Í¡…É•‘MÑ…Ñ•]•¥¡ÑÌˆéÍÜ°‰¡•‰É•Ý=Á•É…Ñ½ÉÌˆé¡É½ÝÍ}•°°‰±åÁ¡=Á•É…Ñ½ÉÌˆéÉ½ÝÍ}•°°‰Á…¹•±=Á•É…Ñ½ÉÌˆé °‰Á…¥ÉÌˆéÁ…¥ÉÌ°‰…¹¹½Ñ…Ñ¥½¹5…ÁÌˆéµ…ÁÌ°‰É•±…Ñ¥½¹½Õ¹ÑÌˆéÉ•±½Õ¹ÑÌ°‰‰±¥¹‘5•Ñ…‘…Ñ„ˆé‰µ•Ñ„°‰ÑÉ…¥¹Ù•¹Ñ½Õ¹ÑÌˆéì‰¡•‰É•Üˆé±•¸¡¡•Ø¤°‰±åÁ ˆé±•¸¡•Ø¥ô°‰Í½¹M½ÕÉ•AÉ½Ù•¹…¹”ˆéÍ½¹}µ…¹¥™•ÍÑl‰Í½ÕÉ•Ì‰uô()‘•˜•Ù…±}™¥¹•ÉÁÉ¥¹ÑÌ¡É½ÝÌ±­¥¹±™É••é”±ÁÉ½Ñ½½°¤è(€€€™œõÁÉ½Ñ½½±l‰•á…ÑXÄÔ‰ul‰ÑÉ…¥¹¥¹œ‰tì•Øõ•Ù•¹Ñ}É½ÝÌ¡É½ÝÌ±­¥¹¤ìÑ…ˆõÑ…‰±•Ì¡•Ø¤ìÍÑ…Ñ•Ìõ™É••é•l‰Í¡…É•‘MÑ…Ñ•Ì‰tìÍÜõ™É••é•l‰Í¡…É•‘MÑ…Ñ•]•¥¡ÑÌ‰t(€€€½ÁÌõ™É••é•l‰Á…¹•±=Á•É…Ñ½ÉÌ‰t¥˜­¥¹ôô‰¡•‰É•Üˆ•±Í”mÉl‰±åÁ ‰t™½ÈÈ¥¸™É••é•l‰Á…¥ÉÌ‰ut(€€€É•ÑÕÉ¸‰Õ¥±‘}™¥¹•ÉÁÉ¥¹ÑÌ¡Ñ…ˆ±ÍÑ…Ñ•Ì±ÍÜ±½ÁÌ±™œ¤±Ñ…ˆ()‘•˜Á…¥É¥¹}±…¹”¡¡É½ÝÌ±É½ÝÌ±™É••é”±ÁÉ½Ñ½½°±±…¹”¤è(€€€¡™À±¡Ðõ•Ù…±}™¥¹•ÉÁÉ¥¹ÑÌ¡¡É½ÝÌ°‰¡•‰É•Üˆ±™É••é”±ÁÉ½Ñ½½°¤ì™À±Ðõ•Ù…±}™¥¹•ÉÁÉ¥¹ÑÌ¡É½ÝÌ°‰±åÁ ˆ±™É••é”±ÁÉ½Ñ½½°¤ìÙÜõÙ•Ñ½É}Ý•¥¡ÑÌ¡™É••é•l‰Í¡…É•‘MÑ…Ñ•Ì‰t±™É••é•l‰Í¡…É•‘MÑ…Ñ•]•¥¡ÑÌ‰t¤(€€€µ¸õ¥¹Ð¡ÁÉ½Ñ½½±l‰•Ù…±Õ…Ñ¥½¸‰ul‰µ¥¹¥µÕµÙ…±Õ…Ñ¥½¹Ù•¹ÑÍA•É5…Ñ¡•‘=Á•É…Ñ½È‰t¤ìÁ…¥ÉÌõmÈ™½ÈÈ¥¸™É••é•l‰Á…¥ÉÌ‰t¥˜¡ÑlÑumÉl‰¡•‰É•Ü‰utøõµ¸…¹ÑlÑumÉl‰±åÁ ‰utøõµ¹t(€€€‘•˜Í¥´¡ ±œ¤èÉ•ÑÕÉ¸½Í¥¹”¡¡™Ám¡ul‰Ù•Ñ½È‰t±™Ámul‰Ù•Ñ½È‰t±ÙÜ¤(€€€½‰ÌõmÍ¥´¡Él‰¡•‰É•Ü‰t±Él‰±åÁ ‰t¤™½ÈÈ¥¸Á…¥ÉÍtìµ•…¸õÍÕ´¡½‰Ì¤½µ…à Ä±±•¸¡½‰Ì¤¤ì±åÁ¡ÌõmÉl‰±åÁ ‰t™½ÈÈ¥¸Á…¥ÉÍtìÉ…¹­Ìõmt(€€€™½ÈÈ¥¸Á…¥ÉÌè(€€€€€€€…ÑÕ…°õÍ¥´¡Él‰¡•‰É•Ü‰t±Él‰±åÁ ‰t¤ìÍ½É•ÌõmÍ¥´¡Él‰¡•‰É•Ü‰t±œ¤™½Èœ¥¸±åÁ¡ÍtìÉ…¹­Ì¹…ÁÁ•¹ ¡ÍÕ´¡àðõ…ÑÕ…°™½Èà¥¸Í½É•Ì¤´Ä¤½µ…à Ä±±•¸¡Í½É•Ì¤´Ä¤¤(€€€µ•õÍ½ÉÑ•¡É…¹­Ì¥m±•¸¡É…¹­Ì¤¼¼Ét¥˜É…¹­Ì•±Í”€À¸À(€€€ÁŒõ¥¹Ð¡ÁÉ½Ñ½½±l‰•Ù…±Õ…Ñ¥½¸‰ul‰Á•ÉµÕÑ…Ñ¥½¹½Õ¹Ð‰t¤ìÉ¹œõÉ…¹‘½´¹I…¹‘½´¡ÁÉ½Ñ½½±l‰•Ù…±Õ…Ñ¥½¸‰ul‰Á…¥É¥¹A•ÉµÕÑ…Ñ¥½¹M••‰t¬ˆèˆ­±…¹”¤ì”õmÉl‰±åÁ ‰t™½ÈÈ¥¸Á…¥ÉÍtì¹Õ±°õmt(€€€™½È|¥¸É…¹”¡ÁŒ¤è(€€€€€€€Àõ•létìÉ¹œ¹Í¡Õ™™±”¡À¤ì¹Õ±°¹…ÁÁ•¹¡ÍÕ´¡Í¥´¡Él‰¡•‰É•Ü‰t±œ¤™½ÈÈ±œ¥¸é¥À¡Á…¥ÉÌ±À¤¤½µ…à Ä±±•¸¡Á…¥ÉÌ¤¤¤(€€€ÁÙ…°ô Ä­ÍÕ´¡àøõµ•…¸™½Èà¥¸¹Õ±°¤¤¼ Ä­ÁŒ¤(€€€™É…Œõ±•¸¡Á…¥ÉÌ¤½µ…à Ä±±•¸¡™É••é•l‰Á…¥ÉÌ‰t¤¤ì…Ñ•ÌõÁÉ½Ñ½½±l‰•Ù…±Õ…Ñ¥½¸‰ul‰Á…¥É¥¹…Ñ•ÍA•É1…¹”‰t(€€€Á…ÍÍ•ô¡±•¸¡Á…¥ÉÌ¤øõ¥¹Ð¡ÁÉ½Ñ½½±l‰•Ù…±Õ…Ñ¥½¸‰ul‰µ¥¹¥µÕµÙ…±Õ…‰±•=Á•É…Ñ½É½Õ¹Ð‰t¤…¹™É…Œøõ™±½…Ð¡ÁÉ½Ñ½½±l‰•Ù…±Õ…Ñ¥½¸‰ul‰µ¥¹¥µÕµÙ…±Õ…‰±•=Á•É…Ñ½ÉÉ…Ñ¥½¸‰t¤…¹µ•…¸ù™±½…Ð¡…Ñ•Íl‰µ•…¹M¥µ¥±…É¥ÑåÉ•…Ñ•ÉQ¡…¸‰t¤…¹ÁÙ…°ðõ™±½…Ð¡…Ñ•Íl‰Õ¹ÍÑÉ…Ñ¥™¥•‘A•ÉµÕÑ…Ñ¥½¹AÑ5½ÍÐ‰t¤…¹µ•øõ™±½…Ð¡…Ñ•Íl‰µ•‘¥…¹I…¹­A•É•¹Ñ¥±•Ñ1•…ÍÐ‰t¤¤(€€€É•ÑÕÉ¸ì‰•Ù…±Õ…‰±•A…¥ÉÌˆé±•¸¡Á…¥ÉÌ¤°‰™É½é•¹A…¥ÉÌˆé±•¸¡™É••é•l‰Á…¥ÉÌ‰t¤°‰•Ù…±Õ…‰±•É…Ñ¥½¸ˆé™É…Œ°‰µ•…¹M¥µ¥±…É¥Ñäˆéµ•…¸°‰Á•ÉµÕÑ…Ñ¥½¹@ˆéÁÙ…°°‰µ•‘¥…¹I…¹­A•É•¹Ñ¥±”ˆéµ•°‰Á…ÍÌˆéÁ…ÍÍ•°‰Á…¥ÉÌˆémì‰¡•‰É•ÜˆéÉl‰¡•‰É•Ü‰t°‰±åÁ ˆéÉl‰±åÁ ‰t°‰Í¥µ¥±…É¥ÑäˆéÍ¥´¡Él‰¡•‰É•Ü‰t±Él‰±åÁ ‰t¥ô™½ÈÈ¥¸Á…¥ÉÍuô()‘•˜µ…Á}±…¹”¡É½ÝÌ±™É••é”±ÁÉ½Ñ½½°±±…¹”±µ…Á}¹…µ”¤è(€€€™À±Ðõ•Ù…±}™¥¹•ÉÁÉ¥¹ÑÌ¡É½ÝÌ°‰±åÁ ˆ±™É••é”±ÁÉ½Ñ½½°¤ìÙÜõÙ•Ñ½É}Ý•¥¡ÑÌ¡™É••é•l‰Í¡…É•‘MÑ…Ñ•Ì‰t±™É••é•l‰Í¡…É•‘MÑ…Ñ•]•¥¡ÑÌ‰t¤ìµ¸õ¥¹Ð¡ÁÉ½Ñ½½±l‰•Ù…±Õ…Ñ¥½¸‰ul‰µ¥¹¥µÕµÙ…±Õ…Ñ¥½¹Ù•¹ÑÍA•É5…Ñ¡•‘=Á•É…Ñ½È‰t¤(€€€Á…¥ÉÌõmÈ™½ÈÈ¥¸™É••é•l‰Á…¥ÉÌ‰t¥˜ÑlÑumÉl‰±åÁ ‰utøõµ¹tì½ÁÌõmÉl‰¡•‰É•Ü‰t™½ÈÈ¥¸Á…¥ÉÍtì}™½ÈõíÉl‰¡•‰É•Ü‰téÉl‰±åÁ ‰t™½ÈÈ¥¸Á…¥ÉÍôì±…‰•±Ìõ™É••é•l‰…¹¹½Ñ…Ñ¥½¹5…ÁÌ‰umµ…Á}¹…µ•t(€€€‘•˜Í¥´¡„±ˆ¤èÉ•ÑÕÉ¸½Í¥¹”¡™Ám}™½Ém…uul‰Ù•Ñ½È‰t±™Ám}™½Ém‰uul‰Ù•Ñ½È‰t±ÙÜ¤(€€€‘•˜Í½É”¡±…‰µ…À¤è(€€€€€€€Á•ÈõmtìÉ•±…Ñ•‘}Á…¥ÉÌõmtìÕ¹É•±…Ñ•‘}Á…¥ÉÌõmt(€€€€€€€™½È¤±„¥¸•¹Õµ•É…Ñ”¡½ÁÌ¤è(€€€€€€€€€€€É•°õmˆ™½Èˆ¥¸½ÁÌ¥˜ˆ„õ„…¹É•±…Ñ¥½¸¡±…‰µ…À±„±ˆ¥tìÕ¸õmˆ™½Èˆ¥¸½ÁÌ¥˜ˆ„õ„…¹¹½ÐÉ•±…Ñ¥½¸¡±…‰µ…À±„±ˆ¥t(€€€€€€€€€€€¥˜É•°…¹Õ¸èÁ•È¹…ÁÁ•¹¡ÍÕ´¡Í¥´¡„±ˆ¤™½Èˆ¥¸É•°¤½±•¸¡É•°¤µÍÕ´¡Í¥´¡„±ˆ¤™½Èˆ¥¸Õ¸¤½±•¸¡Õ¸¤¤(€€€€€€€™½È¤±„¥¸•¹Õµ•É…Ñ”¡½ÁÌ¤è(€€€€€€€€€€€™½Èˆ¥¸½ÁÍm¤¬Äétè(€€€€€€€€€€€€€€€€¡É•±…Ñ•‘}Á…¥ÉÌ¥˜É•±…Ñ¥½¸¡±…‰µ…À±„±ˆ¤•±Í”Õ¹É•±…Ñ•‘}Á…¥ÉÌ¤¹…ÁÁ•¹¡Í¥´¡„±ˆ¤¤(€€€€€€€ÁÉ¥µ…ÉäõÍÕ´¡Á•È¤½±•¸¡Á•È¤¥˜Á•È•±Í”€À¸ÀìÍ•½¹‘…Éäô¡ÍÕ´¡É•±…Ñ•‘}Á…¥ÉÌ¤½±•¸¡É•±…Ñ•‘}Á…¥ÉÌ¤µÍÕ´¡Õ¹É•±…Ñ•‘}Á…¥ÉÌ¤½±•¸¡Õ¹É•±…Ñ•‘}Á…¥ÉÌ¤¤¥˜É•±…Ñ•‘}Á…¥ÉÌ…¹Õ¹É•±…Ñ•‘}Á…¥ÉÌ•±Í”€À¸À(€€€€€€€É•ÑÕÉ¸ÁÉ¥µ…Éä±Í•½¹‘…Éä±±•¸¡Á•È¤±±•¸¡É•±…Ñ•‘}Á…¥ÉÌ¤±±•¸¡Õ¹É•±…Ñ•‘}Á…¥ÉÌ¤(€€€…ÑÕ…°õÍ½É”¡±…‰•±Ì¤ìÁŒõ¥¹Ð¡ÁÉ½Ñ½½±l‰•Ù…±Õ…Ñ¥½¸‰ul‰Á•ÉµÕÑ…Ñ¥½¹½Õ¹Ð‰t¤ìÉ¹œõÉ…¹‘½´¹I…¹‘½´¡ÁÉ½Ñ½½±l‰•Ù…±Õ…Ñ¥½¸‰ul‰µ…ÁA•ÉµÕÑ…Ñ¥½¹M••‰t¬ˆèˆ­±…¹”¬ˆèˆ­µ…Á}¹…µ”¤ì‰Õ¹‘±•Ìõm±…‰•±Ì¹•Ð¡¼±mt¤™½È¼¥¸½ÁÍtì¹Õ±°õmt(€€€™½È|¥¸É…¹”¡ÁŒ¤è(€€€€€€€Àõ‰Õ¹‘±•ÍlétìÉ¹œ¹Í¡Õ™™±”¡À¤ì±…ˆõí¼é±¥ÍÐ¡Ø¤™½È¼±Ø¥¸é¥À¡½ÁÌ±À¥ôì¹Õ±°¹…ÁÁ•¹¡Í½É”¡±…ˆ¥lÁt¤(€€€ÁÙ…°ô Ä­ÍÕ´¡àøõ…ÑÕ…±lÁt™½Èà¥¸¹Õ±°¤¤¼ Ä­ÁŒ¤ìµÔõÍÕ´¡¹Õ±°¤½±•¸¡¹Õ±°¤¥˜¹Õ±°•±Í”€À¸ÀìÍõµ…Ñ ¹ÍÅÉÐ¡ÍÕ´ ¡àµµÔ¤¨¨È™½Èà¥¸¹Õ±°¤½µ…à Ä±±•¸¡¹Õ±°¤´Ä¤¤¥˜±•¸¡¹Õ±°¤øÄ•±Í”€À¸Àìèô¡…ÑÕ…±lÁtµµÔ¤½Í¥˜ÍøÀ•±Í”€À¸À(€€€…Ñ•ÌõÁÉ½Ñ½½±l‰•Ù…±Õ…Ñ¥½¸‰ul‰µ…Á…Ñ•ÍA•É1…¹”‰t(€€€Á…ÍÍ•ô¡…ÑÕ…±lÁtù™±½…Ð¡…Ñ•Íl‰½Á•É…Ñ½É	…±…¹•‘I•±…Ñ•‘‘Ù…¹Ñ…•É•…Ñ•ÉQ¡…¸‰t¤…¹ÁÙ…°ðõ™±½…Ð¡…Ñ•Íl‰…¹¹½Ñ…Ñ¥½¹A•ÉµÕÑ…Ñ¥½¹AÑ5½ÍÐ‰t¤…¹…ÑÕ…±lÍtøõ¥¹Ð¡…Ñ•Íl‰µ¥¹¥µÕµI•±…Ñ•‘A…¥É½Õ¹Ð‰t¤…¹…ÑÕ…±lÑtøõ¥¹Ð¡…Ñ•Íl‰µ¥¹¥µÕµU¹É•±…Ñ•‘A…¥É½Õ¹Ð‰t¤¤(€€€É•ÑÕÉ¸ì‰µ…Àˆéµ…Á}¹…µ”°‰•Ù…±Õ…‰±•=Á•É…Ñ½ÉÌˆé±•¸¡½ÁÌ¤°‰½Á•É…Ñ½É	…±…¹•‘‘Ù…¹Ñ…”ˆé…ÑÕ…±lÁt°‰Á…¥ÉÝ¥Í•‘Ù…¹Ñ…”ˆé…ÑÕ…±lÅt°‰½Á•É…Ñ½ÉÍ]¥Ñ¡	½Ñ ˆé…ÑÕ…±lÉt°‰É•±…Ñ•‘A…¥ÉÌˆé…ÑÕ…±lÍt°‰Õ¹É•±…Ñ•‘A…¥ÉÌˆé…ÑÕ…±lÑt°‰Á•ÉµÕÑ…Ñ¥½¹@ˆéÁÙ…°°‰Á•ÉµÕÑ…Ñ¥½¹hˆéè°‰Á…ÍÌˆéÁ…ÍÍ•‘ô()‘•˜…‘©Õ‘¥…Ñ”¡Á…¥É¥¹œ±µ…ÁÌ¤è(€€€¥˜¹½ÐÁ…¥É¥¹l‰¡½±‘½ÕÐ‰ul‰Á…ÍÌ‰t½È¹½ÐÁ…¥É¥¹l‰½¹ÑÉ½°‰ul‰Á…ÍÌ‰tèÉ•ÑÕÉ¸€‰M=9}=YI}A%I%9}=M}9=Q}QI9MHˆ(€€€Ý¥¹¹•ÉÌõm´™½È´¥¸€ ‰Í½¹œˆ°‰½¹Ù•¹Ñ¥½¹…°ˆ°‰‰±¥¹ˆ¤¥˜µ…ÁÍmµul‰¡½±‘½ÕÐ‰ul‰Á…ÍÌ‰t…¹µ…ÁÍmµul‰½¹ÑÉ½°‰ul‰Á…ÍÌ‰ut(€€€¥˜¹½ÐÝ¥¹¹•ÉÌèÉ•ÑÕÉ¸€‰9=}99=QQ%=9}5A}QI9MILˆ(€€€¥˜±•¸¡Ý¥¹¹•ÉÌ¤øÄèÉ•ÑÕÉ¸€‰5U1Q%A1}5AM}QI9MI}]%Q!=UQ}1I}]%99Hˆ(€€€É•ÑÕÉ¸ì‰Í½¹œˆè‰M=9}U9Q%=91}5A}AI%QM}1eA!}MQIUQUIˆ°‰½¹Ù•¹Ñ¥½¹…°ˆè‰=9Y9Q%=91}5A}AI%QM}1eA!}MQIUQUIˆ°‰‰±¥¹ˆè‰	1%9}!	I]}MQIUQUI}MU%%9P‰õmÝ¥¹¹•ÉÍlÁut(