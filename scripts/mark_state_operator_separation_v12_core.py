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
            if expected_lane is not None and r.get("lane")!=expected_lane: raise RuntimeError(f"expected lane {expected_lane}, got {r.get('lane')}")
            out.append(r)
    out.sort(key=lambda r:r["anonymousInscriptionId"]); return out

def sequence_stream(words):
    s=["<DOC>"]
    for token in words:
        if token=="\n":
            if s[-1]!="<LINE>": s.append("<LINE>")
            continue
        s.extend(token)
    if s[-1]=="<LINE>": s.pop()
    s.append("<DOC>"); return s

def map_token(tok,common):
    if tok in ("<DOC>","<LINE>"): return tok
    return tok if tok in common else OTHER

def mapped_stream(words,common):
    raw=sequence_stream(words); return raw,[map_token(x,common) for x in raw]

def history_before(s,i,L=2): return tuple((["<DOC>"]*L+s[:i])[-L:])

def build_ngram(rows,common,max_order=4):
    tabs=[defaultdict(Counter) for _ in range(max_order+1)]; totals=[Counter() for _ in range(max_order+1)]; vocab=Counter()
    for row in rows:
        _,s=mapped_stream(row["words"],common)
        for i in range(1,len(s)):
            y=s[i]; vocab[y]+=1
            for o in range(max_order+1):
                ctx=tuple(s[max(0,i-o):i]) if o else ()
                tabs[o][ctx][y]+=1; totals[o][ctx]+=1
    return sorted(vocab),tabs,totals,vocab

def ngram_distribution(ctx,tokens,tabs,totals,alpha,lam):
    V=max(1,len(tokens)); uni=tabs[0][()]; N=totals[0][()]
    p=[(uni[t]+alpha)/(N+alpha*V) for t in tokens]
    for o in range(1,min(len(ctx),len(tabs)-1)+1):
        c=tuple(ctx[-o:]); n=totals[o].get(c,0)
        if not n: continue
        cc=tabs[o][c]; den=n+lam
        p=[(cc[t]+lam*p[j])/den for j,t in enumerate(tokens)]
    return p

def top_fingerprint_outcomes(vocab,n): return [t for t,_ in sorted(vocab.items(),key=lambda kv:(-kv[1],kv[0]))[:n]]
def fingerprint(ctx,tokens,tabs,totals,fp,alpha,lam):
    p=ngram_distribution(ctx,tokens,tabs,totals,alpha,lam); idx={t:i for i,t in enumerate(tokens)}
    vals=[p[idx[t]] if t in idx else 0.0 for t in fp]; vals.append(max(0.0,1.0-sum(vals))); return vals

def sqdist(a,b): return sum((x-y)*(x-y) for x,y in zip(a,b))
def weighted_kmeans(vecs,weights,k,iters):
    n=len(vecs); k=min(k,n); first=max(range(n),key=lambda i:(weights[i],-i)); centers=[list(vecs[first])]; chosen={first}
    for _ in range(1,k):
        best=(-1.0,None)
        for i,v in enumerate(vecs):
            if i in chosen: continue
            score=min(sqdist(v,c) for c in centers)*math.sqrt(weights[i])
            if score>best[0]+1e-18 or (abs(score-best[0])<=1e-18 and (best[1] is None or i<best[1])): best=(score,i)
        chosen.add(best[1]); centers.append(list(vecs[best[1]]))
    assign=[-1]*n; D=len(vecs[0])
    for _ in range(iters):
        changed=0; sums=[[0.0]*D for _ in range(k)]; sw=[0.0]*k
        for i,v in enumerate(vecs):
            a=min(range(k),key=lambda j:(sqdist(v,centers[j]),j)); changed += assign[i]!=a; assign[i]=a; w=weights[i]; sw[a]+=w
            for d,x in enumerate(v): sums[a][d]+=w*x
        for j in range(k):
            if sw[j]: centers[j]=[x/sw[j] for x in sums[j]]
        if not changed: break
    return centers,assign

def induce_state_space(rows,common,protocol,k):
    L=int(protocol["representation"]["historyLength"]); cfg=protocol["probabilityModel"]; scfg=protocol["stateInduction"]
    tokens,tabs,totals,vocab=build_ngram(rows,common,max(cfg["ngramOrders"])); fp=top_fingerprint_outcomes(vocab,int(scfg["fingerprintOutcomeDimensions"])); hc=Counter()
    for row in rows:
        _,s=mapped_stream(row["words"],common)
        for i in range(1,len(s)): hc[history_before(s,i,L)]+=1
    histories=sorted(hc); vecs=[fingerprint(h,tokens,tabs,totals,fp,float(cfg["globalAdditiveAlpha"]),float(cfg["hierarchicalBackoffPseudoCount"])) for h in histories]
    centers,assign=weighted_kmeans(vecs,[hc[h] for h in histories],int(k),int(scfg["kmeansIterations"])); return {"tokens":tokens,"tabs":tabs,"totals":totals,"vocab":vocab,"fpOutcomes":fp,"centers":centers,"exact":{h:a for h,a in zip(histories,assign)},"historyCounts":hc}

def state_assigner(space,protocol):
    cfg=protocol["probabilityModel"]; cache={}
    def state(h):
        h=tuple(h)
        if h in space["exact"]: return space["exact"][h]
        if h in cache: return cache[h]
        v=fingerprint(h,space["tokens"],space["tabs"],space["totals"],space["fpOutcomes"],float(cfg["globalAdditiveAlpha"]),float(cfg["hierarchicalBackoffPseudoCount"])); s=min(range(len(space["centers"])),key=lambda j:(sqdist(v,space["centers"][j]),j)); cache[h]=s; return s
    return state

