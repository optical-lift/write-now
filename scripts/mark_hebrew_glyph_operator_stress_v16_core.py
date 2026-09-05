#!/usr/bin/env python3
import hashlib, json, math, random, re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

OUTCOMES=("SAME_CURRENT","REPEAT_H1","REPEAT_H2","REPEAT_H3","REPEAT_H4","OTHER")
NS={"osis":"http://www.bibletechnologies.net/2003/OSIS/namespace"}

def canonical_json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def sha256_json(v): return hashlib.sha256(canonical_json(v).encode()).hexdigest()
def sha256_file(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""): h.update(b)
    return h.hexdigest()
def read_json(path): return json.loads(Path(path).read_text(encoding="utf-8"))
def write_json(path,v):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True); p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
def read_jsonl(path):
    out=[]
    with open(path,encoding="utf-8") as f:
        for line in f:
            if line.strip(): out.append(json.loads(line))
    return out

def bucket(s,mod=10): return int.from_bytes(hashlib.sha256(s.encode()).digest()[:8],"big")%mod

def morph_is_proper(morph):
    return any(part.endswith("Np") for part in (morph or "").split("/") if part)

def parse_hebrew_wlc(wlc_dir,protocol):
    split=protocol["hebrewSplit"]; lanes={"train":[],"holdout":[],"control":[]}; counts=Counter(); proper=Counter(); books=Counter()
    bsets={"train":set(split["trainBuckets"]),"holdout":set(split["holdoutBuckets"]),"control":set(split["controlBuckets"])}
    for p in sorted(Path(wlc_dir).glob("*.xml")):
        root=ET.parse(p).getroot()
        for verse in root.findall(".//osis:verse",NS):
            vid=verse.attrib.get("osisID")
            if not vid: continue
            b=bucket(vid,int(split["modulus"])); lane=next((k for k,v in bsets.items() if b in v),None)
            if lane is None: raise RuntimeError(f"unassigned Hebrew bucket {b}")
            toks=[]; pm=[]
            for w in verse.findall(".//osis:w",NS):
                nums=re.findall(r"\d+",w.attrib.get("lemma",""))
                if not nums: continue
                toks.append("H"+nums[0]); isprop=morph_is_proper(w.attrib.get("morph","")); pm.append(isprop); proper[lane]+=int(isprop)
            if not toks: continue
            anon="V"+hashlib.sha256(vid.encode()).hexdigest()[:20]
            lanes[lane].append({"anonymousUnitId":anon,"lane":lane,"tokens":toks,"properMask":pm})
            counts[lane]+=len(toks); books[(lane,p.stem)]+=1
    for lane in lanes: lanes[lane].sort(key=lambda r:r["anonymousUnitId"])
    manifest={"schema":"mark_hebrew_blind_split_v16","sourceCommit":protocol["hebrewSource"]["commit"],"unitCounts":{k:len(v) for k,v in lanes.items()},"tokenCounts":dict(counts),"properTaggedTokenCounts":dict(proper),"bookUnitCounts":{f"{k[0]}:{k[1]}":v for k,v in books.items()}}
    return lanes,manifest

def glyph_segments(row):
    seg=[]; j=0
    for word in row["words"]:
        if word=="\n":
            if seg: yield j,seg; j+=1; seg=[]
        else: seg.extend(list(word))
    if seg: yield j,seg

def canonical_history(seq,i,L):
    if i<L: raise RuntimeError("V16 internal projector received boundary position")
    hist=seq[i-L:i]; seen={}; out=[]
    for x in hist:
        if x not in seen: seen[x]=f"A{len(seen)}"
        out.append(seen[x])
    return tuple(out)

def consequence(seq,i,L):
    if i<L or i+1>=len(seq): raise RuntimeError("V16 consequence called outside internal position")
    y=seq[i+1]; cur=seq[i]
    if y==cur: return "SAME_CURRENT"
    for k in range(1,L+1):
        if y==seq[i-k]: return f"REPEAT_H{k}"
    return "OTHER"

def selected_internal_indices(unit,seq,protocol):
    cfg=protocol["projector"]; L=int(cfg["historyLength"]); n=len(seq)
    if n<int(cfg["minimumSegmentLength"]) or n>int(cfg["maximumSegmentLength"]): return []
    inds=list(range(L,n-1)); seed=cfg["eventSelectionSeed"]
    inds.sort(key=lambda i:hashlib.sha256(f"{seed}|{unit}|{i}".encode()).digest())
    return sorted(inds[:int(cfg["maximumEventsPerSegment"])])

