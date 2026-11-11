import {readFileSync,mkdirSync,appendFileSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {pathToFileURL} from 'node:url';
const [sourceRoot,casesFile,outDir]=process.argv.slice(2);
if(!sourceRoot||!casesFile||!outDir)throw Error('Usage: node evaluate-assessment-shadow.mjs SOURCE_ROOT FROZEN_CASES NEW_OUTPUT_DIR');
const cases=JSON.parse(readFileSync(casesFile,'utf8'));
if(!Array.isArray(cases)||!cases.length||new Set(cases.map(c=>c.id)).size!==cases.length||cases.some(c=>typeof c.id!=='string'||!/^[-a-zA-Z0-9.]+$/.test(c.id)||typeof c.answer!=='string'||!c.answer.trim()||c.answer.length>4000||!Array.isArray(c.expected)||c.expected.length!==3||c.expected.some(v=>typeof v!=='boolean')))throw Error('Invalid frozen cases');
const dir=resolve(outDir);mkdirSync(dir);
const {LocalModel}=await import(pathToFileURL(resolve(sourceRoot,'integration/ai/core/src/local-model.mjs')));
const {validateAssessment,rubrics}=await import(pathToFileURL(resolve(sourceRoot,'integration/ai/core/src/assessment.mjs')));
if(cases.some(c=>!Object.hasOwn(rubrics.tasks,c.task_key)))throw Error('Unsupported task; do not extend mapping implicitly');
const rows=[];let stages=[];
const record=x=>{appendFileSync(resolve(dir,'events.jsonl'),JSON.stringify({at:new Date().toISOString(),...x})+'\n');console.log(JSON.stringify(x));};
// Read-only instrumentation around the existing adapter. Request payload is unchanged.
const measuredFetch=async(url,options)=>{
 const started=performance.now();const response=await fetch(url,options);
 if(options?.method!=='POST'||!url.endsWith('/v1/chat/completions'))return response;
 const stage=stages.length===0?'proposal':'verification';
 if(!response.ok){stages.push({stage,ms:performance.now()-started,http_status:response.status,terminal_body:false});return response;}
 return {ok:response.ok,text:async()=>{try{return await response.text();}finally{stages.push({stage,ms:performance.now()-started,http_status:response.status,terminal_body:true});}}};
};
let model;
try{
 model=await LocalModel.loadOwned({modelKey:'qwen3.5-9b',contextLength:8192,fetchImpl:measuredFetch,lockPath:resolve(dir,'model.lock'),recoveryLog:event=>appendFileSync(resolve(dir,'recovery.jsonl'),JSON.stringify(event)+'\n')});record({event:'loaded',instance:model.model});
 for(const c of cases){
  stages=[];const start=performance.now();
  const req={role:'assess',lesson:c.task_key.slice(0,2),message:c.answer,assessment:{task_key:c.task_key}};
  try{
   const raw=await model.generate(req,{signal:AbortSignal.timeout(60000),maxTokens:192});let result=null,error=null;
   try{result=validateAssessment(raw,c.answer);}catch(e){error=e.message;}
   let counters=[];try{const p=JSON.parse(raw.candidate.answer);counters=Object.entries(p).filter(([,v])=>v.counter!==null).map(([criterion,v])=>({criterion,fragment:v.counter}));}catch{}
   const diagnosis=error==='assessment disagreement'?'review_disagreement':error?'technical_invalid_output':counters.length?'model_reports_contradiction':'assessed';
   const row={id:c.id,source_id:c.source_id??c.id,task_key:c.task_key,expected:c.expected,actual:result?.checks??null,match:JSON.stringify(result?.checks)===JSON.stringify(c.expected),ms:performance.now()-start,stages:[...stages],diagnosis,counters,error,raw,result};
   rows.push(row);writeFileSync(resolve(dir,c.id+'.json'),JSON.stringify(row,null,2));record({event:'case',id:c.id,match:row.match,actual:row.actual,ms:row.ms,stages:row.stages,diagnosis,error});
  }catch(e){record({event:'transport_error',id:c.id,error:e.message,stages});throw e;}
 }
 const summary={total:rows.length,correct:rows.filter(r=>r.match).length,wrong:rows.filter(r=>r.actual!==null&&!r.match).length,abstentions:rows.filter(r=>r.actual===null).length,max_ms:Math.max(...rows.map(r=>r.ms))};writeFileSync(resolve(dir,'summary.json'),JSON.stringify(summary,null,2));record({event:'summary',...summary});
}finally{if(model){if(model.state.phase==='idle'){model.coordinator.begin();model.quarantineActive();}const retired=await model.retireOwnedInstance();record({event:'retired',proven:retired,instance:model.model});if(!retired)process.exitCode=2;}}
