#!/usr/bin/env python3
import hashlib, json, math
from collections import Counter, defaultdict

BOUNDARIES={"<DOC>","<LINE>","<WORD>"}
OTHER="OTHER"

def canonical_json(v): return json.dumps(v,ensure_ascii=False,sort_keys=True,separators=(",",":"))
def canonical_sha(v): return hashlib.sha256(canonical_json(v).encode("utf-8")).hexdigest()
def fold_for_doc(doc,folds=3): return int.from_bytes(hashlib.sha256(doc.encode("utf-8")).digest()[:8],"big")%folds

def read_jsonl(path,expected_lane=None):
    out=[]
    with open(path,encoding="utf-8") as f:
        for line in f:
            if not line.strip(): continue
            r=json.loads(line)
            if expected_lane is not None and r.get("lane")!=expected_lane:
                raise RuntimeError(f"expected lane {expected_lane}, got {r.get('lane')}")
            out.append(r)
    out.sort(key=lambda r:r["anonymousInscriptionId"])
    return out

def sequence_stream(words):
    s=["<DOC>"]
    for token in words:
        if token=="\n":
            if s[-1]!="<LINE>": s.append("<LINE>")
            continue
        s.extend(token)
    if s[-1]=="<LINE>": s.pop()
    s.append("<DOC>")
    return s

def map_token(tok,common):
    if tok in ("<DOC>","<LINE>"): return tok
    return tok if tok in common else OTHER

def mapped_stream(words,common):
    raw=sequence_stream(words)
    return raw,[map_token(x,common) for x in raw]

def history_before(s,i,L=2): return tuple((["<DOC>"]*L+s[:i])[-L:])

def ngram_distribution(ctx,tokens,tabs,totals,alpha,lam,max_order=None):
    max_order=len(tabs)-1 if max_order is None else min(max_order,len(tabs)-1)
    V=max(1,len(tokens)); uni=tabs[0][()]; N=totals[0][()]
    p=[(uni[t]+alpha)/(N+alpha*V) for t in tokens]
    for o in range(1,min(len(ctx),max_order)+1):
        c=tuple(ctx[-o:]); n=totals[o].get(c,0)
        if not n: continue
        cc=tabs[o][c]; den=n+lam
        p=[(cc[t]+lam*p[j])/den for j,t in enumerate(tokens)]
    return p

def fingerprint(ctx,tokens,tabs,totals,fp,alpha,lam):
    p=ngram_distribution(ctx,tokens,tabs,totals,alpha,lam)
    idx={t:i for i,t in enumerate(tokens)}
    vals=[p[idx[t]] if t in idx else 0.0 for t in fp]
    vals.append(max(0.0,1.0-sum(vals)))
    return vals

def sqdist(a,b): return sum((x-y)*(x-y) for x,y in zip(a,b))

def thaw_v12_state(packet,protocol):
    sp=packet["space"]; max_order=4
    tabs=[defaultdict(Counter) for _ in range(max_order+1)]; totals=[Counter() for _ in range(max_order+1)]
    for r in sp["ngramRows"]:
        o=int(r["order"]); c=tuple(r["context"]); tabs[o][c][r["outcome"]]+=int(r["count"]); totals[o][c]+=int(r["count"])
    exact={tuple(r["history"]):int(r["state"]) for r in sp["exactHistoryStates"]}
    tokens=list(sp["tokens"]); centers=sp["centroids"]; fp=sp["fingerprintOutcomes"]
    alpha=float(protocol["probabilityModel"]["globalAdditiveAlpha"]); lam=float(protocol["probabilityModel"]["backoffPseudoCount"]); cache={}
    def state(h):
        h=tuple(h)
        if h in exact: return exact[h]
        if h in cache: return cache[h]
        v=fingerprint(h,tokens,tabs,totals,fp,alpha,lam)
        s=min(range(len(centers)),key=lambda j:(sqdist(v,centers[j]),j)); cache[h]=s; return s
    return {"tokens":tokens,"state":state,"exact":exact,"centers":centers}

def canonicalize_surface(seq):
    seen={}; out=[]
    for x in seq:
        if x in ("<DOC>","<LINE>"):
            out.append(x)
        else:
            if x not in seen: seen[x]=len(seen)
            out.append(f"G{seen[x]}")
    return tuple(out)