def event_rows_from_segments(segments,protocol):
    L=int(protocol["projector"]["historyLength"]); out=[]
    for unit,seq,proper_mask in segments:
        for i in selected_internal_indices(unit,seq,protocol):
            out.append({"unit":unit,"state":canonical_json(canonical_history(seq,i,L)),"operator":seq[i],"outcome":consequence(seq,i,L),"currentProper":bool(proper_mask[i]) if proper_mask is not None else False})
    return out

def hebrew_events(rows,protocol):
    return event_rows_from_segments(((r["anonymousUnitId"],r["tokens"],r.get("properMask",[False]*len(r["tokens"]))) for r in rows),protocol)
def glyph_events(rows,protocol):
    segs=[]
    for r in rows:
        for j,s in glyph_segments(r): segs.append((f'{r["anonymousInscriptionId"]}:{j}',s,None))
    return event_rows_from_segments(segs,protocol)

def corpus_tables(events):
    state=defaultdict(Counter); sop=defaultdict(Counter); sn=Counter(); sopn=Counter(); opn=Counter(); prop=Counter()
    for e in events:
        S,o,y=e["state"],e["operator"],e["outcome"]
        state[S][y]+=1; sn[S]+=1; sop[(S,o)][y]+=1; sopn[(S,o)]+=1; opn[o]+=1; prop[o]+=int(e.get("currentProper",False))
    return state,sop,sn,sopn,opn,prop

def select_shared_states(hev,gev,protocol):
    th=int(protocol["training"]["minimumSharedStateEventsPerCorpus"])
    hs=corpus_tables(hev)[2]; gs=corpus_tables(gev)[2]
    keep=sorted(s for s in set(hs)&set(gs) if hs[s]>=th and gs[s]>=th)
    return keep,hs,gs

def select_operators(events,states,protocol,exclude_proper=False):
    cfg=protocol["training"]; _,_,_,sopn,opn,prop=corpus_tables(events)
    mn=int(cfg["minimumOperatorEvents"]); msc=int(cfg["minimumOperatorStateEventsForCoverage"]); need=int(cfg["minimumCoveredSharedStates"])
    ok=[]
    for op,n in opn.items():
        if exclude_proper and cfg.get("excludeHebrewOperatorIfAnyTrainProperOccurrence") and prop[op]>0: continue
        cov=sum(sopn[(S,op)]>=msc for S in states)
        if n>=mn and cov>=need: ok.append((op,n,cov,int(prop[op])))
    ok.sort(key=lambda x:(-x[1],x[0])); return ok[:int(cfg["maximumOperatorsPerCorpus"])]

def frequency_percentiles(op_rows):
    arr=sorted((int(r[1]),r[0]) for r in op_rows); n=len(arr); out={}; i=0
    while i<n:
        j=i+1
        while j<n and arr[j][0]==arr[i][0]: j+=1
        mid=((i+j-1)/2)/max(1,n-1)
        for k in range(i,j): out[arr[k][1]]=mid
        i=j
    return out

def baseline_dist(counter,n,alpha):
    V=len(OUTCOMES); return {y:(counter[y]+alpha)/(n+alpha*V) for y in OUTCOMES}
def op_dist(counter,n,base,lam):
    if n<=0: return dict(base)
    return {y:(counter[y]+lam*base[y])/(n+lam) for y in OUTCOMES}

def build_fingerprints(events,states,operators,shared_weights,protocol):
    state,sop,sn,sopn,_,_=corpus_tables(events); cfg=protocol["training"]
    alpha=float(cfg["globalAdditiveAlpha"]); lam=float(cfg["backoffPseudoCount"]); clip=float(cfg["residualLog2Clip"])
    out={}
    for op in operators:
        vals=[]; weights=[]
        for S in states:
            b=baseline_dist(state[S],sn[S],alpha); q=op_dist(sop[(S,op)],sopn[(S,op)],b,lam)
            sw=shared_weights[S]
            for y in OUTCOMES:
                r=max(-clip,min(clip,math.log2(max(q[y],1e-300)/max(b[y],1e-300))))
                vals.append(r); weights.append(sw)
        norm=math.sqrt(sum(w*v*v for w,v in zip(weights,vals)))
        out[op]={"vector":vals,"norm":norm,"supportByState":{S:int(sopn[(S,op)]) for S in states}}
    return out

