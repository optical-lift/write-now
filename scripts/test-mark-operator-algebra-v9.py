#!/usr/bin/env python3
import copy
from mark_operator_algebra_v9_core import build_graph, iter_compositions, iter_transitions, operator_occurrence

cfg={"degreeCap":6,"multiplicityCap":3,"normalizedLengthBinWidth":0.05}

def row(ids=("a","b","c","d","s"), lengths=(2,3,4,5)):
    a,b,c,d,s=ids
    return {
        "observationId":"TEST","sourceGroupId":"SRC","lane":"train",
        "region":{"x":0,"y":0,"width":100,"height":100},
        "centers":[
            {"eventId":a,"kind":"ENDPOINT","degree":1,"x":0,"y":0},
            {"eventId":b,"kind":"JUNCTION","degree":3,"x":1,"y":0},
            {"eventId":c,"kind":"JUNCTION","degree":3,"x":2,"y":0},
            {"eventId":d,"kind":"ENDPOINT","degree":1,"x":3,"y":0},
            {"eventId":s,"kind":"ENDPOINT","degree":1,"x":1,"y":1},
        ],
        "edges":[
            {"a":a,"b":b,"pathSteps":lengths[0],"selfLoop":False},
            {"a":b,"b":c,"pathSteps":lengths[1],"selfLoop":False},
            {"a":c,"b":d,"pathSteps":lengths[2],"selfLoop":False},
            {"a":b,"b":s,"pathSteps":lengths[3],"selfLoop":False},
        ]
    }

base=row();g=build_graph(base,cfg,"lengthAware")
occ=operator_occurrence(g,"a","b","c",cfg)
assert occ["operatorId"] != occ["reverseOperatorId"], "typed ports should distinguish reverse when endpoint classes differ"
# Changing only the traversed input/output edge lengths changes state values but not the operator core.
changed=row(lengths=(40,45,4,5));gc=build_graph(changed,cfg,"lengthAware")
occ2=operator_occurrence(gc,"a","b","c",cfg)
assert occ2["operatorId"] == occ["operatorId"], "operator leaked traversed edge-state values"
assert occ2["inputState"] != occ["inputState"] or occ2["outputState"] != occ["outputState"], "test failed to alter interface state"
# Renaming event IDs and reordering rows cannot change the anonymous state/operator multiset.
renamed=row(ids=("q5","q2","q9","q1","q7"));renamed["centers"].reverse();renamed["edges"].reverse();gr=build_graph(renamed,cfg,"lengthAware")
base_trans=sorted((x["operatorId"],x["reverseOperatorId"],x["inputState"],x["outputState"]) for x in iter_transitions(g,cfg))
ren_trans=sorted((x["operatorId"],x["reverseOperatorId"],x["inputState"],x["outputState"]) for x in iter_transitions(gr,cfg))
assert base_trans == ren_trans, "event-ID or row-order dependence detected"
base_comp=sorted((x["operatorA"],x["operatorB"],x["state0"],x["state1"],x["state2"]) for x in iter_compositions(g,cfg))
ren_comp=sorted((x["operatorA"],x["operatorB"],x["state0"],x["state1"],x["state2"]) for x in iter_compositions(gr,cfg))
assert base_comp == ren_comp, "composition changed under event renaming"
assert any(x["operatorA"] and x["operatorB"] for x in iter_compositions(g,cfg)), "four-center composition not enumerated"
print("mark operator algebra v9 synthetic invariance tests passed")