def role_signature(raw,i,protocol):
    cfg=protocol["roleDefinition"]; W=int(cfg["windowIncludingCurrentGlyph"])
    j=i-1
    while j>=0 and raw[j] not in ("<DOC>","<LINE>"): j-=1
    line_start=j+1
    line_dist=min(i-line_start,int(cfg["lineDistanceBucketCap"]))
    recur=0; max_recur=min(int(cfg["suffixRecurrenceDepthCap"]),i-line_start+1)
    for L in range(1,max_recur+1):
        sub=raw[i-L+1:i+1]
        if any(raw[e-L+1:e+1]==sub for e in range(line_start+L-1,i-L+1)):
            recur=L
    prior=sum(1 for x in raw[line_start:i] if x==raw[i])
    prior=min(prior,int(cfg["priorSameGlyphCountBucketCap"]))
    return {
        "pattern":list(canonicalize_surface(raw[max(0,i-W+1):i+1])),
        "lineDistanceBucket":line_dist,
        "suffixRecurrenceDepth":recur,
        "priorSameGlyphCountBucket":prior
    }

def role_key(sig): return canonical_json(sig)

def assert_role_anonymous(sig):
    for x in sig["pattern"]:
        if x in ("<DOC>","<LINE>"): continue
        if not (isinstance(x,str) and x.startswith("G") and x[1:].isdigit()):
            raise RuntimeError("surface identity leaked into role pattern")

def build_prediction_events(rows,v12,protocol):
    common=set(v12["commonStates"]); eligible=set(v12["eligibleGlyphs"]); L=int(v12["historyLength"]); st=thaw_v12_state(v12,protocol)["state"]
    out=[]
    for row in rows:
        doc=row["anonymousInscriptionId"]; raw,s=mapped_stream(row["words"],common)
        for i in range(1,len(s)-1):
            g=raw[i]
            if g not in eligible: continue
            sig=role_signature(raw,i,protocol); assert_role_anonymous(sig); R=role_key(sig); S=st(history_before(s,i,L)); y=s[i+1]
            out.append({"doc":doc,"state":S,"glyph":g,"role":R,"outcome":y,"context8":list(s[max(0,i+1-8):i+1])})
    return out

def eligible_roles(events,protocol):
    cfg=protocol["roleDefinition"]; counts=Counter(); glyphs=defaultdict(set)
    for e in events: counts[e["role"]]+=1; glyphs[e["role"]].add(e["glyph"])
    keep={r for r,n in counts.items() if n>=int(cfg["minimumTrainRoleOccurrences"]) and len(glyphs[r])>=int(cfg["minimumDistinctTrainGlyphsPerRole"])}
    return keep,counts,glyphs

def select_mask(events,roles,protocol):
    cfg=protocol["matrixHoldout"]; pair=Counter(); gt=Counter(); rt=Counter(); gs=defaultdict(set); rg=defaultdict(set); states=defaultdict(Counter); sg=Counter(); sr=Counter()
    for e in events:
        R=e["role"]
        if R not in roles: continue
        g=e["glyph"]; S=e["state"]; pair[(g,R)]+=1; gt[g]+=1; rt[R]+=1; gs[g].add(R); rg[R].add(g); states[(g,R)][S]+=1; sg[(S,g)]+=1; sr[(S,R)]+=1
    selected=[]
    for (g,R),n in sorted(pair.items(),key=lambda kv:(kv[0][0],kv[0][1])):
        if n<int(cfg["minimumTrainCombinationOccurrences"]): continue
        if len(gs[g])<int(cfg["minimumDistinctRolesForGlyph"]): continue
        if len(rg[R])<int(cfg["minimumDistinctGlyphsForRole"]): continue
        if n>float(cfg["maximumCombinationFractionOfGlyph"])*gt[g]: continue
        if n>float(cfg["maximumCombinationFractionOfRole"])*rt[R]: continue
        ok=False
        for S,k in states[(g,R)].items():
            if sg[(S,g)]-k>=int(cfg["minimumResidualStateGlyphSupport"]) and sr[(S,R)]-k>=int(cfg["minimumResidualStateRoleSupport"]): ok=True; break
        if not ok: continue
        h=int.from_bytes(hashlib.sha256((g+"|"+R).encode("utf-8")).digest()[:8],"big")
        if h%4!=0: continue
        selected.append({"glyph":g,"role":R,"trainOccurrences":int(n)})
    return selected

