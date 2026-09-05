#!/usr/bin/env python3
import hashlib, json, math, random, re
import xml.etree.ElementTree as ET
from collections import Counter, defaultdict
from pathlib import Path

NS={"osis":"http://www.bibletechnologies.net/2003/OSIS/namespace"}
START="<START>"
BASE_REPEAT=("SAME_CURRENT","REPEAT_H1","REPEAT_H2","REPEAT_H3","REPEAT_H4")

def canonical_json(v):
    return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))

def sha256_json(v):
    return hashlib.sha256(canonical_json(v).encode("utf-8")).hexdigest()

def sha256_file(path):
    h=hashlib.sha256()
    with open(path,"rb") as f:
        for b in iter(lambda:f.read(1<<20),b""):
            h.update(b)
    return h.hexdigest()

def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))

def write_json(path,v):
    p=Path(path)
    p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")

def read_jsonl(path):
    out=[]
    with open(path,encoding="utf-8") as f:
        for line in f:
            if line.strip():
                out.append(json.loads(line))
    return out

def bucket(s,mod=10):
    return int.from_bytes(hashlib.sha256(s.encode("utf-8")).digest()[:8],"big")%mod

def morph_is_proper(morph):
    return any(part.endswith("Np") for part in (morph or "").split("/") if part)

def parse_hebrew_wlc(wlc_dir,protocol):
    split=protocol["hebrewSplit"]
    lanes={"train":[],"holdout":[],"control":[]}
    counts=Counter()
    proper=Counter()
    books=Counter()
    bsets={
        "train":set(split["trainBuckets"]),
        "holdout":set(split["holdoutBuckets"]),
        "control":set(split["controlBuckets"])
    }
    for p in sorted(Path(wlc_dir).glob("*.xml")):
        root=ET.parse(p).getroot()
        for verse in root.findall(".//osis:verse",NS):
            vid=verse.attrib.get("osisID")
            if not vid:
                continue
            b=bucket(vid,int(split["modulus"]))
            lane=next((k for k,v in bsets.items() if b in v),None)
            if lane is None:
                raise RuntimeError(f"unassigned Hebrew bucket {b}")
            toks=[]
            pm=[]
            for w in verse.findall(".//osis:w",NS):
                nums=re.findall(r"\d+",w.attrib.get("lemma",""))
                if not nums:
                    continue
                toks.append("H"+nums[0])
                isprop=morph_is_proper(w.attrib.get("morph",""))
                pm.append(isprop)
                proper[lane]+=int(isprop)
            if not toks:
                continue
            anon="V"+hashlib.sha256(vid.encode("utf-8")).hexdigest()[:20]
            lanes[lane].append({
                "anonymousUnitId":anon,
                "lane":lane,
                "tokens":toks,
                "properMask":pm
            })
            counts[lane]+=len(toks)
            books[(lane,p.stem)]+=1
    for lane in lanes:
        lanes[lane].sort(key=lambda r:r["anonymousUnitId"])
    manifest={
        "schema":"mark_hebrew_blind_split_v17",
        "sourceCommit":protocol["hebrewSource"]["commit"],
        "unitCounts":{k:len(v) for k,v in lanes.items()},
        "tokenCounts":dict(counts),
        "properTaggedTokenCounts":dict(proper),
        "bookUnitCounts":{f"{k[0]}:{k[1]}":v for k,v in books.items()}
    }
    return lanes,manifest

def glyph_segments(rows):
    for row in rows:
        seg=[]
        j=0
        for word in row["words"]:
            if word=="\n":
                if seg:
                    yield f'{row["anonymousInscriptionId"]}:{j}',seg,None
                    j+=1
                    seg=[]
            else:
                seg.extend(list(word))
        if seg:
            yield f'{row["anonymousInscriptionId"]}:{j}',seg,None

def hebrew_segments(rows):
    for row in rows:
        yield (
            row["anonymousUnitId"],
            row["tokens"],
            row.get("properMask",[False]*len(row["tokens"]))
        )

