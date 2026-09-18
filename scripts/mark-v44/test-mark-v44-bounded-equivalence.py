#!/usr/bin/env python3
"""Implementation-only equivalence gate for Mark V44.

Compares the frozen V43 unbounded composition cache against the V44 bounded
cache over the same finite model. The arithmetic order and probability
equations must be exactly equal. This test also proves the V44 cache is bounded.
"""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def load_module(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

old=load_module("v43core",ROOT/"scripts"/"mark-v43"/"mark_operator_algebra_v9_core.py")
new=load_module("v44core",ROOT/"scripts"/"mark-v44"/"mark_operator_algebra_v9_core.py")

states=["S0","S1","S2","OTHER"]
ops=["OPA","OPB","OPC"]

def rows(keys, tuples):
    return [dict(zip(keys,t[:-1]),count=t[-1]) for t in tuples]

model={
    "states":states,
    "smoothing":{"globalAdditiveAlpha":0.5,"operatorBackoffPseudoCount":8.0,"baselineBackoffPseudoCount":8.0},
    "counts":{
        "baseOneStep":rows(("inputState","outputState"),[
            ("S0","S0",9),("S0","S1",4),("S1","S2",7),("S2","S0",3),("OTHER","OTHER",5)
        ]),
        "baseTwoStep":rows(("inputState","outputState"),[
            ("S0","S2",8),("S0","S1",2),("S1","S0",5),("S2","S2",6),("OTHER","OTHER",4)
        ]),
        "operatorOneStep":rows(("operatorId","inputState","outputState"),[
            ("OPA","S0","S1",11),("OPA","S1","S2",7),("OPA","S2","S0",5),
            ("OPB","S0","S2",8),("OPB","S1","S0",9),("OPB","S2","S1",6),
            ("OPC","S0","S0",4),("OPC","S1","S1",4),("OPC","S2","S2",4)
        ]),
        "firstOperatorTwoStep":rows(("operatorId","inputState","outputState"),[
            ("OPA","S0","S2",6),("OPA","S1","S0",4),("OPB","S0","S1",5),("OPB","S2","S0",3)
        ]),
        "secondOperatorTwoStep":rows(("operatorId","inputState","outputState"),[
            ("OPA","S0","S1",3),("OPA","S2","S0",5),("OPB","S0","S2",5),("OPB","S1","S0",4)
        ]),
        "directPairTwoStep":rows(("operatorA","operatorB","inputState","outputState"),[
            ("OPA","OPB","S0","S2",7),("OPA","OPB","S1","S0",4),
            ("OPB","OPA","S0","S1",6),("OPC","OPA","S2","S0",3)
        ])
    }
}
po=old.build_probability_functions(model)
pn=new.build_probability_functions(model)
inputs=states+["UNSEEN"]
outputs=states+["UNSEEN"]
for i in inputs:
    for o in outputs:
        assert po["p1"](i,o)==pn["p1"](i,o)
        assert po["p2"](i,o)==pn["p2"](i,o)
        for a in ops+["OPX"]:
            assert po["pop"](a,i,o)==pn["pop"](a,i,o)
            assert po["pa2"](a,i,o)==pn["pa2"](a,i,o)
            assert po["pb2"](a,i,o)==pn["pb2"](a,i,o)
            for b in ops+["OPY"]:
                assert po["pcomp"](a,b,i,o)==pn["pcomp"](a,b,i,o)
                assert po["ppair"](a,b,i,o)==pn["ppair"](a,b,i,o)

# Force more than the cache capacity with exact-backoff operator IDs.
for n in range(10000):
    pn["pcomp"](f"A{n}",f"B{n}","S0","S1")
info=pn["pcomp"].cache_info()
assert info.maxsize==8192, info
assert info.currsize<=8192, info
print(f"V44 bounded equivalence PASS; cache={info}")