def mask_set(mask_rows): return {(r["glyph"],r["role"]) for r in mask_rows}

def build_model(events,roles,masked,vocab,protocol):
    model={
        "global":Counter(),"state":defaultdict(Counter),"sg":defaultdict(Counter),"role":defaultdict(Counter),"sr":defaultdict(Counter),
        "roleByGlyph":defaultdict(Counter),"srByGlyph":defaultdict(Counter),"sgr":defaultdict(Counter),
        "globalN":0,"stateN":Counter(),"sgN":Counter(),"roleN":Counter(),"srN":Counter(),"roleByGlyphN":Counter(),"srByGlyphN":Counter(),"sgrN":Counter()
    }
    for e in events:
        R=e["role"]
        if R not in roles or (e["glyph"],R) in masked: continue
        S=e["state"]; g=e["glyph"]; y=e["outcome"]
        model["global"][y]+=1; model["globalN"]+=1
        for name,key in (("state",S),("sg",(S,g)),("role",R),("sr",(S,R)),("roleByGlyph",(R,g)),("srByGlyph",(S,R,g)),("sgr",(S,g,R))):
            model[name][key][y]+=1; model[name+"N"][key]+=1
    model["vocab"]=list(vocab)
    return model

def _normalize(vals):
    z=sum(vals.values())
    if z<=0: return {k:1.0/max(1,len(vals)) for k in vals}
    return {k:v/z for k,v in vals.items()}

def global_dist(m,protocol):
    a=float(protocol["probabilityModel"]["globalAdditiveAlpha"]); V=max(1,len(m["vocab"])); N=m["globalN"]
    return {y:(m["global"][y]+a)/(N+a*V) for y in m["vocab"]}

def backoff_dist(counter,n,base,lam):
    if not n: return dict(base)
    return {y:(counter[y]+lam*base[y])/(n+lam) for y in base}

def state_dist(m,S,protocol):
    base=global_dist(m,protocol); lam=float(protocol["probabilityModel"]["backoffPseudoCount"])
    return backoff_dist(m["state"][S],m["stateN"][S],base,lam)

def glyph_dist(m,S,g,protocol):
    base=state_dist(m,S,protocol); lam=float(protocol["probabilityModel"]["backoffPseudoCount"])
    return backoff_dist(m["sg"][(S,g)],m["sgN"][(S,g)],base,lam)

def role_global_loo_dist(m,R,g,protocol):
    base=global_dist(m,protocol); lam=float(protocol["probabilityModel"]["backoffPseudoCount"])
    n=m["roleN"][R]-m["roleByGlyphN"][(R,g)]; c=Counter(m["role"][R]); c.subtract(m["roleByGlyph"][(R,g)])
    return backoff_dist(c,n,base,lam)

def role_state_loo_dist(m,S,R,g,protocol):
    ps=state_dist(m,S,protocol); pr=role_global_loo_dist(m,R,g,protocol); pg=global_dist(m,protocol)
    prior=_normalize({y:ps[y]*pr[y]/max(pg[y],1e-300) for y in m["vocab"]})
    n=m["srN"][(S,R)]-m["srByGlyphN"][(S,R,g)]; c=Counter(m["sr"][(S,R)]); c.subtract(m["srByGlyph"][(S,R,g)])
    lam=float(protocol["probabilityModel"]["backoffPseudoCount"])
    return backoff_dist(c,n,prior,lam)

def factorized_dist(m,S,g,R,protocol):
    ps=state_dist(m,S,protocol); pg=glyph_dist(m,S,g,protocol); pr=role_state_loo_dist(m,S,R,g,protocol)
    return _normalize({y:pg[y]*pr[y]/max(ps[y],1e-300) for y in m["vocab"]})

def direct_dist(m,S,g,R,protocol):
    base=factorized_dist(m,S,g,R,protocol); lam=float(protocol["probabilityModel"]["directBackoffPseudoCount"])
    return backoff_dist(m["sgr"][(S,g,R)],m["sgrN"][(S,g,R)],base,lam)

