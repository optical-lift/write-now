#!/usr/bin/env python3
import hashlib, json, math, random, re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

OUTCOMES=("SAME_CURRENT","REPEAT_H1","REPEAT_H2","REPEAT_H3","REPEAT_H4","SEEN_EARLIER_SEGMENT","NEW_SEGMENT","END")
START="<START>"
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

def parse_hebrew_wlc(wlc_dir,protocol):
    split=protocol["hebrewSplit"]; lanes={"train":[],"holdout":[],"control":[]}; counts=Counter(); books=Counter()
    bsets={"train":set(split["trainBuckets"]),"holdout":set(split["holdoutBuckets"]),"control":set(split["controlBuckets"])}
    for p in sorted(Path(wlc_dir).glob("*.xml")):
        root=ET.parse(p).getroot()
        for verse in root.findall(".//osis:verse",NS):
            vid=verse.attrib.get("osisID")
            if not vid: continue
            b=bucket(vid,int(split["modulus"])); lane=next((k for k,v in bsets.items() if b in v),None)
            if lane is None: raise RuntimeError(f"unassigned Hebrew bucket {b}")
            toks=[]
            for w in verse.findall(".//osis:w",NS):
                nums=re.findall(r"\d+",w.attrib.get("lemma",""))
                if not nums: continue
                toks.append("H"+nums[0])
            if len(toks)<1: continue
            anon="V"+hashlib.sha256(vid.encode()).hexdigest()[:20]
            lanes[lane].append({"anonymousUnitId":anon,"lane":lane,"tokens":toks})
            counts[lane]+=len(toks); books[(lane,p.stem)]+=1
    for lane in lanes: lanes[lane].sort(key=lambda r:r["anonymousUnitId"])
    manifest={"schema":"mark_hebrew_blind_split_v15","sourceCommit":protocol["hebrewSource"]["commit"],"unitCounts":{k:len(v) for k,v in lanes.items()},"tokenCounts":dict(counts),"bookUnitCounts":{f"{k[0]}:{k[1]}":v for k,v in books.items()}}
    return lanes,manifest

def glyph_segments(row):
    seg=[]
    for word in row["words"]:
        if word=="\n":
            if seg: yield seg; seg=[]
        else: seg.extend(list(word))
    if seg: yield seg

def canonical_history(seq,i,L):
    hist=[START]*max(0,L-i)+seq[max(0,i-L):i]
    seen={}; out=[]
    for x in hist:
        if x==START: out.append(START); continue
        if x not in seen: seen[x]=f"A{len(seen)}"
        out.append(seen[x])
    return tuple(out)

def consequence(seq,i,L):
    if i+1>=len(seq): return "END"
    y=seq[i+1]; cur=seq[i]
    if y==cur: return "SAME_CURRENT"
    for k in range(1,L+1):
        j=i-k
        if j>=0 and y==seq[j]: return f"REPEAT_H{k}"
    if y in seq[:max(0,i-L)]: return "SEEN_EARLIER_SEGMENT"
    return "NEW_SEGMENT"

def event_rows_from_segments(segments,L):
    out=[]
    for unit,seq in segments:
        for i,op in enumerate(seq):
            out.append({"unit":unit,"state":canonical_json(canonical_history(seq,i,L)),"operator":op,"outcome":consequence(seq,i,L)})
    return out

def hebrew_events(rows,protocol):
    L=int(protocol["projector"]["historyLength"])
    return event_rows_from_segments(((r["anonymousUnitId"],r["tokens"]) for r in rows),L)
def glyph_events(rows,protocol):
    L=int(protocol["projector"]["historyLength"]); segs=[]
    for r in rows:
        for j,s in enumerate(glyph_segments(r)): segs.append((f'{r["anonymousInscriptionId"]}:{j}',s))
    return event_rows_from_segments(segs,L)

