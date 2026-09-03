#!/usr/bin/env python3
import hashlib, json, os
from collections import defaultdict
from pathlib import Path

transition_dir=Path(os.environ.get("MARK_TRANSITION_PACKET","artifact-staging/transition"))
context_dir=Path(os.environ.get("MARK_SOURCE_CONTEXT","artifact-staging/context"))
out_dir=Path(os.environ.get("MARK_TRANSITION_REJOIN_OUT","artifacts/mark-state-transition-grammar-v1-context"))

def load_json(p): return json.loads(Path(p).read_text(encoding="utf-8"))
def canonical_sha(v): return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(",",":"),ensure_ascii=False).encode()).hexdigest()

packet=load_json(transition_dir/"state-transition-grammar-discovery.json")
if packet.get("schema")!="mark_state_transition_grammar_discovery_v1": raise RuntimeError("unexpected transition packet")
sha=packet.get("stateTransitionGrammarDiscoverySha256")
core={k:v for k,v in packet.items() if k!="stateTransitionGrammarDiscoverySha256"}
if canonical_sha(core)!=sha: raise RuntimeError("transition packet SHA mismatch")
if packet.get("provenanceAvailableDuringDiscovery"): raise RuntimeError("transition packet was not blind")

context_summary=load_json(context_dir/"summary.json")
if context_summary.get("schema")!="mark_source_rule_atlas_context_rejoin_v1": raise RuntimeError("unexpected context schema")
contexts={}
with (context_dir/"source-rule-context.jsonl").open(encoding="utf-8") as h:
    for line in h:
        if not line.strip(): continue
        r=json.loads(line); s=r["blindRow"]["sourceGroupId"]
        contexts.setdefault(s,r["sourceContext"])

profiles=[]
with (transition_dir/"source-transition-profiles.jsonl").open(encoding="utf-8") as h:
    for line in h:
        if line.strip(): profiles.append(json.loads(line))
profile_by={r["sourceGroupId"]:r for r in profiles}
missing=sorted(set(profile_by)-set(contexts))
if missing: raise RuntimeError(f"missing source provenance for {len(missing)} transition profiles")

def enrich_examples(motif, kind, direction, limit=8):
    candidates=[]
    for s,p in profile_by.items():
        counts=p["edgeCounts"] if kind=="edge" else p["programCounts"]
        observed=int(counts.get(motif,0))
        if kind=="edge":
            prefix=motif.split("->")[0]+"->"
            opportunity=sum(int(v) for k,v in counts.items() if k.startswith(prefix))
        else:
            parts=motif.split("->"); prefix="->".join(parts[:2])+"->"
            opportunity=sum(int(v) for k,v in counts.items() if k.startswith(prefix))
        if opportunity<3: continue
        rate=observed/opportunity
        score=(rate,observed,opportunity) if direction=="enrichment" else (-rate,opportunity,-observed)
        candidates.append((score,s,observed,opportunity,rate))
    candidates.sort(reverse=True)
    out=[]
    for _,s,observed,opportunity,rate in candidates[:limit]:
        out.append({"sourceGroupId":s,"lane":profile_by[s]["lane"],"observed":observed,
                    "opportunity":opportunity,"conditionalRate":rate,"sourceContext":contexts[s]})
    return out

top_edges=[]
for row in packet["transitionEdges"][:9]:
    top_edges.append({"transitionRank":row["transitionRank"],"motif":row["motif"],"direction":row["direction"],
                      "standardizedDeviation":row["standardizedDeviation"],"distinctSourceSupport":row["distinctSourceSupport"],
                      "examples":enrich_examples(row["motif"],"edge",row["direction"])})
top_programs=[]
for row in packet["transitionPrograms"][:12]:
    top_programs.append({"programRank":row["programRank"],"motif":row["motif"],"direction":row["direction"],
                         "standardizedDeviation":row["standardizedDeviation"],"distinctSourceSupport":row["distinctSourceSupport"],
                         "examples":enrich_examples(row["motif"],"program",row["direction"])})

institution=defaultdict(lambda:{"sources":set(),"commitment":0,"returnToState2":0,"chains":0})
for p in profiles:
    ctx=contexts[p["sourceGroupId"]]; inst=ctx.get("institution","unknown")
    slot=institution[inst]; slot["sources"].add(p["sourceGroupId"]); slot["commitment"]+=int(p["commitmentCount"])
    slot["returnToState2"]+=int(p["returnToState2Count"]); slot["chains"]+=int(p["containmentChains"])
institution_rows=[]
for inst,slot in sorted(institution.items()):
    institution_rows.append({"institution":inst,"sources":len(slot["sources"]),"commitmentPrograms":slot["commitment"],
                             "returnToState2Programs":slot["returnToState2"],"containmentChains":slot["chains"],
                             "commitmentToReturnRatio":slot["commitment"]/(slot["returnToState2"]+1.0)})

core={
 "schema":"mark_state_transition_grammar_context_rejoin_v1",
 "sealedStateTransitionGrammarDiscoverySha256":sha,
 "blindTransitionStatisticsPreserved":True,
 "sourceContextAttachedAfterFreeze":True,
 "transitionEdges":packet["transitionEdges"],
 "transitionPrograms":packet["transitionPrograms"],
 "commitmentHysteresis":packet["commitmentHysteresis"],
 "sourceTransitionDynamics":packet["sourceTransitionDynamics"],
 "institutionDynamics":institution_rows,
 "topTransitionContextExamples":top_edges,
 "topProgramContextExamples":top_programs,
 "contract":{"transitionRanksUnchanged":True,"programRanksUnchanged":True,"statisticsUnchanged":True,
             "provenanceCouldNotDefineTransitionGrammar":True,"semanticMeaningNotAutomaticallyAssigned":True}
}
digest=canonical_sha(core); out={**core,"contextRejoinSha256":digest}
out_dir.mkdir(parents=True,exist_ok=True)
(out_dir/"state-transition-grammar-context-rejoin.json").write_text(json.dumps(out,indent=2,ensure_ascii=False)+"\n")
(out_dir/"summary.txt").write_text("\n".join([
 f"sealed_transition_sha256={sha}",
 f"context_rejoin_sha256={digest}",
 f"institutions={len(institution_rows)}",
 f"transition_ranks_preserved=true",
 f"program_ranks_preserved=true"
])+"\n")
print(json.dumps(out,indent=2,ensure_ascii=False))