def learn_machine(rows,common,eligible,space,protocol):
    L=int(protocol["representation"]["historyLength"]); K=len(space["centers"]); st=state_assigner(space,protocol); emit=[Counter() for _ in range(K)]; emitN=[0]*K; trans=defaultdict(Counter); transN=Counter(); trans0=[Counter() for _ in range(K)]; trans0N=[0]*K; pair=defaultdict(Counter); pairN=Counter(); support=Counter()
    for row in rows:
        raw,s=mapped_stream(row["words"],common)
        for i in range(1,len(s)):
            S=st(history_before(s,i,L)); y=s[i]; emit[S][y]+=1; emitN[S]+=1; g=raw[i]
            if g in eligible and i+1<len(s):
                S1=st(history_before(s,i+1,L)); trans[(S,g)][S1]+=1; transN[(S,g)]+=1; trans0[S][S1]+=1; trans0N[S]+=1; support[(S,g)]+=1
                if i+2<len(s) and raw[i+1] in eligible: pair[(S,g,raw[i+1])][s[i+2]]+=1; pairN[(S,g,raw[i+1])]+=1
    gc=Counter(); GN=0
    for c in emit: gc.update(c); GN+=sum(c.values())
    return {"K":K,"emit":emit,"emitN":emitN,"trans":trans,"transN":transN,"trans0":trans0,"trans0N":trans0N,"pair":pair,"pairN":pairN,"opSupport":support,"global":gc,"globalN":GN,"state":st}

def emit_prob(m,y,S,protocol):
    cfg=protocol["probabilityModel"]; alpha=float(cfg["globalAdditiveAlpha"]); lam=float(cfg["emissionBackoffPseudoCount"]); V=max(1,len(m["global"])); pg=(m["global"][y]+alpha)/(m["globalN"]+alpha*V); n=m["emitN"][S]
    return (m["emit"][S][y]+lam*pg)/(n+lam) if n else pg

def t0_probs(m,S,protocol):
    alpha=float(protocol["probabilityModel"]["globalAdditiveAlpha"]); K=m["K"]; n=m["trans0N"][S]
    if not n: return [1.0/K]*K
    return [(m["trans0"][S][j]+alpha)/(n+alpha*K) for j in range(K)]
def trans_probs(m,S,g,protocol):
    lam=float(protocol["probabilityModel"]["transitionBackoffPseudoCount"]); base=t0_probs(m,S,protocol); n=m["transN"][(S,g)]
    if not n: return base
    c=m["trans"][(S,g)]; return [(c[j]+lam*base[j])/(n+lam) for j in range(m["K"])]
def consequence_kernel(m,S,g,protocol):
    tp=trans_probs(m,S,g,protocol); return {y:sum(tp[j]*emit_prob(m,y,j,protocol) for j in range(m["K"])) for y in m["global"]}
def compose_kernel(m,S,a,b,protocol,mode="factorized"):
    first=trans_probs(m,S,a,protocol) if mode in ("factorized","firstOnly") else t0_probs(m,S,protocol); dist=[0.0]*m["K"]
    for s1,w in enumerate(first):
        second=trans_probs(m,s1,b,protocol) if mode in ("factorized","secondOnly") else t0_probs(m,s1,protocol)
        for s2,q in enumerate(second): dist[s2]+=w*q
    return {y:sum(dist[j]*emit_prob(m,y,j,protocol) for j in range(m["K"])) for y in m["global"]}
def direct_pair_prob(m,S,a,b,y,protocol):
    lam=float(protocol["probabilityModel"]["directPairBackoffPseudoCount"]); back=compose_kernel(m,S,a,b,protocol)[y]; n=m["pairN"][(S,a,b)]
    return (m["pair"][(S,a,b)][y]+lam*back)/(n+lam) if n else back
def tv(p,q): return 0.5*sum(abs(p.get(x,0)-q.get(x,0)) for x in set(p)|set(q))
def select_substitutes(m,eligible,protocol):
    cfg=protocol["counterfactualSubstitution"]; mn=int(cfg["minimumTrainStateGlyphOccurrences"]); tvmin=float(cfg["minimumConsequenceKernelTv"]); out={}
    for (S,g),ng in sorted(m["opSupport"].items(),key=lambda kv:(kv[0][0],kv[0][1])):
        if ng<mn: continue
        pg=consequence_kernel(m,S,g,protocol); best=None
        for b in sorted(eligible):
            if b==g: continue
            nb=m["opSupport"][(S,b)]
            if nb<mn: continue
            pb=consequence_kernel(m,S,b,protocol); d=tv(pg,pb)
            if d<tvmin: continue
            cand=(abs(math.log2(ng/nb)),hashlib.sha256(f"{S}|{g}|{b}".encode()).hexdigest(),b,d,ng,nb)
            if best is None or cand[:2]<best[:2]: best=cand
        if best: out[(S,g)]={"substitute":best[2],"tv":best[3],"actualSupport":best[4],"substituteSupport":best[5]}
    return out

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
def serialize_counter(counter,names):
    rows=[]
    for k,v in counter.items():
        if not isinstance(k,tuple): k=(k,)
        r={n:x for n,x in zip(names,k)}; r["count"]=int(v); rows.append(r)
    rows.sort(key=lambda r:tuple(str(r[n]) for n in names)); return rows
def deserialize_counter(rows,names):
    c=Counter()
    for r in rows: c[tuple(r[n] for n in names)]=int(r["count"])
    return c
