#!/usr/bin/env python3
import hashlib,json,math,random,re
import xml.etree.ElementTree as ET
from collections import Counter,defaultdict
from pathlib import Path
NS={"osis":"http://www.bibletechnologies.net/2003/OSIS/namespace"}
START="<START>"
REPEATS=("SAME_CURRENT","REPEAT_H1","REPEAT_H2","REPEAT_H3","REPEAT_H4")

def canonical_json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha256_json(v): return hashlib.sha256(canonical_json(v).encode()).hexdigest()
def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def read_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def write_json(p,v):
    p=Path(p); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
def read_jsonl(p):
    with open(p,encoding="utf-8") as f: return [json.loads(x) for x in f if x.strip()]
def bucket(s,m=10): return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8],"big")%m
def is_proper(m): return any(x.endswith("Np") for x in (m or "").split("/") if x)

def parse_hebrew_wlc(wlc,protocol):
    split=protocol["hebrewSplit"]; lanes={k:[] for k in ("train","holdout","control")}
    sets={"train":set(split["trainBuckets"]),"holdout":set(split["holdoutBuckets"]),"control":set(split["controlBuckets"])}
    counts=Counter(); props=Counter()
    for p in sorted(Path(wlc).glob("*.xml")):
        root=ET.parse(p).getroot()
        for verse in root.findall(".//osis:verse",NS):
            vid=verse.attrib.get("osisID")
            if not vid: continue
            b=bucket(vid,int(split["modulus"])); lane=next(k for k,s in sets.items() if b in s)
            toks=[]; pm=[]
            for w in verse.findall(".//osis:w",NS):
                nums=re.findall(r"\d+",w.attrib.get("lemma",""))
                if not nums: continue
                toks.append("H"+nums[0]); q=is_proper(w.attrib.get("morph","")); pm.append(q); props[lane]+=int(q)
            if not toks: continue
            lanes[lane].append({"anonymousUnitId":"V"+hashlib.sha256(vid.encode()).hexdigest()[:20],"lane":lane,"tokens":toks,"properMask":pm})
            counts[lane]+=len(toks)
    for k in lanes: lanes[k].sort(key=lambda r:r["anonymousUnitId"])
    return lanes,{"schema":"mark_hebrew_blind_split_v18","sourceCommit":protocol["hebrewSource"]["commit"],"unitCounts":{k:len(v) for k,v in lanes.items()},"tokenCounts":dict(counts),"properTaggedTokenCounts":dict(props)}

def hebrew_segments(rows):
    for r in rows: yield r["anonymousUnitId"],r["tokens"],r.get("properMask",[False]*len(r["tokens"]))
def glyph_segments(rows):
    for r in rows:
        seg=[]; j=0
        for w in r["words"]:
            if w=="\n":
                if seg: yield f'{r["anonymousInscriptionId"]}:{j}',seg,None; j+=1; seg=[]
            else: seg.extend(list(w))
        if seg: yield f'{r["anonymousInscriptionId"]}:{j}',seg,None

def controls(v): return set(v.get("controls",[]))
def outcomes(v):
    o=list(REPEATS)
    if "seenNew" in controls(v): o.append("OTHER")
    else: o += ["SEEN_EARLIER_SEGMENT","NEW_SEGMENT"]
    if "boundary" not in controls(v): o.append("END")
    return tuple(o)

def hist(seq,i,internal):
    L=4
    h=seq[i-L:i] if internal else [START]*max(0,L-i)+seq[max(0,i-L):i]
    seen={}; out=[]
    for x in h:
        if x==START: out.append(x)
        else:
            if x not in seen: seen[x]=f"A{len(seen)}"
            out.append(seen[x])
    return canonical_json(out)

def consequence(seq,i,v):
    if i+1>=len(seq): return "END"
    y=seq[i+1]
    if y==seq[i]: return "SAME_CURRENT"
    for k in range(1,5):
        if i-k>=0 and y==seq[i-k]: return f"REPEAT_H{k}"
    if "seenNew" in controls(v): return "OTHER"
    return "SEEN_EARLIER_SEGMENT" if y in seq[:max(0,i-4)] else "NEW_SEGMENT"

def raw_events(segments,v,protocol):
    c=controls(v); sc=protocol["controls"]["segment"]; out=[]
    for unit,seq,pm in segments:
        n=len(seq)
        if "segment" in c and not (int(sc["minimumSegmentLength"])<=n<=int(sc["maximumSegmentLength"])): continue
        inds=list(range(4,n-1)) if "boundary" in c else list(range(n))
        if "segment" in c and len(inds)>int(sc["maximumEventsPerSegment"]):
            seed=sc["eventSelectionSeed"]
            inds=sorted(inds,key=lambda i:hashlib.sha256(f"{seed}|{unit}|{i}".encode()).digest())[:int(sc["maximumEventsPerSegment"])]
        for i in sorted(inds):
            out.append({"eventId":f"{unit}:{i}","state":hist(seq,i,"boundary" in c),"operator":seq[i],"outcome":consequence(seq,i,v),"currentProper":bool(pm[i]) if pm is not None else False})
    return out

