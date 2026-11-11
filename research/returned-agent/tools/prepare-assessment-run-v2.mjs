import {readFileSync} from 'node:fs';
import {freezeRun} from './frozen-assessment-run-v2.mjs';
const [source,dataset,rubric,settings,plan]=process.argv.slice(2);
if(!plan)throw Error('Usage: node prepare-assessment-run-v2.mjs SOURCE_ROOT FROZEN_DIR REVIEWED_RUBRICS SETTINGS_JSON NEW_PLAN_JSON');
const result=freezeRun(source,dataset,rubric,JSON.parse(readFileSync(settings,'utf8').replace(/^\uFEFF/,'')),plan);
console.log(JSON.stringify({plan,data_origin:result.data_origin,primary_series:1,source_files:Object.keys(result.source_sha256).length}));