def variant_controls(variant):
    return set(variant.get("controls",[]))

def variant_outcomes(variant):
    controls=variant_controls(variant)
    out=list(BASE_REPEAT)
    if "seenNew" in controls:
        out.append("OTHER")
    else:
        out.extend(["SEEN_EARLIER_SEGMENT","NEW_SEGMENT"])
    if "boundary" not in controls:
        out.append("END")
    return tuple(out)

def canonical_history(seq,i,L,internal_only):
    if internal_only:
        if i<L:
            raise RuntimeError("internal projector received boundary position")
        hist=seq[i-L:i]
    else:
        hist=[START]*max(0,L-i)+seq[max(0,i-L):i]
    seen={}
    out=[]
    for x in hist:
        if x==START:
            out.append(START)
            continue
        if x not in seen:
            seen[x]=f"A{len(seen)}"
        out.append(seen[x])
    return tuple(out)

def consequence(seq,i,L,variant):
    controls=variant_controls(variant)
    internal="boundary" in controls
    if i+1>=len(seq):
        if internal:
            raise RuntimeError("END reached in boundary-removed variant")
        return "END"
    y=seq[i+1]
    cur=seq[i]
    if y==cur:
        return "SAME_CURRENT"
    for k in range(1,L+1):
        j=i-k
        if j>=0 and y==seq[j]:
            return f"REPEAT_H{k}"
    if "seenNew" in controls:
        return "OTHER"
    if y in seq[:max(0,i-L)]:
        return "SEEN_EARLIER_SEGMENT"
    return "NEW_SEGMENT"

def selected_indices(unit,seq,variant,protocol):
    controls=variant_controls(variant)
    cfg=protocol["controls"]["segment"]
    L=int(protocol["baseProjector"]["historyLength"])
    n=len(seq)
    if "segment" in controls:
        if n<int(cfg["minimumSegmentLength"]) or n>int(cfg["maximumSegmentLength"]):
            return []
    if "boundary" in controls:
        inds=list(range(L,n-1))
    else:
        inds=list(range(n))
    if "segment" in controls and len(inds)>int(cfg["maximumEventsPerSegment"]):
        seed=cfg["eventSelectionSeed"]
        inds.sort(key=lambda i:hashlib.sha256(f"{seed}|{unit}|{i}".encode("utf-8")).digest())
        inds=inds[:int(cfg["maximumEventsPerSegment"])]
    return sorted(inds)

def events_from_segments(segments,variant,protocol):
    L=int(protocol["baseProjector"]["historyLength"])
    out=[]
    internal="boundary" in variant_controls(variant)
    for unit,seq,proper_mask in segments:
        for i in selected_indices(unit,seq,variant,protocol):
            out.append({
                "unit":unit,
                "state":canonical_json(canonical_history(seq,i,L,internal)),
                "operator":seq[i],
                "outcome":consequence(seq,i,L,variant),
                "currentProper":bool(proper_mask[i]) if proper_mask is not None else False
            })
    return out

def hebrew_events(rows,variant,protocol):
    return events_from_segments(hebrew_segments(rows),variant,protocol)

def glyph_events(rows,variant,protocol):
    return events_from_segments(glyph_segments(rows),variant,protocol)

def corpus_tables(events):
    state=defaultdict(Counter)
    sop=defaultdict(Counter)
    sn=Counter()
    sopn=Counter()
    opn=Counter()
    for e in events:
        S,o,y=e["state"],e["operator"],e["outcome"]
        state[S][y]+=1
        sn[S]+=1
        sop[(S,o)][y]+=1
        sopn[(S,o)]+=1
        opn[o]+=1
    return state,sop,sn,sopn,opn

def raw_train_proper_operators(hebrew_rows):
    out=set()
    for row in hebrew_rows:
        for op,isprop in zip(row["tokens"],row.get("properMask",[])):
            if isprop:
                out.add(op)
    return out