def tv(p,q): return 0.5*sum(abs(p.get(y,0)-q.get(y,0)) for y in set(p)|set(q))

def select_role_switches(m,roles,protocol):
    mn=6; ratio_max=2.0; tvmin=0.10; by=defaultdict(list)
    for (S,g,R),n in m["sgrN"].items():
        if R in roles and n>=mn: by[(S,g)].append(R)
    out=[]
    for (S,g),rs in sorted(by.items(),key=lambda kv:(kv[0][0],kv[0][1])):
        for R in sorted(set(rs)):
            n=m["sgrN"][(S,g,R)]; p=factorized_dist(m,S,g,R,protocol); best=None
            for Rp in sorted(set(rs)):
                if Rp==R: continue
                np=m["sgrN"][(S,g,Rp)]; ratio=max(n/np,np/n)
                if ratio>ratio_max: continue
                q=factorized_dist(m,S,g,Rp,protocol); d=tv(p,q)
                if d<tvmin: continue
                sd=abs(math.log2(n/np)); tie=hashlib.sha256(f"{S}|{g}|{R}|{Rp}".encode()).hexdigest(); cand=(sd,-d,tie,Rp,np,ratio,d)
                if best is None or cand[:3]<best[:3]: best=cand
            if best:
                out.append({"state":int(S),"glyph":g,"actualRole":R,"substituteRole":best[3],"actualSupport":int(n),"substituteSupport":int(best[4]),"supportRatio":float(best[5]),"kernelTv":float(best[6])})
    return out

def build_ngram_tables(rows,common,eligible,roles,masked,protocol,max_order=8):
    tabs=[defaultdict(Counter) for _ in range(max_order+1)]; totals=[Counter() for _ in range(max_order+1)]; vocab=Counter()
    for row in rows:
        raw,s=mapped_stream(row["words"],common)
        for j in range(1,len(s)):
            skip=False; i=j-1; g=raw[i]
            if g in eligible:
                R=role_key(role_signature(raw,i,protocol))
                if R in roles and (g,R) in masked: skip=True
            if skip: continue
            y=s[j]; vocab[y]+=1
            for o in range(max_order+1):
                ctx=tuple(s[max(0,j-o):j]) if o else ()
                tabs[o][ctx][y]+=1; totals[o][ctx]+=1
    return sorted(vocab),tabs,totals

def ngram_prob(tokens,tabs,totals,ctx,y,order,protocol):
    p=ngram_distribution(tuple(ctx),tokens,tabs,totals,float(protocol["probabilityModel"]["globalAdditiveAlpha"]),float(protocol["probabilityModel"]["backoffPseudoCount"]),max_order=order)
    try: return p[tokens.index(y)]
    except ValueError: return 1e-300

def choose_ngram_order(rows,common,eligible,roles,masked,protocol):
    orders=list(protocol["models"]["ngramOrders"]); folds=3; scores={o:[0.0,0] for o in orders}
    for f in range(folds):
        fit=[r for r in rows if fold_for_doc(r["anonymousInscriptionId"],folds)!=f]; val=[r for r in rows if fold_for_doc(r["anonymousInscriptionId"],folds)==f]
        tokens,tabs,totals=build_ngram_tables(fit,common,eligible,roles,masked,protocol,max(orders))
        for row in val:
            raw,s=mapped_stream(row["words"],common)
            for j in range(1,len(s)):
                i=j-1; g=raw[i]
                if g not in eligible: continue
                R=role_key(role_signature(raw,i,protocol))
                if R not in roles or (g,R) in masked: continue
                y=s[j]
                for o in orders:
                    q=max(ngram_prob(tokens,tabs,totals,s[max(0,j-o):j],y,o,protocol),1e-300); scores[o][0]+=-math.log2(q); scores[o][1]+=1
    rows_out=[{"order":o,"bitsPerEvent":scores[o][0]/max(1,scores[o][1]),"events":scores[o][1]} for o in orders]
    best=min(rows_out,key=lambda r:(r["bitsPerEvent"],r["order"]))["order"]
    return best,rows_out

