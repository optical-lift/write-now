#!/usr/bin/env python3
"""V45 implementation-only equivalence gate.

V45 must preserve V43/V44 probability arithmetic and V44 operator occurrence
identity while eliminating the per-observation operator memoization.
"""
import importlib.util
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

v43=load("v43core",ROOT/"scripts"/"mark-v43"/"mark_operator_algebra_v9_core.py")
v44=load("v44core",ROOT/"scripts"/"mark-v44"/"mark_operator_algebra_v9_core.py")
v45=load("v45core",ROOT/"scripts"/"mark-v45"/"mark_operator_algebra_v9_core.py")

states=["S0","S1","S2","OTHER"]
ops=["OPA","OPB","OPC"]
def rows(keys,tuples):
    return [dict(zip(keys,t[:-1]),count=t[-1]) for t in tuples]
model={
 "states":states,
 "smoothing":{"globalAdditiveAlpha":0.5,"operatorBackoffPseudoCount":8.0,"baselineBackoffPseudoCount":8.0},
 "counts":{
  "baseOneStep":rows(("inputState","outputState"),[("S0","S0",9),("S0","S1",4),("S1","S2",7),("S2","S0",3),("OTHER","OTHER",5)]),
  "baseTwoStep":rows(("inputState","outputState"),[("S0","S2",8),("S0","S1",2),("S1","S0",5),("S2","S2",6),("OTHER","OTHER",4)]),
  "operatorOneStep":rows(("operatorId","inputState","outputState"),[
   ("OPA","S0","S1",11),("OPA","S1","S2",7),("OPA","S2","S0",5),
   ("OPB","S0","S2",8),("OPB","S1","S0",9),("OPB","S2","S1",6),
   ("OPC","S0","S0",4),("OPC","S1","S1",4),("OPC","S2","S2",4)]),
  "firstOperatorTwoStep":rows(("operatorId","inputState","outputState"),[("OPA","S0","S2",6),("OPA","S1","S0",4),("OPB","S0","S1",5),("OPB","S2","S0",3)]),
  "secondOperatorTwoStep":rows(("operatorId","inputState","outputState"),[("OPA","S0","S1",3),("OPA","S2","S0",5),("OPB","S0","S2",5),("OPB","S1","S0",4)]),
  "directPairTwoStep":rows(("operatorA","operatorB","inputState","outputState"),[
   ("OPA","OPB","S0","S2",7),("OPA","OPB","S1","S0",4),("OPB","OPA","S0","S1",6),("OPC","OPA","S2","S0",3)])
 }}
p43=v43.build_probability_functions(model); p44=v44.build_probability_functions(model); p45=v45.build_probability_functions(model)
for i in states+["UNSEEN"]:
  for o in states+["UNSEEN"]:
    for key,args in (("p1",(i,o)),("p2",(i,o))):
      assert p43[key](*args)==p44[key](*args)==p45[key](*args)
    for a in ops+["OPX"]:
      for key,args in (("pop",(a,i,o)),("pa2",(a,i,o)),("pb2",(a,i,o))):
        assert p43[key](*args)==p44[key](*args)==p45[key](*args)
      for b in ops+["OPY"]:
        assert p43["pcomp"](a,b,i,o)==p44["pcomp"](a,b,i,o)==p45["pcomp"](a,b,i,o)
        assert p43["ppair"](a,b,i,o)==p44["ppair"](a,b,i,o)==p45["ppair"](a,b,i,o)
for n in range(10000):
  p45["pcomp"](f"A{n}",f"B{n}","S0","S1")
info=p45["pcomp"].cache_info()
assert info.maxsize==8192 and info.currsize<=8192, info

cfg={"degreeCap":6,"multiplicityCap":3,"normalizedLengthBinWidth":0.05}
row={
 "observationId":"TEST","sourceGroupId":"SRC","lane":"train","region":{"width":100,"height":80},
 "centers":[
  {"eventId":"a","kind":"ENDPOINT","degree":1},
  {"eventId":"b","kind":"JUNCTION","degree":4},
  {"eventId":"c","kind":"JUNCTION","degree":3},
  {"eventId":"d","kind":"ENDPOINT","degree":1},
  {"eventId":"e","kind":"ENDPOINT","degree":1}],
 "edges":[
  {"a":"a","b":"b","selfLoop":False,"pathSteps":10},
  {"a":"b","b":"c","selfLoop":False,"pathSteps":15},
  {"a":"c","b":"d","selfLoop":False,"pathSteps":12},
  {"a":"b","b":"e","selfLoop":False,"pathSteps":8},
  {"a":"b","b":"b","selfLoop":True,"pathSteps":2}]
}
for variant in ("lengthAware","topology"):
  g44=v44.build_graph(row,cfg,variant); g45=v45.build_graph(row,cfg,variant)
  for center,ns in sorted(g44["adjacency"].items()):
    for u in sorted(ns):
      for w in sorted(ns):
        if u==w: continue
        assert v44.operator_occurrence(g44,u,center,w,cfg)==v45.operator_occurrence(g45,u,center,w,cfg)
  assert len(g44["operatorCache"])>0
  assert len(g45["operatorCache"])==0
print(f"V45 implementation equivalence PASS; pcomp_cache={info}")