def shared_states(hev,gev,protocol):
    th=int(protocol["training"]["minimumSharedStateEventsPerCorpus"])
    hs=corpus_tables(hev)[2]
    gs=corpus_tables(gev)[2]
    states=sorted(S for S in set(hs)&set(gs) if hs[S]>=th and gs[S]>=th)
    return states,hs,gs

def select_operators(events,states,protocol,excluded=None):
    cfg=protocol["training"]
    excluded=excluded or set()
    tab=corpus_tables(events)
    out=[]
    for op,n in tab[4].items():
        if op in excluded:
            continue
        cov=sum(tab[3][(S,op)]>=int(cfg["minimumOperatorStateEventsForCoverage"]) for S in states)
        if n>=int(cfg["minimumOperatorEvents"]) and cov>=int(cfg["minimumCoveredSharedStates"]):
            out.append((op,int(n),int(cov)))
    out.sort(key=lambda x:(-x[1],x[0]))
    return out[:int(cfg["maximumOperatorsPerCorpus"])]

def frequency_percentiles(operator_rows):
    arr=sorted((int(r[1]),r[0]) for r in operator_rows)
    n=len(arr)
    out={}
    i=0
    while i<n:
        j=i+1
        while j<n and arr[j][0]==arr[i][0]:
            j+=1
        mid=((i+j-1)/2)/max(1,n-1)
        for k in range(i,j):
            out[arr[k][1]]=mid
        i=j
    return out

def baseline_dist(counter,n,outcomes,alpha):
    V=len(outcomes)
    return {y:(counter[y]+alpha)/(n+alpha*V) for y in outcomes}

def operator_dist(counter,n,base,lam):
    if n<=0:
        return dict(base)
    return {y:(counter[y]+lam*base[y])/(n+lam) for y in base}

def build_fingerprints(events,states,operators,shared_weights,outcomes,protocol):
    tab=corpus_tables(events)
    cfg=protocol["training"]
    alpha=float(cfg["globalAdditiveAlpha"])
    lam=float(cfg["backoffPseudoCount"])
    clip=float(cfg["residualLog2Clip"])
    out={}
    for op in operators:
        vals=[]
        weights=[]
        for S in states:
            b=baseline_dist(tab[0][S],tab[2][S],outcomes,alpha)
            q=operator_dist(tab[1][(S,op)],tab[3][(S,op)],b,lam)
            sw=shared_weights[S]
            for y in outcomes:
                r=math.log2(max(q[y],1e-300)/max(b[y],1e-300))
                r=max(-clip,min(clip,r))
                vals.append(r)
                weights.append(sw)
        norm=math.sqrt(sum(w*x*x for w,x in zip(weights,vals)))
        out[op]={
            "vector":vals,
            "norm":norm,
            "supportByState":{S:int(tab[3][(S,op)]) for S in states}
        }
    return out

def cosine(a,b,weights):
    na=math.sqrt(sum(w*x*x for w,x in zip(weights,a)))
    nb=math.sqrt(sum(w*y*y for w,y in zip(weights,b)))
    if na<=0 or nb<=0:
        return 0.0
    return sum(w*x*y for w,x,y in zip(weights,a,b))/(na*nb)

