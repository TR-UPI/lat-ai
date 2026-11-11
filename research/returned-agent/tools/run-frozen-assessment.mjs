import {runSeries} from './frozen-assessment-run.mjs';
const [plan,series,out]=process.argv.slice(2);
if(!out)throw Error('Usage: node run-frozen-assessment.mjs PLAN_JSON SERIES_1_TO_3 NEW_OUTPUT_DIR');
const summary=await runSeries(plan,Number(series),out);console.log(JSON.stringify(summary));if(summary.status!=='complete')process.exitCode=2;