def signflip_p(values,iters,salt):
    if not values: return None
    obs=sum(values)/len(values)
    if obs<=0: return 1.0
    exceed=0
    for it in range(iters):
        total=0.0
        for idx,v in enumerate(values): total += v if hashlib.sha256(f"{salt}|{it}|{idx}".encode()).digest()[0]&1 else -v
        if total/len(values)>=obs-1e-15: exceed+=1
    return (exceed+1)/(iters+1)

def summarize_docs(by_doc,iters,salt):
    vals=[sum(by_doc[d])/len(by_doc[d]) for d in sorted(by_doc) if by_doc[d]]; mean=sum(vals)/max(1,len(vals)); pos=sum(v>0 for v in vals)/max(1,len(vals))
    return {"inscriptions":len(vals),"meanBits":mean,"medianBits":sorted(vals)[len(vals)//2] if vals else None,"positiveFraction":pos,"signFlipP":signflip_p(vals,int(iters),salt)}

def encode_counter_map(d,key_names):
    out=[]
    for k,c in d.items():
        if not isinstance(k,tuple): k=(k,)
        for y,n in c.items():
            r={name:v for name,v in zip(key_names,k)}; r.update({"outcome":y,"count":int(n)}); out.append(r)
    out.sort(key=lambda r:tuple(str(r[n]) for n in key_names)+(r["outcome"],)); return out

def decode_counter_map(rows,key_names):
    d=defaultdict(Counter); N=Counter()
    for r in rows:
        key=tuple(r[n] for n in key_names); key=key[0] if len(key)==1 else key; d[key][r["outcome"]]+=int(r["count"]); N[key]+=int(r["count"])
    return d,N

def encode_model(m):
    return {
        "vocab":m["vocab"],"globalRows":[{"outcome":y,"count":int(n)} for y,n in sorted(m["global"].items())],
        "stateRows":encode_counter_map(m["state"],["state"]),"stateGlyphRows":encode_counter_map(m["sg"],["state","glyph"]),
        "roleRows":encode_counter_map(m["role"],["role"]),"stateRoleRows":encode_counter_map(m["sr"],["state","role"]),
        "roleByGlyphRows":encode_counter_map(m["roleByGlyph"],["role","glyph"]),"stateRoleByGlyphRows":encode_counter_map(m["srByGlyph"],["state","role","glyph"]),
        "stateGlyphRoleRows":encode_counter_map(m["sgr"],["state","glyph","role"])
    }

def decode_model(x):
    m={"vocab":x["vocab"],"global":Counter({r["outcome"]:int(r["count"]) for r in x["globalRows"]})}; m["globalN"]=sum(m["global"].values())
    specs=[("state","stateRows",["state"]),("sg","stateGlyphRows",["state","glyph"]),("role","roleRows",["role"]),("sr","stateRoleRows",["state","role"]),("roleByGlyph","roleByGlyphRows",["role","glyph"]),("srByGlyph","stateRoleByGlyphRows",["state","role","glyph"]),("sgr","stateGlyphRoleRows",["state","glyph","role"])]
    for name,field,keys in specs:
        d,N=decode_counter_map(x[field],keys)
        fixed=defaultdict(Counter); fixedN=Counter()
        for k,c in d.items():
            kk=k if isinstance(k,tuple) else (k,); vals=list(kk)
            for idx,key in enumerate(keys):
                if key=="state": vals[idx]=int(vals[idx])
            nk=vals[0] if len(vals)==1 else tuple(vals); fixed[nk]=c; fixedN[nk]=N[k]
        m[name]=fixed; m[name+"N"]=fixedN
    return m

def encode_ngram(tokens,tabs):
    rows=[]
    for o,tab in enumerate(tabs):
        for ctx,c in tab.items():
            for y,n in c.items(): rows.append({"order":o,"context":list(ctx),"outcome":y,"count":int(n)})
    rows.sort(key=lambda r:(r["order"],r["context"],r["outcome"])); return {"tokens":tokens,"rows":rows}

def decode_ngram(x,max_order=8):
    tabs=[defaultdict(Counter) for _ in range(max_order+1)]; totals=[Counter() for _ in range(max_order+1)]
    for r in x["rows"]:
        o=int(r["order"]); ctx=tuple(r["context"]); tabs[o][ctx][r["outcome"]]+=int(r["count"]); totals[o][ctx]+=int(r["count"])
    return x["tokens"],tabs,totals