def train_pairs(hfp,gfp,states,shared_weights,outcomes,hfreq,gfreq,hsupport,gsupport,variant,protocol):
    cfg=protocol["training"]
    controls=variant_controls(variant)
    weights=[]
    for S in states:
        weights.extend([shared_weights[S]]*len(outcomes))
    floor=float(cfg["minimumFingerprintNorm"])
    H=[h for h,d in hfp.items() if d["norm"]>=floor]
    G=[g for g,d in gfp.items() if d["norm"]>=floor]
    gap=float(protocol["controls"]["frequency"]["maximumFrequencyPercentileGap"])
    sims={}
    for h in H:
        for g in G:
            if "frequency" in controls and abs(hfreq[h]-gfreq[g])>gap:
                continue
            sims[(h,g)]=cosine(hfp[h]["vector"],gfp[g]["vector"],weights)
    hb={}
    gb={}
    for h in H:
        cand=[g for g in G if (h,g) in sims]
        if cand:
            hb[h]=max(cand,key=lambda g:(sims[(h,g)],g))
    for g in G:
        cand=[h for h in H if (h,g) in sims]
        if cand:
            gb[g]=max(cand,key=lambda h:(sims[(h,g)],h))
    strata=max(1,int(cfg["frequencyNullStrata"]))
    pairs=[]
    for h,g in hb.items():
        if gb.get(g)!=h:
            continue
        avg=(hfreq[h]+gfreq[g])/2
        pairs.append({
            "hebrew":h,
            "glyph":g,
            "trainSimilarity":sims[(h,g)],
            "hebrewTrainSupport":int(hsupport[h]),
            "glyphTrainSupport":int(gsupport[g]),
            "hebrewFrequencyPercentile":hfreq[h],
            "glyphFrequencyPercentile":gfreq[g],
            "frequencyPercentileGap":abs(hfreq[h]-gfreq[g]),
            "frequencyStratum":min(strata-1,int(avg*strata))
        })
    pairs.sort(key=lambda r:(-r["trainSimilarity"],r["hebrew"],r["glyph"]))
    return pairs

def freeze_variant(hebrew_rows,glyph_rows,variant,protocol,proper_operators):
    hev=hebrew_events(hebrew_rows,variant,protocol)
    gev=glyph_events(glyph_rows,variant,protocol)
    states,hs,gs=shared_states(hev,gev,protocol)
    HN=sum(hs[S] for S in states)
    GN=sum(gs[S] for S in states)
    raw={S:math.sqrt((hs[S]/max(1,HN))*(gs[S]/max(1,GN))) for S in states}
    z=sum(raw.values()) or 1.0
    sw={S:raw[S]/z for S in states}
    excluded=proper_operators if "proper" in variant_controls(variant) else set()
    hrows=select_operators(hev,states,protocol,excluded)
    grows=select_operators(gev,states,protocol,set())
    hops=[r[0] for r in hrows]
    gops=[r[0] for r in grows]
    hfreq=frequency_percentiles(hrows)
    gfreq=frequency_percentiles(grows)
    outcomes=variant_outcomes(variant)
    hfp=build_fingerprints(hev,states,hops,sw,outcomes,protocol)
    gfp=build_fingerprints(gev,states,gops,sw,outcomes,protocol)
    ht=corpus_tables(hev)
    gt=corpus_tables(gev)
    pairs=train_pairs(hfp,gfp,states,sw,outcomes,hfreq,gfreq,ht[4],gt[4],variant,protocol)
    return {
        "variantSpec":variant,
        "outcomes":list(outcomes),
        "sharedStates":states,
        "sharedStateWeights":sw,
        "hebrewOperators":hrows,
        "glyphOperators":grows,
        "hebrewFrequencyPercentiles":hfreq,
        "glyphFrequencyPercentiles":gfreq,
        "pairs":pairs,
        "trainEventCounts":{"hebrew":len(hev),"glyph":len(gev)},
        "trainSharedStateCounts":{
            "hebrew":{S:int(hs[S]) for S in states},
            "glyph":{S:int(gs[S]) for S in states}
        },
        "properOperatorUniverseCount":len(proper_operators),
        "properExclusionApplied":"proper" in variant_controls(variant)
    }

def freeze_all_variants(hebrew_rows,glyph_rows,protocol):
    proper=raw_train_proper_operators(hebrew_rows)
    variants={}
    for variant in protocol["variants"]:
        variants[variant["id"]]=freeze_variant(hebrew_rows,glyph_rows,variant,protocol,proper)
    return {
        "variants":variants,
        "properOperatorUniverseCount":len(proper)
    }

