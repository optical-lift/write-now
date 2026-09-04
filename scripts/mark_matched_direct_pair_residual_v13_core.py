#!/usr/bin/env python3
import hashlib, math
from collections import Counter, defaultdict
from mark_state_operator_separation_v12_core import canonical_sha, history_before, mapped_stream, ngram_distribution, state_assigner, compose_kernel, direct_pair_prob, tv, signflip_p


def thaw_v12(packet, protocol):
    sp=packet["space"]
    tabs=[defaultdict(Counter) for _ in range(5)]; totals=[Counter() for _ in range(5)]
    for r in sp["ngramRows"]:
        o=int(r["order"]); c=tuple(r["context"]); tabs[o][c][r["outcome"]]+=int(r["count"]); totals[o][c]+=int(r["count"])
    exact={tuple(r["history"]):int(r["state"]) for r in sp["exactHistoryStates"]}
    hc=Counter({tuple(r["history"]):int(r["count"]) for r in sp["exactHistoryStates"]})
    vocab=Counter(tabs[0][()])
    space={"tokens":sp["tokens"],"tabs":tabs,"totals":totals,"vocab":vocab,"fpOutcomes":sp["fingerprintOutcomes"],"centers":sp["centroids"],"exact":exact,"historyCounts":hc}
    st=state_assigner(space,protocol); K=int(packet["selectedStateCount"])
    emit=[Counter() for _ in range(K)]; emitN=[0]*K
    for r in packet["machine"]["emissionRows"]:
        s=int(r["state"]); emit[s][r["outcome"]]+=int(r["count"]); emitN[s]+=int(r["count"])
    trans=defaultdict(Counter); transN=Counter()
    for r in packet["machine"]["transitionRows"]:
        k=(int(r["state"]),r["glyph"]); trans[k][int(r["nextState"])]+=int(r["count"]); transN[k]+=int(r["count"])
    trans0=[Counter() for _ in range(K)]; trans0N=[0]*K
    for r in packet["machine"]["stateOnlyTransitionRows"]:
        s=int(r["state"]); trans0[s][int(r["nextState"])]+=int(r["count"]); trans0N[s]+=int(r["count"])
    pair=defaultdict(Counter); pairN=Counter()
    for r in packet["machine"]["directPairRows"]:
        k=(int(r["state"]),r["firstGlyph"],r["secondGlyph"]); pair[k][r["outcome"]]+=int(r["count"]); pairN[k]+=int(r["count"])
    support=Counter({(int(r["state"]),r["glyph"]):int(r["count"]) for r in packet["machine"]["stateGlyphSupport"]})
    gc=Counter(); GN=0
    for c in emit: gc.update(c); GN+=sum(c.values())
    return space,{"K":K,"emit":emit,"emitN":emitN,"trans":trans,"transN":transN,"trans0":trans0,"trans0N":trans0N,"pair":pair,"pairN":pairN,"opSupport":support,"global":gc,"globalN":GN,"state":st}


def build_history_pair(rows, common, eligible, machine, L):
    counts=defaultdict(Counter); totals=Counter(); docs=defaultdict(set)
    for row in rows:
        raw,s=mapped_stream(row["words"],common); doc=row["anonymousInscriptionId"]
        for i in range(1,len(s)-2):
            a,b=raw[i],raw[i+1]
            if a not in eligible or b not in eligible: continue
            H=history_before(s,i,L); S=machine["state"](H); z=s[i+2]; k=(H,S,a,b)
            counts[k][z]+=1; totals[k]+=1; docs[k].add(doc)
    return counts,totals,docs


def history_pair_prob(counts,totals,m,H,S,a,b,y,protocol):
    back=direct_pair_prob(m,S,a,b,y,protocol); k=(tuple(H),S,a,b); n=totals[k]
    if not n: return back
    lam=float(protocol["probabilityModel"]["historyPairBackoffPseudoCount"])
    return (counts[k][y]+lam*back)/(n+lam)


def ngram_prob(space,context,order,y,protocol):
    p=ngram_distribution(tuple(context[-order:]),space["tokens"],space["tabs"],space["totals"],float(protocol["probabilityModel"]["globalAdditiveAlpha"]),float(protocol["probabilityModel"]["hierarchicalBackoffPseudoCount"]))
    try: return p[space["tokens"].index(y)]
    except ValueError: return 1e-300


def select_panel(m,protocol):
    cfg=protocol["matchedResidualPanel"]; mn=int(cfg["minimumTrainStatePairOccurrences"]); ratio_max=float(cfg["maximumTrainSupportRatio"]); qmax=float(cfg["maximumFactorizedKernelTv"]); dmin=float(cfg["minimumDirectPairKernelTv"])
    supported=[k for k,n in m["pairN"].items() if n>=mn]; by=defaultdict(list)
    for S,a,b in supported: by[(S,a)].append(b)
    out=[]
    for S,a,b in sorted(supported):
        n=m["pairN"][(S,a,b)]; qa=compose_kernel(m,S,a,b,protocol,"factorized"); da={y:direct_pair_prob(m,S,a,b,y,protocol) for y in m["global"]}; best=None
        for bp in sorted(by[(S,a)]):
            if bp==b: continue
            np=m["pairN"][(S,a,bp)]; ratio=max(n/np,np/n)
            if ratio>ratio_max: continue
            qs=compose_kernel(m,S,a,bp,protocol,"factorized"); qtv=tv(qa,qs)
            if qtv>qmax: continue
            ds={y:direct_pair_prob(m,S,a,bp,y,protocol) for y in m["global"]}; dtv=tv(da,ds)
            if dtv<dmin: continue
            sd=abs(math.log2(n/np)); tie=hashlib.sha256(f"{S}|{a}|{b}|{bp}".encode()).hexdigest(); cand=(qtv,sd,-dtv,tie,bp,np,ratio,dtv)
            if best is None or cand[:4]<best[:4]: best=cand
        if best:
            out.append({"state":S,"firstGlyph":a,"actualSecondGlyph":b,"substituteSecondGlyph":best[4],"actualSupport":n,"substituteSupport":best[5],"supportRatio":best[6],"factorizedKernelTv":best[0],"directPairKernelTv":best[7]})
    return out


def encode_history(counts):
    out=[]
    for (H,S,a,b),c in counts.items():
        for y,n in c.items(): out.append({"history":list(H),"state":S,"firstGlyph":a,"secondGlyph":b,"outcome":y,"count":n})
    out.sort(key=lambda r:(r["history"],r["state"],r["firstGlyph"],r["secondGlyph"],r["outcome"])); return out


def decode_history(rows):
    counts=defaultdict(Counter); totals=Counter()
    for r in rows:
        k=(tuple(r["history"]),int(r["state"]),r["firstGlyph"],r["secondGlyph"]); counts[k][r["outcome"]]+=int(r["count"]); totals[k]+=int(r["count"])
    return counts,totals


def panel_lookup(rows): return {(int(r["state"]),r["firstGlyph"],r["actualSecondGlyph"]):r for r in rows}


def summarize_docs(by_doc,iters,salt):
    vals=[sum(by_doc[d])/len(by_doc[d]) for d in sorted(by_doc) if by_doc[d]]; mean=sum(vals)/max(1,len(vals)); pos=sum(v>0 for v in vals)/max(1,len(vals))
    return {"inscriptions":len(vals),"meanBits":mean,"medianBits":sorted(vals)[len(vals)//2] if vals else None,"positiveFraction":pos,"signFlipP":signflip_p(vals,int(iters),salt)}
