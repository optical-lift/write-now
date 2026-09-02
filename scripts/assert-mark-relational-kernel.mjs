import fs from "node:fs/promises";

const graphPath=process.env.MARK_RELATIONAL_GRAPHS??"artifacts/mark-relational-graphs-v1/mark-relational-graphs-blind-v1.json";
const worldPath=process.env.MARK_RELATIONAL_WORLD??"artifacts/mark-relational-world-v1/mark-relational-program-world-blind-v1.json";
const evalPath=process.env.MARK_RELATIONAL_EVAL??"artifacts/mark-relational-transfer-v1/mark-relational-transfer-evaluation-blind-v1.json";
const graphs=JSON.parse(await fs.readFile(graphPath,"utf8")),world=JSON.parse(await fs.readFile(worldPath,"utf8")),evaluation=JSON.parse(await fs.readFile(evalPath,"utf8"));
const checks=[
  ["graph_schema",graphs.schema==="mark_relational_graph_corpus_blind_v1"],
  ["train_exists",graphs.corpus?.train>=4],
  ["two_transfer_lanes_exist",graphs.corpus?.holdout>=1&&graphs.corpus?.control>=1],
  ["world_schema",world.schema==="mark_relational_program_world_blind_v1"],
  ["no_visual_feature_distance",world.discoveryContract?.visualFeatureDistanceUsed===false],
  ["no_whole_image_similarity",world.discoveryContract?.wholeImageSimilarityUsed===false],
  ["relational_primitives_exercised",world.primitives?.length>=1],
  ["masked_grammar_exercised",world.grammarRules?.length>=1],
  ["evaluation_schema",evaluation.schema==="mark_relational_transfer_evaluation_blind_v1"],
  ["no_presumed_negative_category",evaluation.evaluationContract?.categoryAssumption===false],
  ["rewired_null_exercised",evaluation.transferA?.rewiredNull?.iterations>=4&&evaluation.transferB?.rewiredNull?.iterations>=4],
  ["masked_transfer_a_exercised",evaluation.transferA?.observed?.examples>=1],
  ["masked_transfer_b_exercised",evaluation.transferB?.observed?.examples>=1],
];
for(const[name,pass]of checks)console.log(`${pass?"PASS":"FAIL"} ${name}`);
const failed=checks.filter(([,pass])=>!pass);if(failed.length)throw new Error(`Mark v6 relational kernel contract failed: ${failed.map(([name])=>name).join(", ")}`);
console.log("Mark v6 relational kernel contract passed. No historical or semantic hypothesis is asserted by this CI result.");