def lane_score(hebrew_rows,glyph_rows,variant_freeze,protocol,lane):
    variant=variant_freeze["variantSpec"]
    outcomes=tuple(variant_freeze["outcomes"])
    hev=hebrew_events(hebrew_rows,variant,protocol)
    gev=glyph_events(glyph_rows,variant,protocol)
    states=variant_freeze["sharedStates"]
    sw=variant_freeze["sharedStateWeights"]
    hops=[r[0] for r in variant_freeze["hebrewOperators"]]
    gops=[r[0] for r in variant_freeze["glyphOperators"]]
    hfp=build_fingerprints(hev,states,hops,sw,outcomes,protocol)
    gfp=build_fingerprints(gev,states,gops,sw,outcomes,protocol)
    weights=[]
    for S in states:
        weights.extend([sw[S]]*len(outcomes))
    ht=corpus_tables(hev)
    gt=corpus_tables(gev)
    mn=int(protocol["evaluation"]["minimumEvaluationEventsPerOperator"])
    allpairs=variant_freeze["pairs"]
    pairs=[
        r for r in allpairs
        if ht[4][r["hebrew"]]>=mn and gt[4][r["glyph"]]>=mn
    ]
    evaluable_fraction=len(pairs)/max(1,len(allpairs))
    def sim(h,g):
        return cosine(hfp[h]["vector"],gfp[g]["vector"],weights)
    obs=[sim(r["hebrew"],r["glyph"]) for r in pairs]
    mean=sum(obs)/max(1,len(obs))
    positive=sum(x>0 for x in obs)/max(1,len(obs))
    glyph_pool=[r["glyph"] for r in pairs]
    ranks=[]
    for r in pairs:
        actual=sim(r["hebrew"],r["glyph"])
        scores=[sim(r["hebrew"],g) for g in glyph_pool]
        below=sum(s<=actual for s in scores)-1
        ranks.append(below/max(1,len(scores)-1))
    med=sorted(ranks)[len(ranks)//2] if ranks else 0.0
    pc=int(protocol["evaluation"]["permutationCount"])
    seed=protocol["evaluation"]["permutationSeed"]+":"+variant["id"]+":"+lane

    def pvalue(stratified,salt):
        if not pairs:
            return 1.0
        rng=random.Random(seed+":"+salt)
        ge=0
        for _ in range(pc):
            assigned={}
            if stratified:
                groups=defaultdict(list)
                for i,r in enumerate(pairs):
                    groups[r["frequencyStratum"]].append(i)
                for inds in groups.values():
                    vals=[pairs[i]["glyph"] for i in inds]
                    rng.shuffle(vals)
                    for i,g in zip(inds,vals):
                        assigned[i]=g
            else:
                vals=[r["glyph"] for r in pairs]
                rng.shuffle(vals)
                for i,g in enumerate(vals):
                    assigned[i]=g
            m=sum(sim(r["hebrew"],assigned[i]) for i,r in enumerate(pairs))/len(pairs)
            if m>=mean-1e-15:
                ge+=1
        return (ge+1)/(pc+1)

    p_un=pvalue(False,"unstratified")
    p_fr=pvalue(True,"frequency")
    gates=protocol["evaluation"]["gatesPerLane"]
    eval_gate=(
        len(pairs)>=int(protocol["evaluation"]["minimumEvaluablePairCount"])
        and evaluable_fraction>=float(protocol["evaluation"]["minimumEvaluablePairFraction"])
    )
    stats_gate=(
        mean>float(gates["meanSimilarityGreaterThan"])
        and p_un<=float(gates["unstratifiedPermutationPAtMost"])
        and p_fr<=float(gates["frequencyStratifiedPermutationPAtMost"])
        and med>=float(gates["medianRankPercentileAtLeast"])
        and positive>=float(gates["positivePairFractionAtLeast"])
    )
    return {
        "lane":lane,
        "frozenPairCount":len(allpairs),
        "evaluablePairCount":len(pairs),
        "evaluablePairFraction":evaluable_fraction,
        "meanSimilarity":mean,
        "positivePairFraction":positive,
        "medianRankPercentile":med,
        "unstratifiedPermutationP":p_un,
        "frequencyStratifiedPermutationP":p_fr,
        "evaluabilityGate":eval_gate,
        "statisticalGate":stats_gate,
        "gate":eval_gate and stats_gate,
        "pairSimilarities":[
            {
                "hebrew":r["hebrew"],
                "glyph":r["glyph"],
                "similarity":s,
                "rankPercentile":rp
            }
            for r,s,rp in zip(pairs,obs,ranks)
        ]
    }

def variant_result(hebrew_lanes,glyph_lanes,variant_freeze,protocol):
    pair_count=len(variant_freeze["pairs"])
    min_pairs=int(protocol["training"]["minimumFrozenPairCount"])
    lane_results={
        lane:lane_score(
            hebrew_lanes[lane],
            glyph_lanes[lane],
            variant_freeze,
            protocol,
            lane
        )
        for lane in ("holdout","control")
    }
    train_feasible=pair_count>=min_pairs
    both_eval=all(lane_results[l]["evaluabilityGate"] for l in ("holdout","control"))
    both_stats=all(lane_results[l]["statisticalGate"] for l in ("holdout","control"))
    full_pass=train_feasible and all(lane_results[l]["gate"] for l in ("holdout","control"))
    if full_pass:
        status="PASS"
    elif not train_feasible:
        status="TRAIN_FEASIBILITY_COLLAPSE"
    elif not both_eval:
        status="EVALUATION_SUPPORT_COLLAPSE"
    else:
        status="TRANSFER_GATE_FAILURE"
    return {
        "status":status,
        "fullPass":full_pass,
        "trainFeasible":train_feasible,
        "frozenPairCount":pair_count,
        "bothLanesEvaluable":both_eval,
        "bothLanesStatisticalGate":both_stats,
        "lanes":lane_results
    }

def adjudicate(results,protocol):
    baseline=results["baseline"]
    if not baseline["fullPass"]:
        return {
            "adjudication":"BASELINE_NOT_REPRODUCED_UNDER_V17",
            "baselineStatus":baseline["status"],
            "isolatedSufficientBreakers":[],
            "cumulativeFirstBreak":None
        }
    isolated_ids={
        "boundary":"boundary_only",
        "segment":"segment_only",
        "seenNew":"seennew_only",
        "proper":"proper_only",
        "frequency":"frequency_only"
    }
    breakers=[]
    for control,vid in isolated_ids.items():
        if not results[vid]["fullPass"]:
            breakers.append({
                "control":control,
                "variant":vid,
                "breakType":results[vid]["status"]
            })
    ladder=[
        ("boundary","boundary_only"),
        ("boundary+segment","cum_boundary_segment"),
        ("boundary+segment+seenNew","cum_boundary_segment_seennew"),
        ("boundary+segment+seenNew+proper","cum_boundary_segment_seennew_proper"),
        ("boundary+segment+seenNew+proper+frequency","cum_full")
    ]
    first=None
    for label,vid in ladder:
        if not results[vid]["fullPass"]:
            first={"rung":label,"variant":vid,"breakType":results[vid]["status"]}
            break
    if breakers:
        adjud="V15_SENSITIVITY_LOCALIZED_TO_ONE_OR_MORE_ISOLATED_CONTROLS"
    elif first is not None:
        adjud="V15_FAILURE_REQUIRES_CONTROL_COMBINATION"
    else:
        adjud="V15_SURVIVES_PREDECLARED_V17_ABLATION_LADDER"
    return {
        "adjudication":adjud,
        "baselineStatus":baseline["status"],
        "isolatedSufficientBreakers":breakers,
        "cumulativeFirstBreak":first
    }
