import {readFileSync,mkdirSync,appendFileSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const [sourceRoot,casesFile,outDir]=process.argv.slice(2);
if(!sourceRoot||!casesFile||!outDir)throw Error('Usage: node evaluate-assessment.mjs SOURCE_ROOT CASES_JSON NEW_OUTPUT_DIRECTORY');
const dir=resolve(outDir);
// Never mix a new experiment with earlier raw answers or recovery evidence.
mkdirSync(dir);
const {LocalModel}=await import(pathToFileURL(resolve(sourceRoot,'integration/ai/core/src/local-model.mjs')));
const {validateAssessment}=await import(pathToFileURL(resolve(sourceRoot,'integration/ai/core/src/assessment.mjs')));
const cases=JSON.parse(readFileSync(casesFile,'utf8'));
const rows=[];
const record=x=>{appendFileSync(resolve(dir,'events.jsonl'),JSON.stringify({at:new Date().toISOString(),...x})+'\n');console.log(JSON.stringify(x));};
let model;
try{
 model=await LocalModel.loadOwned({modelKey:'qwen3.5-9b',contextLength:8192,lockPath:resolve(dir,'model.lock'),recoveryLog:event=>appendFileSync(resolve(dir,'recovery.jsonl'),JSON.stringify(event)+'\n')});
 record({event:'loaded',instance:model.model});
 for(const c of cases){
  const req={role:'assess',lesson:c.task_key.startsWith('L1')?'L1':'L2',message:c.answer,assessment:{task_key:c.task_key}};
  const started=performance.now();
  try{
   const raw=await model.generate(req,{signal:AbortSignal.timeout(60000),maxTokens:192});
   let result=null,error=null;
   try{result=validateAssessment(raw,c.answer);}catch(e){error=e.message;}
   const row={id:c.id,task_key:c.task_key,expected:c.expected,actual:result?.checks??null,match:JSON.stringify(result?.checks)===JSON.stringify(c.expected),ms:performance.now()-started,error,raw,result};
   rows.push(row);writeFileSync(resolve(dir,c.id+'.json'),JSON.stringify(row,null,2));
   record({event:'case',id:c.id,match:row.match,expected:c.expected,actual:row.actual,ms:row.ms,error});
  }catch(e){record({event:'transport_error',id:c.id,error:e.message});throw e;}
 }
 const summary={total:rows.length,matched:rows.filter(r=>r.match).length,failed:rows.filter(r=>!r.match).map(r=>r.id),max_ms:Math.max(...rows.map(r=>r.ms))};
 writeFileSync(resolve(dir,'summary.json'),JSON.stringify(summary,null,2));record({event:'summary',...summary});
}finally{
 if(model){if(model.state.phase==='idle'){model.coordinator.begin();model.quarantineActive();}const retired=await model.retireOwnedInstance();record({event:'retired',proven:retired,instance:model.model});if(!retired)process.exitCode=2;}
}