def cosine(a,b,weights):
    na=math.sqrt(sum(w*x*x for w,x in zip(weights,a))); nb=math.sqrt(sum(w*y*y for w,y in zip(weights,b)))
    if na<=0 or nb<=0: return 0.0
    return sum(w*x*y for w,x,y in zip(weights,a,b))/(na*nb)

def pair_similarities(hfp,gfp,states,shared_weights,hfreq,gfreq,protocol):
    floor=float(protocol["training"]["minimumFingerprintNorm"]); gap=float(protocol["training"]["maximumFrequencyPercentileGap"]); weights=[]
    for S in states: weights.extend([shared_weights[S]]*len(OUTCOMES))
    H=[h for h,d in hfp.items() if d["norm"]>=floor]; G=[g for g,d in gfp.items() if d["norm"]>=floor]
    sims={}
    for h in H:
        for g in G:
            if abs(hfreq[h]-gfreq[g])<=gap: sims[(h,g)]=cosine(hfp[h]["vector"],gfp[g]["vector"],weights)
    return H,G,sims,weights

def mutual_nearest_pairs(H,G,sims,h_support,g_support,hfreq,gfreq,protocol):
    hb={}; gb={}
    for h in H:
        candidates=[g for g in G if (h,g) in sims]
        if candidates: hb[h]=max(candidates,key=lambda g:(sims[(h,g)],g))
    for g in G:
        candidates=[h for h in H if (h,g) in sims]
        if candidates: gb[g]=max(candidates,key=lambda h:(sims[(h,g)],h))
    pairs=[]
    strata=max(1,int(protocol["training"]["frequencyNullStrata"]))
    for h,g in hb.items():
        if gb.get(g)!=h: continue
        avg=(hfreq[h]+gfreq[g])/2
        pairs.append({"hebrew":h,"glyph":g,"trainSimilarity":sims[(h,g)],"hebrewTrainSupport":int(h_support[h]),"glyphTrainSupport":int(g_support[g]),"hebrewFrequencyPercentile":hfreq[h],"glyphFrequencyPercentile":gfreq[g],"frequencyPercentileGap":abs(hfreq[h]-gfreq[g]),"frequencyStratum":min(strata-1,int(avg*strata))})
    pairs.sort(key=lambda r:(-r["trainSimilarity"],r["hebrew"],r["glyph"]))
    return pairs

def freeze_model(hebrew_rows,glyph_rows,protocol):
    hev=hebrew_events(hebrew_rows,protocol); gev=glyph_events(glyph_rows,protocol)
    states,hs,gs=select_shared_states(hev,gev,protocol)
    HN=sum(hs[s] for s in states); GN=sum(gs[s] for s in states)
    raw={s:math.sqrt((hs[s]/max(1,HN))*(gs[s]/max(1,GN))) for s in states}; z=sum(raw.values()) or 1.0; sw={s:raw[s]/z for s in states}
    hop_rows=select_operators(hev,states,protocol,exclude_proper=True); gop_rows=select_operators(gev,states,protocol,exclude_proper=False)
    hop=[x[0] for x in hop_rows]; gop=[x[0] for x in gop_rows]; hfreq=frequency_percentiles(hop_rows); gfreq=frequency_percentiles(gop_rows)
    hfp=build_fingerprints(hev,states,hop,sw,protocol); gfp=build_fingerprints(gev,states,gop,sw,protocol)
    H,G,sims,_=pair_similarities(hfp,gfp,states,sw,hfreq,gfreq,protocol)
    htab=corpus_tables(hev); gtab=corpus_tables(gev); pairs=mutual_nearest_pairs(H,G,sims,htab[4],gtab[4],hfreq,gfreq,protocol)
    excluded=sorted((o,int(n),int(htab[5][o])) for o,n in htab[4].items() if htab[5][o]>0)
    return {"sharedStates":states,"sharedStateWeights":sw,"hebrewOperators":hop_rows,"glyphOperators":gop_rows,"hebrewFrequencyPercentiles":hfreq,"glyphFrequencyPercentiles":gfreq,"pairs":pairs,"trainEventCounts":{"hebrew":len(hev),"glyph":len(gev)},"trainSharedStateCounts":{"hebrew":{s:hs[s] for s in states},"glyph":{s:gs[s] for s in states}},"excludedHebrewProperOperators":excluded}