def corpus_tables(events):
    state=defaultdict(Counter); sop=defaultdict(Counter); sn=Counter(); sopn=Counter(); opn=Counter()
    for e in events:
        S,o,y=e["state"],e["operator"],e["outcome"]
        state[S][y]+=1; sn[S]+=1; sop[(S,o)][y]+=1; sopn[(S,o)]+=1; opn[o]+=1
    return state,sop,sn,sopn,opn

def select_shared_states(hev,gev,protocol):
    th=int(protocol["training"]["minimumSharedStateEventsPerCorpus"])
    hs=corpus_tables(hev)[2]; gs=corpus_tables(gev)[2]
    keep=sorted(s for s in set(hs)&set(gs) if hs[s]>=th and gs[s]>=th)
    return keep,hs,gs

def select_operators(events,states,protocol):
    cfg=protocol["training"]; _,_,_,sopn,opn=corpus_tables(events)
    mn=int(cfg["minimumOperatorEvents"]); msc=int(cfg["minimumOperatorStateEventsForCoverage"]); need=int(cfg["minimumCoveredSharedStates"])
    ok=[]
    for op,n in opn.items():
        cov=sum(sopn[(S,op)]>=msc for S in states)
        if n>=mn and cov>=need: ok.append((op,n,cov))
    ok.sort(key=lambda x:(-x[1],x[0])); return ok[:int(cfg["maximumOperatorsPerCorpus"])]

def baseline_dist(counter,n,alpha):
    V=len(OUTCOMES); return {y:(counter[y]+alpha)/(n+alpha*V) for y in OUTCOMES}
def op_dist(counter,n,base,lam):
    if n<=0: return dict(base)
    return {y:(counter[y]+lam*base[y])/(n+lam) for y in OUTCOMES}

def build_fingerprints(events,states,operators,shared_weights,protocol):
    state,sop,sn,sopn,_=corpus_tables(events); cfg=protocol["training"]
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

def pair_similarities(hfp,gfp,states,shared_weights,protocol):
    floor=float(protocol["training"]["minimumFingerprintNorm"]); weights=[]
    for S in states: weights.extend([shared_weights[S]]*len(OUTCOMES))
    H=[h for h,d in hfp.items() if d["norm"]>=floor]; G=[g for g,d in gfp.items() if d["norm"]>=floor]
    sims={(h,g):cosine(hfp[h]["vector"],gfp[g]["vector"],weights) for h in H for g in G}
    return H,G,sims,weights

def mutual_nearest_pairs(H,G,sims,h_support,g_support):
    hb={h:max(G,key=lambda g:(sims[(h,g)],g)) for h in H}; gb={g:max(H,key=lambda h:(sims[(h,g)],h)) for g in G}
    pairs=[]
    for h,g in hb.items():
        if gb[g]!=h: continue
        pairs.append({"hebrew":h,"glyph":g,"trainSimilarity":sims[(h,g)],"hebrewTrainSupport":int(h_support[h]),"glyphTrainSupport":int(g_support[g])})
    pairs.sort(key=lambda r:(-r["trainSimilarity"],r["hebrew"],r["glyph"]))
    vals=sorted(r["glyphTrainSupport"] for r in pairs)
    if vals:
        qs=[vals[min(len(vals)-1,int((len(vals)-1)*q))] for q in (0.25,0.5,0.75)]
        for r in pairs: r["glyphSupportStratum"]=sum(r["glyphTrainSupport"]>q for q in qs)
    return pairs

def freeze_model(hebrew_rows,glyph_rows,protocol):
    hev=hebrew_events(hebrew_rows,protocol); gev=glyph_events(glyph_rows,protocol)
    states,hs,gs=select_shared_states(hev,gev,protocol)
    HN=sum(hs[s] for s in states); GN=sum(gs[s] for s in states)
    raw={s:math.sqrt((hs[s]/max(1,HN))*(gs[s]/max(1,GN))) for s in states}; z=sum(raw.values()) or 1.0; sw={s:raw[s]/z for s in states}
    hop_rows=select_operators(hev,states,protocol); gop_rows=select_operators(gev,states,protocol); hop=[x[0] for x in hop_rows]; gop=[x[0] for x in gop_rows]
    hfp=build_fingerprints(hev,states,hop,sw,protocol); gfp=build_fingerprints(gev,states,gop,sw,protocol)
    H,G,sims,_=pair_similarities(hfp,gfp,states,sw,protocol)
    hsup=Counter(e["operator"] for e in hev); gsup=Counter(e["operator"] for e in gev)
    pairs=mutual_nearest_pairs(H,G,sims,hsup,gsup)
    return {"sharedStates":states,"sharedStateWeights":sw,"hebrewOperators":hop_rows,"glyphOperators":gop_rows,"pairs":pairs,"trainEventCounts":{"hebrew":len(hev),"glyph":len(gev)},"trainSharedStateCounts":{"hebrew":{s:hs[s] for s in states},"glyph":{s:gs[s] for s in states}}}

