import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
import {LocalModel} from '../lat-ai/integration/ai/core/src/local-model.mjs';
import {validateAssessment,validateCandidate} from '../lat-ai/integration/ai/core/src/assessment.mjs';
import {validateAssessment as verifyAssessment} from '../lat-ai/integration/ai/core/src/assessment-verifier.mjs';
import {sourceHashes} from './frozen-assessment-run.mjs';
const root=resolve(import.meta.dirname,'..'),out=join(root,'outputs/u02-investigation-2026-11-11/reverse-crossover');
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const save=(path,value)=>writeFileSync(path,JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const planFile=join(out,'order-protocol.json');
if(process.argv[2]==='freeze'){
 const known=[...read(join(root,'outputs/assessment-v3-2026-11-11/regression128-with-evidence.json')),...read(join(root,'outputs/assessment-v3-2026-11-11/holdout32.json'))];
 const cases=Object.fromEntries(['U02','N05','U15','V11'].map(id=>[id,known.find(c=>c.id===id)]));
 const plan={frozen_utc:new Date().toISOString(),purpose:'Known-case causal diagnostic, not a quality holdout. No prompt/rubric/gate changes.',source_sha256:sourceHashes(join(root,'lat-ai')),script_sha256:sha(readFileSync(import.meta.filename)),answer_cases:cases,model_fingerprint:read(join(out,'model-fingerprint.json')),config:{model_key:'qwen3.5-9b',context_length:8192,parallel:1,budget_ms:60000,max_tokens:192},sessions:[{id:'A-B-A',order:['N05','U15','U02','V11','U02','N05','U15','U02']}],interpretation:'Within ONE owned model instance: A=N05,U15,U02; then B=V11,U02; then A=N05,U15,U02. Reverse follow-up because B-A-B did not switch back after its first U02 undergrade. Follow-up diagnostic frozen after the initial order association, not an independent holdout. This separates instance identity from order; does not isolate cache internals. No automatic retries; stop whole experiment on transport or retirement failure. Small deterministic diagnostic only, cannot isolate all GPU/runtime sources. Historical weight hash unavailable.'};
 save(planFile,plan);writeFileSync(planFile+'.sha256',sha(readFileSync(planFile))+'\n',{flag:'wx'});console.log(JSON.stringify({sessions:1,assessments:8,target_U02:3}));process.exit(0);
}
const plan=read(planFile);
function checkFreeze(){
 if(sha(readFileSync(planFile))!==readFileSync(planFile+'.sha256','utf8').trim()||sha(readFileSync(import.meta.filename))!==plan.script_sha256||JSON.stringify(sourceHashes(join(root,'lat-ai')))!==JSON.stringify(plan.source_sha256))throw Error('Frozen diagnostic changed');
}
checkFreeze();const dir=join(out,'order-live');mkdirSync(dir);
const reference=read(join(out,'current-reconstructed-requests.json')).map(r=>r.body);
const targetRows=[];let fatal=null;
for(const session of plan.sessions){
 checkFreeze();const folder=join(dir,session.id);mkdirSync(folder);let model=null,requestIndex=0,currentId=null,calls=[],retired=false,error=null;
 const events=[];const event=e=>{events.push({at:new Date().toISOString(),...e});writeFileSync(join(folder,'events.jsonl'),events.map(v=>JSON.stringify(v)).join('\n')+'\n');console.log(JSON.stringify({session:session.id,...e}));};
 const measuredFetch=async(url,options)=>{
  if(options?.method!=='POST'||!String(url).endsWith('/v1/chat/completions'))return fetch(url,options);
  const body=JSON.parse(options.body),normalized={...body,model:'u02-capture-only'};
  const stage=requestIndex++===0?'proposal':'verification';
  if(currentId==='U02'&&JSON.stringify(normalized)!==JSON.stringify(reference[stage==='proposal'?0:1]))throw Error('U02 payload differs from reconstructed reference');
  const started=performance.now(),record={stage,request_body:body,normalized_sha256:sha(JSON.stringify(normalized))};calls.push(record);
  let response;
  try{response=await fetch(url,options);}catch(e){record.ms=performance.now()-started;record.transport_error=e.message;throw e;}
  record.http_status=response.status;
  if(!response.ok){record.ms=performance.now()-started;return response;}
  return {ok:response.ok,text:async()=>{try{const text=await response.text();record.response_body=JSON.parse(text);return text;}finally{record.ms=performance.now()-started;}}};
 };
 try{
  model=await LocalModel.loadOwned({modelKey:plan.config.model_key,contextLength:8192,fetchImpl:measuredFetch,lockPath:join(folder,'model.lock'),recoveryLog:e=>event({event:'recovery',detail:e})});
  event({event:'loaded',instance:model.model});
  const metadata=await fetch('http://127.0.0.1:1234/api/v1/models');if(!metadata.ok)throw Error('Model metadata unavailable');
  const all=await metadata.json();save(join(folder,'loaded-model.json'),{models:all.models.filter(m=>m.loaded_instances?.some(i=>i.id===model.model))});
  for(const [stepIndex,id] of session.order.entries()){
   checkFreeze();currentId=id;requestIndex=0;calls=[];const c=plan.answer_cases[id],started=performance.now();let raw,result=null,validationError=null;
   try{raw=await model.generate({role:'assess',lesson:c.task_key.slice(0,2),message:c.answer,assessment:{task_key:c.task_key}},{signal:AbortSignal.timeout(60000),maxTokens:192});}
   catch(e){save(join(folder,String(stepIndex+1)+'-'+id+'-transport-error.json'),{id,error:e.message,calls});throw e;}
   try{result=validateAssessment(raw,c.answer);}catch(e){validationError=e.message;}
   const row={session:session.id,id,answer_sha256:sha(c.answer),expected:c.expected,actual:result?.checks??null,candidate_checks:validateCandidate(raw.candidate,c.answer).checks,verification_checks:verifyAssessment(raw.verification,c.answer).checks,validation_error:validationError,raw,result,ms:performance.now()-started,calls};
   save(join(folder,String(stepIndex+1)+'-'+id+'.json'),row);event({event:'case',id,actual:row.actual,candidate:row.candidate_checks,verification:row.verification_checks,ms:row.ms});
   if(id==='U02')targetRows.push({session:session.id,step:stepIndex+1,condition:stepIndex===4?'B':'A',actual:row.actual,candidate:row.candidate_checks,verification:row.verification_checks,normalized_request_sha256:calls.map(c=>c.normalized_sha256)});
  }
 }catch(e){error=e.message;event({event:'error',error});}
 finally{
  if(model){try{if(model.state.phase==='idle'){model.coordinator.begin();model.quarantineActive();}retired=await model.retireOwnedInstance();event({event:'retired',proven:retired,instance:model.model});}catch(e){error??=e.message;}}
  save(join(folder,'summary.json'),{session:session.id,error,retirement_proven:retired,automatic_retries:0});
 }
 if(error||!retired){fatal=error??'Retirement not proven';break;}
}
save(join(dir,'summary.json'),{complete:fatal===null,error:fatal,targets:targetRows,protocol_sha256:sha(readFileSync(planFile)),automatic_retries:0});if(fatal)process.exitCode=2;