def lane_score(hebrew_rows,glyph_rows,freeze,protocol,lane):
    hev=hebrew_events(hebrew_rows,protocol); gev=glyph_events(glyph_rows,protocol); states=freeze["sharedStates"]; sw=freeze["sharedStateWeights"]
    hops=[r[0] for r in freeze["hebrewOperators"]]; gops=[r[0] for r in freeze["glyphOperators"]]
    hfp=build_fingerprints(hev,states,hops,sw,protocol); gfp=build_fingerprints(gev,states,gops,sw,protocol)
    weights=[]
    for S in states: weights.extend([sw[S]]*len(OUTCOMES))
    hsup=corpus_tables(hev)[4]; gsup=corpus_tables(gev)[4]; allpairs=freeze["pairs"]; mn=int(protocol["evaluation"]["minimumEvaluationEventsPerOperator"])
    pairs=[r for r in allpairs if hsup[r["hebrew"]]>=mn and gsup[r["glyph"]]>=mn]
    evaluable_fraction=len(pairs)/max(1,len(allpairs))
    def sim(h,g): return cosine(hfp[h]["vector"],gfp[g]["vector"],weights)
    obs=[sim(r["hebrew"],r["glyph"]) for r in pairs]; mean=sum(obs)/max(1,len(obs)); positive=sum(x>0 for x in obs)/max(1,len(obs))
    glyph_pool=[r["glyph"] for r in pairs]; ranks=[]
    for r in pairs:
        h=r["hebrew"]; actual=sim(h,r["glyph"]); scores=[sim(h,g) for g in glyph_pool]; below=sum(s<=actual for s in scores)-1; ranks.append(below/max(1,len(scores)-1))
    med=sorted(ranks)[len(ranks)//2] if ranks else 0.0
    pc=int(protocol["evaluation"]["permutationCount"]); seed=protocol["evaluation"]["permutationSeed"]+":"+lane
    def pvalue(stratified,salt):
        rng=random.Random(seed+":"+salt); ge=0
        for _ in range(pc):
            assigned={}
            if stratified:
                groups=defaultdict(list)
                for i,r in enumerate(pairs): groups[int(r["frequencyStratum"])].append(i)
                for inds in groups.values():
                    vals=[pairs[i]["glyph"] for i in inds]; rng.shuffle(vals)
                    for i,g in zip(inds,vals): assigned[i]=g
            else:
                vals=[r["glyph"] for r in pairs]; rng.shuffle(vals)
                for i,g in enumerate(vals): assigned[i]=g
            m=sum(sim(r["hebrew"],assigned[i]) for i,r in enumerate(pairs))/max(1,len(pairs))
            if m>=mean-1e-15: ge+=1
        return (ge+1)/(pc+1)
    p_un=pvalue(False,"unstratified") if pairs else 1.0; p_st=pvalue(True,"frequency") if pairs else 1.0
    gates=protocol["evaluation"]["gatesPerLane"]
    gate=(len(allpairs)>=int(protocol["training"]["minimumFrozenPairCount"]) and len(pairs)>=int(protocol["evaluation"]["minimumEvaluablePairCount"]) and evaluable_fraction>=float(protocol["evaluation"]["minimumEvaluablePairFraction"]) and mean>float(gates["meanSimilarityGreaterThan"]) and p_un<=float(gates["unstratifiedPermutationPAtMost"]) and p_st<=float(gates["frequencyStratifiedPermutationPAtMost"]) and med>=float(gates["medianRankPercentileAtLeast"]) and positive>=float(gates["positivePairFractionAtLeast"]))
    return {"lane":lane,"frozenPairCount":len(allpairs),"evaluablePairCount":len(pairs),"evaluablePairFraction":evaluable_fraction,"meanSimilarity":mean,"positivePairFraction":positive,"medianRankPercentile":med,"unstratifiedPermutationP":p_un,"frequencyStratifiedPermutationP":p_st,"gate":gate,"eventCounts":{"hebrew":len(hev),"glyph":len(gev)},"pairSimilarities":[{"hebrew":r["hebrew"],"glyph":r["glyph"],"similarity":s,"rankPercentile":rp,"hebrewEvalSupport":int(hsup[r["hebrew"]]),"glyphEvalSupport":int(gsup[r["glyph"]])} for r,s,rp in zip(pairs,obs,ranks)]}