def lane_score(hebrew_rows,glyph_rows,freeze,protocol,lane):
    hev=hebrew_events(hebrew_rows,protocol); gev=glyph_events(glyph_rows,protocol); states=freeze["sharedStates"]; sw=freeze["sharedStateWeights"]
    hops=[r[0] for r in freeze["hebrewOperators"]]; gops=[r[0] for r in freeze["glyphOperators"]]
    hfp=build_fingerprints(hev,states,hops,sw,protocol); gfp=build_fingerprints(gev,states,gops,sw,protocol)
    weights=[]
    for S in states: weights.extend([sw[S]]*len(OUTCOMES))
    pairs=freeze["pairs"]
    def sim(h,g): return cosine(hfp[h]["vector"],gfp[g]["vector"],weights)
    obs=[sim(r["hebrew"],r["glyph"]) for r in pairs]; mean=sum(obs)/max(1,len(obs))
    glyph_pool=[r["glyph"] for r in pairs]; ranks=[]
    for r in pairs:
        h=r["hebrew"]; actual=sim(h,r["glyph"]); scores=sorted((sim(h,g),g) for g in glyph_pool); below=sum(s<=actual for s,g in scores)-1; denom=max(1,len(scores)-1); ranks.append(below/denom)
    med=sorted(ranks)[len(ranks)//2] if ranks else 0.0
    pc=int(protocol["evaluation"]["permutationCount"]); seed=protocol["evaluation"]["permutationSeed"]+":"+lane
    def pvalue(stratified,salt):
        rng=random.Random(seed+":"+salt); ge=0
        for _ in range(pc):
            assigned={}
            if stratified:
                groups=defaultdict(list)
                for i,r in enumerate(pairs): groups[r.get("glyphSupportStratum",0)].append(i)
                for inds in groups.values():
                    vals=[pairs[i]["glyph"] for i in inds]; rng.shuffle(vals)
                    for i,g in zip(inds,vals): assigned[i]=g
            else:
                vals=[r["glyph"] for r in pairs]; rng.shuffle(vals)
                for i,g in enumerate(vals): assigned[i]=g
            m=sum(sim(r["hebrew"],assigned[i]) for i,r in enumerate(pairs))/max(1,len(pairs))
            if m>=mean-1e-15: ge+=1
        return (ge+1)/(pc+1)
    p_un=pvalue(False,"unstratified"); p_st=pvalue(True,"stratified")
    gates=protocol["evaluation"]["gatesPerLane"]
    gate=(len(pairs)>=int(protocol["training"]["minimumFrozenPairCount"]) and mean>float(gates["meanSimilarityGreaterThan"]) and p_un<=float(gates["unstratifiedPermutationPAtMost"]) and p_st<=float(gates["supportStratifiedPermutationPAtMost"]) and med>=float(gates["medianRankPercentileAtLeast"]))
    return {"lane":lane,"pairCount":len(pairs),"meanSimilarity":mean,"medianRankPercentile":med,"unstratifiedPermutationP":p_un,"supportStratifiedPermutationP":p_st,"gate":gate,"pairSimilarities":[{"hebrew":r["hebrew"],"glyph":r["glyph"],"similarity":s,"rankPercentile":rp} for r,s,rp in zip(pairs,obs,ranks)]}
