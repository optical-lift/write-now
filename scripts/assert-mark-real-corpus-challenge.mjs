import fs from "node:fs/promises";
import path from "node:path";

const reportPath=process.env.MARK_REAL_CORPUS_REPORT ?? "artifacts/mark-real-corpus-report-v1/mark-real-corpus-challenge-report-v3.json";
const outDir=process.env.MARK_REAL_CORPUS_VERDICT_OUT ?? "artifacts/mark-real-corpus-verdict-v1";
const report=JSON.parse(await fs.readFile(reportPath,"utf8"));
if(report.schema!=="mark_real_corpus_challenge_report_v3")throw new Error(`unsupported real-corpus report ${report.schema}`);
const pMax=Number(process.env.MARK_V5_NULL_P_MAX??0.05);
const controlMax=Number(process.env.MARK_V5_CONTROL_MAX_WHOLE_ACCEPTANCE??0.25);
const holdoutMarginMin=Number(process.env.MARK_V5_HOLDOUT_CONTROL_MARGIN_MIN??0.10);
const spatialFamilySurvivalMax=Number(process.env.MARK_V5_SPATIAL_FAMILY_SURVIVAL_MAX??0.50);
const spatialDistanceInflationMin=Number(process.env.MARK_V5_SPATIAL_DISTANCE_INFLATION_MIN??1.50);
const g=report.globalValidation;
const holdoutRate=g.holdoutAccepted/Math.max(1,g.holdoutWholeObjects),controlRate=g.controlAccepted/Math.max(1,g.controlWholeObjects),holdoutAbstained=g.holdoutWholeObjects-g.holdoutAccepted;
const replicatedCandidate=report.candidates.find(row=>row.trainInstitutions.length>=2&&row.holdoutWholeAccepted>=1&&row.holdoutVisuallyNontrivial>=1&&row.controlWholeAccepted===0)??null;
const checks=[
  {id:"null_tightness",pass:g.nullTightnessP<=pMax,value:g.nullTightnessP,requirement:`<=${pMax}`},
  {id:"null_recurrence",pass:g.nullRecurrenceP<=pMax,value:g.nullRecurrenceP,requirement:`<=${pMax}`},
  {id:"holdout_recurrence",pass:g.holdoutAccepted>=1,value:g.holdoutAccepted,requirement:">=1 whole holdout accepted"},
  {id:"active_abstention",pass:holdoutAbstained>=1,value:holdoutAbstained,requirement:">=1 whole holdout abstained"},
  {id:"unrelated_control_rejection",pass:controlRate<=controlMax,value:+controlRate.toFixed(6),requirement:`whole control acceptance <=${controlMax}`},
  {id:"holdout_beats_control",pass:holdoutRate-controlRate>=holdoutMarginMin,value:+(holdoutRate-controlRate).toFixed(6),requirement:`holdout-control whole acceptance margin >=${holdoutMarginMin}`},
  {id:"visually_nontrivial_replication",pass:g.holdoutAcceptedVisuallyNontrivial>=1,value:g.holdoutAcceptedVisuallyNontrivial,requirement:">=1 accepted holdout whole object not explained by cheap whole-image dHash"},
  {id:"spatial_original_family_survival",pass:g.spatialOriginalFamilySurvivalRate<=spatialFamilySurvivalMax,value:g.spatialOriginalFamilySurvivalRate,requirement:`spatially destroyed members surviving their frozen original family <=${spatialFamilySurvivalMax}`},
  {id:"spatial_prototype_distance_inflation",pass:g.spatialMedianPrototypeDistanceInflation>=spatialDistanceInflationMin,value:g.spatialMedianPrototypeDistanceInflation,requirement:`median distance to frozen real family prototype >=${spatialDistanceInflationMin}x original`},
  {id:"cross_institution_candidate",pass:Boolean(replicatedCandidate),value:replicatedCandidate?.familyId??null,requirement:"at least one family spans >=2 train institutions, recurs in unseen holdout, is visually nontrivial there, and accepts zero whole controls"},
];
const pass=checks.every(row=>row.pass);
const verdict={schema:"mark_real_corpus_challenge_verdict_v2",generatedAt:new Date().toISOString(),reportSchema:report.schema,verdict:pass?"PASS":"FAIL",contract:{allChecksRequired:true,thresholds:{pMax,controlMax,holdoutMarginMin,spatialFamilySurvivalMax,spatialDistanceInflationMin},spatialRuler:"real training scaler, family prototypes, and family acceptance envelopes are frozen before the spatial-null observations are scored",failureMeaning:"The v5 challenge did not satisfy its predeclared hostile validation contract. A failure is a valid experimental result and must not be promoted as evidence."},rates:{holdoutWholeAcceptance:+holdoutRate.toFixed(6),controlWholeAcceptance:+controlRate.toFixed(6),holdoutControlMargin:+(holdoutRate-controlRate).toFixed(6)},replicatedCandidateFamilyId:replicatedCandidate?.familyId??null,checks};
await fs.mkdir(outDir,{recursive:true});
await fs.writeFile(path.join(outDir,"mark-real-corpus-challenge-verdict-v2.json"),`${JSON.stringify(verdict,null,2)}\n`);
await fs.writeFile(path.join(outDir,"summary.txt"),[`schema=${verdict.schema}`,`verdict=${verdict.verdict}`,`holdout_whole_acceptance=${verdict.rates.holdoutWholeAcceptance}`,`control_whole_acceptance=${verdict.rates.controlWholeAcceptance}`,`holdout_control_margin=${verdict.rates.holdoutControlMargin}`,`replicated_candidate_family=${verdict.replicatedCandidateFamilyId??"none"}`,...checks.map(row=>`${row.id}=${row.pass?"PASS":"FAIL"} value=${row.value} requirement=${row.requirement}`)].join("\n")+"\n");
console.log(`Mark v5 hostile challenge verdict: ${verdict.verdict}`);
for(const row of checks)console.log(`${row.pass?"PASS":"FAIL"} ${row.id}: ${row.value} (${row.requirement})`);
if(!pass)throw new Error(`Mark v5 hostile challenge failed: ${checks.filter(row=>!row.pass).map(row=>row.id).join(", ")}`);