def events(rows,kind,v,protocol,variant_map):
    factory=hebrew_segments if kind=="hebrew" else glyph_segments
    if v.get("shamOf"):
        base=raw_events(factory(rows),variant_map["baseline"],protocol)
        target=raw_events(factory(rows),variant_map[v["shamOf"]],protocol)
        seed=protocol["controls"]["volumeSham"]["eventSelectionSeed"]
        base.sort(key=lambda e:hashlib.sha256(f"{seed}|{v['id']}|{e['eventId']}".encode()).digest())
        return base[:min(len(base),len(target))]
    return raw_events(factory(rows),v,protocol)

def tables(ev):
    state=defaultdict(Counter); sop=defaultdict(Counter); sn=Counter(); sopn=Counter(); opn=Counter()
    for e in ev:
        S,o,y=e["state"],e["operator"],e["outcome"]; state[S][y]+=1; sn[S]+=1; sop[(S,o)][y]+=1; sopn[(S,o)]+=1; opn[o]+=1
    return state,sop,sn,sopn,opn

def raw_propers(rows):
    s=set()
    for r in rows:
        for o,p in zip(r["tokens"],r.get("properMask",[])):
            if p:s.add(o)
    return s

def freqpct(rows):
    arr=sorted((int(r[1]),r[0]) for r in rows); n=len(arr); out={}; i=0
    while i<n:
        j=i+1
        while j<n and arr[j][0]==arr[i][0]: j+=1
        mid=((i+j-1)/2)/max(1,n-1)
        for k in range(i,j): out[arr[k][1]]=mid
        i=j
    return out

def freeze_variant(hrows,grows,v,protocol,variant_map,properU):
    cfg=protocol["exactV15"]["training"]; he=events(hrows,"hebrew",v,protocol,variant_map); ge=events(grows,"glyph",v,protocol,variant_map)
    ht=tables(he); gt=tables(ge)
    states=sorted(S for S in set(ht[2])&set(gt[2]) if ht[2][S]>=cfg["minimumSharedStateEventsPerCorpus"] and gt[2][S]>=cfg["minimumSharedStateEventsPerCorpus"])
    HN=sum(ht[2][S] for S in states); GN=sum(gt[2][S] for S in states)
    rw={S:math.sqrt((ht[2][S]/max(1,HN))*(gt[2][S]/max(1,GN))) for S in states}; z=sum(rw.values()) or 1.; sw={S:rw[S]/z for S in states}
    def select(tab,excluded=set()):
        out=[]
        for op,n in tab[4].items():
            if op in excluded: continue
            cov=sum(tab[3][(S,op)]>=cfg["minimumOperatorStateEventsForCoverage"] for S in states)
            if n>=cfg["minimumOperatorEvents"] and cov>=cfg["minimumCoveredSharedStates"]: out.append((op,int(n),int(cov)))
        out.sort(key=lambda x:(-x[1],x[0])); return out[:cfg["maximumOperatorsPerCorpus"]]
    hr=select(ht,properU if "proper" in controls(v) else set()); gr=select(gt)
    H=[x[0] for x in hr]; G=[x[0] for x in gr]; hf=freqpct(hr); gf=freqpct(gr); outs=outcomes(v)
    def fps(tab,ops):
        d={}
        for op in ops:
            vals=[]; ws=[]
            for S in states:
                a=cfg["globalAdditiveAlpha"]; V=len(outs); b={y:(tab[0][S][y]+a)/(tab[2][S]+a*V) for y in outs}; n=tab[3][(S,op)]; lam=cfg["backoffPseudoCount"]
                q={y:(tab[1][(S,op)][y]+lam*b[y])/(n+lam) if n else b[y] for y in outs}
                for y in outs:
                    r=max(-cfg["residualLog2Clip"],min(cfg["residualLog2Clip"],math.log2(max(q[y],1e-300)/max(b[y],1e-300))))
                    vals.append(r); ws.append(sw[S])
            d[op]={"vector":vals,"norm":math.sqrt(sum(w*x*x for w,x in zip(ws,vals)))}
        return d
    hfp=fps(ht,H); gfp=fps(gt,G); weights=[]
    for S in states: weights += [sw[S]]*len(outs)
    def cos(a,b):
        na=math.sqrt(sum(w*x*x for w,x in zip(weights,a))); nb=math.sqrt(sum(w*y*y for w,y in zip(weights,b)))
        return sum(w*x*y for w,x,y in zip(weights,a,b))/(na*nb) if na and nb else 0.
    HH=[h for h in H if hfp[h]["norm"]>=cfg["minimumFingerprintNorm"]]; GG=[g for g in G if gfp[g]["norm"]>=cfg["minimumFingerprintNorm"]]; sims={}
    gap=protocol["controls"]["frequency"]["maximumFrequencyPercentileGap"]
    for h in HH:
        for g in GG:
            if "frequency" in controls(v) and abs(hf[h]-gf[g])>gap: continue
            sims[(h,g)]=cos(hfp[h]["vector"],gfp[g]["vector"])
    hb={h:max([g for g in GG if (h,g) in sims],key=lambda g:(sims[(h,g)],g)) for h in HH if any((h,g) in sims for g in GG)}
    gb={g:max([h for h in HH if (h,g) in sims],key=lambda h:(sims[(h,g)],h)) for g in GG if any((h,g) in sims for h in HH)}
    pairs=[]
    for h,g in hb.items():
        if gb.get(g)==h: pairs.append({"hebrew":h,"glyph":g,"trainSimilarity":sims[(h,g)],"hebrewTrainSupport":int(ht[4][h]),"glyphTrainSupport":int(gt[4][g])})
    pairs.sort(key=lambda r:(-r["trainSimilarity"],r["hebrew"],r["glyph"]))
    vals=sorted(r["glyphTrainSupport"] for r in pairs)
    if vals:
        qs=[vals[min(len(vals)-1,int((len(vals)-1)*q))] for q in (.25,.5,.75)]
        for r in pairs:r["glyphSupportStratum"]=sum(r["glyphTrainSupport"]>q for q in qs)
    return {"variantSpec":v,"outcomes":list(outs),"sharedStates":states,"sharedStateWeights":sw,"hebrewOperators":hr,"glyphOperators":gr,"pairs":pairs,"trainEventCounts":{"hebrew":len(he),"glyph":len(ge)}}

