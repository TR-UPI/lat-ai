import {readFileSync,writeFileSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {runSeries,hash} from './frozen-assessment-run-v2.mjs';
const root=resolve(import.meta.dirname,'..'),base=join(root,'outputs/u02-runtime-controls-2026-11-11');
const protocol=JSON.parse(readFileSync(join(base,'known128-protocol.json'),'utf8'));
if(protocol.plan_sha256!==hash(readFileSync(join(base,'known128-plan.json'))))throw Error('Known128 plan changed');
const results=[];
for(let series=1;series<=3;series++){
 console.log(JSON.stringify({event:'start_series',series,at:new Date().toISOString()}));
 const result=await runSeries(join(base,'known128-plan.json'),series,join(base,'known128-live-'+series));results.push(result);
 console.log(JSON.stringify({event:'end_series',...result}));
 if(result.status!=='complete'){process.exitCode=2;break;}
}
writeFileSync(join(base,'known128-run-summary.json'),JSON.stringify({complete:results.length===3&&results.every(r=>r.status==='complete'),series:results.map(r=>({series:r.series,status:r.status,failure:r.failure,completed:r.completed,not_run:r.not_run,retirement_proven:r.retirement_proven})),automatic_retries:0},null,2)+'\n',{flag:'wx'});
