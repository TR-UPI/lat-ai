import {readFileSync,writeFileSync,mkdirSync,createReadStream,statSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {LMStudioClient} from '../work/u02-runtime-sdk/node_modules/@lmstudio/sdk/dist/index.mjs';
import {LocalModel} from '../lat-ai/integration/ai/core/src/local-model.mjs';
import {validateAssessment,validateCandidate} from '../lat-ai/integration/ai/core/src/assessment.mjs';
import {validateAssessment as verifyAssessment} from '../lat-ai/integration/ai/core/src/assessment-verifier.mjs';
import {sourceHashes} from './frozen-assessment-run.mjs';
const root=resolve(import.meta.dirname,'..'),out=join(root,'outputs/u02-runtime-controls-2026-11-11');
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const sha=b=>createHash('sha256').update(b).digest('hex');
const save=(p,v)=>writeFileSync(p,JSON.stringify(v,null,2)+'\n',{flag:'wx'});
const planFile=join(out,'checkpoint-protocol.json');
const sdkPaths=['work/u02-runtime-sdk/package-lock.json','work/u02-runtime-sdk/node_modules/@lmstudio/sdk/dist/index.mjs','tools/frozen-assessment-run.mjs'];
const dependencies=()=>Object.fromEntries(sdkPaths.map(p=>[p,sha(readFileSync(join(root,p)))]));
if(process.argv[2]==='freeze'){
 const previous=read(join(root,'outputs/u02-investigation-2026-11-11/order-protocol.json'));
 const config=read(join(out,'checkpoint-probe/sdk-load-config.json'));
 const sessions=[['D-A1',32,'A'],['D-B1',32,'B'],['Z-A1',0,'A'],['Z-B1',0,'B'],['Z-B2',0,'B'],['Z-A2',0,'A'],['D-B2',32,'B'],['D-A2',32,'A']].map(([id,checkpoints,history])=>({id,checkpoints,history,order:history==='A'?['N05','U15','U02']:['V11','U02']}));
 const plan={created_utc:new Date().toISOString(),purpose:'Bounded known U02 runtime diagnostic; NOT holdout or population inference',source_sha256:sourceHashes(join(root,'lat-ai')),script_sha256:sha(readFileSync(import.meta.filename)),dependency_sha256:dependencies(),node:process.version,answer_cases:previous.answer_cases,model_fingerprint:previous.model_fingerprint,sdk_expected_config:config,rest_expected_config:read(join(out,'checkpoint-probe/loaded-metadata.json')).loaded_instances[0].config,sessions,config:{context_length:8192,parallel:1,budget_ms:60000,max_tokens:192},interpretation:'Both arms SDK 2.1.0; only contextCheckpoints differs. Require visible REST and SDK config equality otherwise. D baseline must reproduce A refusal/B undergrade before interpreting checkpoint effect. Two fresh loads per cell, one U02 each. A disappearance is evidence for a configuration effect, not proof of internal cache mechanism or general fix. Stop after 8 loads, on unknown transport or unproven retirement; no retries, no production promotion.'};
 save(planFile,plan);writeFileSync(planFile+'.sha256',sha(readFileSync(planFile))+'\n',{flag:'wx'});console.log('Frozen: 8 loads, 20 assessments, 40 POST.');process.exit(0);
}
const plan=read(planFile);
function checkFreeze(){assert.equal(sha(readFileSync(planFile)),readFileSync(planFile+'.sha256','utf8').trim());assert.equal(sha(readFileSync(import.meta.filename)),plan.script_sha256);assert.deepEqual(sourceHashes(join(root,'lat-ai')),plan.source_sha256);assert.deepEqual(dependencies(),plan.dependency_sha256);assert.equal(process.version,plan.node);}
async function fingerprint(){const p=plan.model_fingerprint.path,h=createHash('sha256');for await(const b of createReadStream(p))h.update(b);const value={path:p,sha256:h.digest('hex'),bytes:statSync(p).size,measured_utc:new Date().toISOString()};assert.equal(value.sha256,plan.model_fingerprint.sha256.toLowerCase());return value;}
checkFreeze();const dir=join(out,'checkpoint-live');mkdirSync(dir);save(join(dir,'weights-before.json'),await fingerprint());
const client=new LMStudioClient({baseUrl:'ws://127.0.0.1:1234'});
const reference=read(join(root,'outputs/u02-investigation-2026-11-11/current-reconstructed-requests.json')).map(r=>r.body);
const targets=[];let fatal=null;
try{for(const session of plan.sessions){
 checkFreeze();const folder=join(dir,session.id);mkdirSync(folder);let model,handle,currentId,calls=[],retired=false,error=null,position=0;const events=[],history=[];
 const event=e=>{events.push({at:new Date().toISOString(),...e});writeFileSync(join(folder,'events.jsonl'),events.map(v=>JSON.stringify(v)).join('\n')+'\n');console.log(JSON.stringify({session:session.id,...e}));};
 const measuredFetch=async(url,options)=>{
  if(options?.method!=='POST'||!String(url).endsWith('/v1/chat/completions'))return fetch(url,options);
  const body=JSON.parse(options.body),normalized={...body,model:'u02-capture-only'},stage=calls.length===0?'proposal':'verification';
  if(currentId==='U02')assert.deepEqual(normalized,reference[stage==='proposal'?0:1]);
  const record={stage,request_body:body,normalized_sha256:sha(JSON.stringify(normalized)),predecessor_calls:[...history]},started=performance.now();calls.push(record);
  save(join(folder,`${position}-${currentId}-${stage}-dispatch.json`),{at:new Date().toISOString(),...record});
  try{const response=await fetch(url,options);record.http_status=response.status;const text=await response.text();record.response_text=text;try{record.response_body=JSON.parse(text);}catch{}record.ms=performance.now()-started;history.push({case_id:currentId,stage,request_sha256:record.normalized_sha256,response_sha256:sha(text)});return {ok:response.ok,status:response.status,text:async()=>text};}
  catch(e){record.ms=performance.now()-started;record.transport_error=e.message;throw e;}
 };
 try{
  model=await LocalModel.loadOwned({modelKey:'qwen3.5-9b',contextLength:8192,fetchImpl:measuredFetch,lockPath:join(folder,'model.lock'),recoveryLog:e=>event({event:'recovery',detail:e}),loadImpl:async({modelKey,id,contextLength})=>{handle=await client.llm.load(modelKey,{identifier:id,config:{contextLength,maxParallelPredictions:1,contextCheckpoints:session.checkpoints},verbose:false,signal:AbortSignal.timeout(120000)});}});
  const response=await fetch('http://127.0.0.1:1234/api/v1/models');assert.ok(response.ok);const all=await response.json(),metadata=all.models.find(m=>m.loaded_instances?.some(i=>i.id===model.model));assert.ok(metadata);
  const config=metadata.loaded_instances.find(i=>i.id===model.model).config,sdkConfig=await handle.getLoadConfig();save(join(folder,'loaded-model.json'),metadata);save(join(folder,'sdk-load-config.json'),sdkConfig);
  assert.deepEqual({...config,context_checkpoints:0},plan.rest_expected_config);assert.equal(config.context_checkpoints,session.checkpoints);assert.deepEqual({...sdkConfig,contextCheckpoints:0},plan.sdk_expected_config);assert.equal(sdkConfig.contextCheckpoints,session.checkpoints);
  event({event:'loaded',instance:model.model,checkpoints:session.checkpoints,history:session.history,fresh:true});
  for(const id of session.order){
   checkFreeze();currentId=id;calls=[];position++;const c=plan.answer_cases[id],started=performance.now();let raw,result=null,validationError=null;
   try{raw=await model.generate({role:'assess',lesson:c.task_key.slice(0,2),message:c.answer,assessment:{task_key:c.task_key}},{signal:AbortSignal.timeout(60000),maxTokens:192});}catch(e){save(join(folder,`${position}-${id}-transport-error.json`),{id,error:e.message,calls});throw e;}
   try{result=validateAssessment(raw,c.answer);}catch(e){validationError=e.message;}
   const row={session:session.id,checkpoints:session.checkpoints,history:session.history,position,id,instance:model.model,fresh_before_case:position===1,answer_sha256:sha(c.answer),expected:c.expected,actual:result?.checks??null,candidate_checks:validateCandidate(raw.candidate,c.answer).checks,verification_checks:verifyAssessment(raw.verification,c.answer).checks,validation_error:validationError,raw,result,ms:performance.now()-started,calls};
   save(join(folder,`${position}-${id}.json`),row);event({event:'case',id,actual:row.actual,ms:row.ms});if(id==='U02')targets.push({session:session.id,checkpoints:session.checkpoints,history:session.history,actual:row.actual,candidate:row.candidate_checks,verification:row.verification_checks});
  }
 }catch(e){error=e.message;event({event:'error',error,provisioning_instance:e.instanceId??null});}
 finally{if(model){try{if(model.state.phase==='idle'){model.coordinator.begin();model.quarantineActive();}retired=await model.retireOwnedInstance();event({event:'retired',proven:retired,instance:model.model});}catch(e){error??=e.message;}}save(join(folder,'summary.json'),{session:session.id,error,retirement_proven:retired,automatic_retries:0});}
 if(error||!retired){fatal=error??'Retirement not proven';break;}
}}finally{await client[Symbol.asyncDispose]();save(join(dir,'weights-after.json'),await fingerprint());save(join(dir,'summary.json'),{complete:fatal===null,error:fatal,targets,protocol_sha256:sha(readFileSync(planFile)),automatic_retries:0});}
if(fatal)process.exitCode=2;