def freeze_all(hrows,grows,protocol):
    vm={v["id"]:v for v in protocol["variants"]}; pu=raw_propers(hrows)
    return {"variants":{v["id"]:freeze_variant(hrows,grows,v,protocol,vm,pu) for v in protocol["variants"]},"properOperatorUniverseCount":len(pu)}

def lane_score(hrows,grows,fz,protocol,lane):
    v=fz["variantSpec"]; vm={x["id"]:x for x in protocol["variants"]}; he=events(hrows,"hebrew",v,protocol,vm); ge=events(grows,"glyph",v,protocol,vm)
    ht=tables(he); gt=tables(ge); cfg=protocol["exactV15"]["training"]; outs=tuple(fz["outcomes"]); states=fz["sharedStates"]; sw=fz["sharedStateWeights"]
    H=[r[0] for r in fz["hebrewOperators"]]; G=[r[0] for r in fz["glyphOperators"]]
    def fps(tab,ops):
        d={}
        for op in ops:
            vals=[]; ws=[]
            for S in states:
                a=cfg["globalAdditiveAlpha"];V=len(outs);b={y:(tab[0][S][y]+a)/(tab[2][S]+a*V) for y in outs};n=tab[3][(S,op)];lam=cfg["backoffPseudoCount"]
                q={y:(tab[1][(S,op)][y]+lam*b[y])/(n+lam) if n else b[y] for y in outs}
                for y in outs:
                    r=max(-cfg["residualLog2Clip"],min(cfg["residualLog2Clip"],math.log2(max(q[y],1e-300)/max(b[y],1e-300))))
                    vals.append(r);ws.append(sw[S])
            d[op]=vals
        return d
    hfp=fps(ht,H);gfp=fps(gt,G);weights=[]
    for S in states:weights += [sw[S]]*len(outs)
    def sim(h,g):
        a=hfp[h];b=gfp[g];na=math.sqrt(sum(w*x*x for w,x in zip(weights,a)));nb=math.sqrt(sum(w*y*y for w,y in zip(weights,b)))
        return sum(w*x*y for w,x,y in zip(weights,a,b))/(na*nb) if na and nb else 0.
    pairs=fz["pairs"]; obs=[sim(r["hebrew"],r["glyph"]) for r in pairs]; mean=sum(obs)/max(1,len(obs)); glyphs=[r["glyph"] for r in pairs]; ranks=[]
    for r in pairs:
        actual=sim(r["hebrew"],r["glyph"]); scores=[sim(r["hebrew"],g) for g in glyphs]; ranks.append((sum(s<=actual for s in scores)-1)/max(1,len(scores)-1))
    med=sorted(ranks)[len(ranks)//2] if ranks else 0.
    ecfg=protocol["exactV15"]["evaluation"]; pc=ecfg["permutationCount"]; seed=(ecfg["baselinePermutationSeed"] if v["id"]=="baseline" else ecfg["variantPermutationSeed"]+":"+v["id"])+":"+lane
    def pv(mode):
        if not pairs:return 1.
        rng=random.Random(seed+":"+mode); geq=0
        for _ in range(pc):
            assigned={}
            if mode=="stratified":
                groups=defaultdict(list)
                for i,r in enumerate(pairs):groups[r.get("glyphSupportStratum",0)].append(i)
                for inds in groups.values():
                    vals=[pairs[i]["glyph"] for i in inds];rng.shuffle(vals)
                    for i,g in zip(inds,vals):assigned[i]=g
            else:
                vals=[r["glyph"] for r in pairs];rng.shuffle(vals)
                for i,g in enumerate(vals):assigned[i]=g
            m=sum(sim(r["hebrew"],assigned[i]) for i,r in enumerate(pairs))/len(pairs)
            if m>=mean-1e-15:geq+=1
        return (geq+1)/(pc+1)
    pu=pv("unstratified");ps=pv("stratified"); gates=ecfg["gatesPerLane"]
    gate=(len(pairs)>=cfg["minimumFrozenPairCount"] and mean>gates["meanSimilarityGreaterThan"] and pu<=gates["unstratifiedPermutationPAtMost"] and ps<=gates["supportStratifiedPermutationPAtMost"] and med>=gates["medianRankPercentileAtLeast"])
    return {"pairCount":len(pairs),"meanSimilarity":mean,"medianRankPercentile":med,"unstratifiedPermutationP":pu,"supportStratifiedPermutationP":ps,"gate":gate,"pairSimilarities":[{"hebrew":r["hebrew"],"glyph":r["glyph"],"similarity":s} for r,s in zip(pairs,obs)]}

def evaluate_all(hlanes,glanes,freeze,protocol):
    out={}
    minp=protocol["exactV15"]["training"]["minimumFrozenPairCount"]
    for v in protocol["variants"]:
        f=freeze["variants"][v["id"]]; feasible=len(f["pairs"])>=minp
        lanes={l:lane_score(hlanes[l],glanes[l],f,protocol,l) for l in ("holdout","control")} if f["pairs"] else {l:{"pairCount":0,"meanSimilarity":0.,"medianRankPercentile":0.,"unstratifiedPermutationP":1.,"supportStratifiedPermutationP":1.,"gate":False,"pairSimilarities":[]} for l in ("holdout","control")}
        passed=feasible and lanes["holdout"]["gate"] and lanes["control"]["gate"]
        out[v["id"]]={"trainFeasible":feasible,"frozenPairCount":len(f["pairs"]),"fullPass":passed,"status":"PASS" if passed else ("TRAIN_FEASIBILITY_COLLAPSE" if not feasible else "TRANSFER_GATE_FAILURE"),"lanes":lanes}
    return out

def adjudicate(results,protocol):
    if not results["baseline"]["fullPass"]:
        return {"adjudication":"EXACT_V15_BASELINE_NOT_REPRODUCED","baselineStatus":results["baseline"]["status"]}
    findings={}
    for ctl,vid,sham in [("boundary","boundary_only","boundary_volume_sham"),("segment","segment_only","segment_volume_sham")]:
        r,s=results[vid],results[sham]
        if not r["trainFeasible"] and not s["trainFeasible"]: cls="SUPPORT_THINNING_CONFOUNDED"
        elif not r["fullPass"] and s["fullPass"]: cls="STRUCTURAL_BREAKER"
        elif not r["fullPass"] and not s["fullPass"]: cls="BOTH_FAIL_UNRESOLVED"
        else: cls="SURVIVES"
        findings[ctl]={"classification":cls,"controlStatus":r["status"],"volumeShamStatus":s["status"]}
    for ctl,vid in [("seenNew","seennew_only"),("proper","proper_only"),("frequency","frequency_only")]:
        r=results[vid]; findings[ctl]={"classification":("SURVIVES" if r["fullPass"] else ("TRAIN_FEASIBILITY_COLLAPSE" if not r["trainFeasible"] else "ISOLATED_BREAKER")),"status":r["status"]}
    return {"adjudication":"EXACT_V15_ABLATION_LOCALIZED","baselineStatus":"PASS","findings":findings}
