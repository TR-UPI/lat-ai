import {readFileSync,writeFileSync,mkdirSync,existsSync} from 'node:fs';
import {join,resolve} from 'node:path';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {LMStudioClient} from '../work/u02-runtime-sdk/node_modules/@lmstudio/sdk/dist/index.mjs';
import {loadWithDeadline} from './sdk-load-with-deadline.mjs';
import {LocalModel} from '../lat-ai/integration/ai/core/src/local-model.mjs';
import {validateAssessment} from '../lat-ai/integration/ai/core/src/assessment.mjs';
import {sourceHashes} from './frozen-assessment-run.mjs';
const root=resolve(import.meta.dirname,'..'),out=join(root,'outputs/sdk-fix-and-history-scan-2026-11-11');
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const hash=b=>createHash('sha256').update(b).digest('hex');
const save=(p,v)=>writeFileSync(p,JSON.stringify(v,null,2)+'\n',{flag:'wx'});
const files=['tools/verify-sdk-deadline-live.mjs','tools/sdk-load-with-deadline.mjs','work/u02-runtime-sdk/node_modules/@lmstudio/sdk/dist/index.mjs','work/u02-runtime-sdk/package-lock.json'];
const hashes=()=>Object.fromEntries(files.map(p=>[p,hash(readFileSync(join(root,p)))]));
const planPath=join(out,'sdk-live-protocol.json');
if(process.argv[2]==='freeze'){
 mkdirSync(out);
 const previous=read(join(root,'outputs/u02-runtime-controls-2026-11-11/checkpoint-protocol.json'));
 save(planPath,{utc:new Date().toISOString(),purpose:'Verify cancellable SDK load deadline on live local model, including post-dispose survival past both original deadlines; no quality claim.',source_sha256:sourceHashes(join(root,'lat-ai')),tool_sha256:hashes(),case:previous.answer_cases.V11,load_deadline_ms:120000,post_deadline_margin_ms:3000,sessions:[{id:'S1',checkpoints:32},{id:'S2',checkpoints:0}],expected_sdk_config:previous.sdk_expected_config,expected_rest_config:previous.rest_expected_config,assertions:['Two actual loads with helper, one assessment each, terminal responses, own unload proof and lock release.','Dispose shared SDK client after both loads. Keep process alive past latest load-start +120000+3000ms.','No retry, no source/prompt change, preserve all failures. Old frozen scripts/artifacts immutable.']});
 writeFileSync(planPath+'.sha256',hash(readFileSync(planPath))+'\n',{flag:'wx'});console.log('Frozen live SDK verification: two loads, two assessments, post-dispose deadline observation.');process.exit(0);
}
const plan=read(planPath);
function check(){assert.equal(hash(readFileSync(planPath)),readFileSync(planPath+'.sha256','utf8').trim());assert.deepEqual(hashes(),plan.tool_sha256);assert.deepEqual(sourceHashes(join(root,'lat-ai')),plan.source_sha256);}
check();const dir=join(out,'sdk-live');mkdirSync(dir);const client=new LMStudioClient({baseUrl:'ws://127.0.0.1:1234'});
const results=[],events=[];let failure=null,lastStarted=0,disposed=false;
const event=e=>{events.push({utc:new Date().toISOString(),...e});writeFileSync(join(dir,'events.jsonl'),events.map(x=>JSON.stringify(x)).join('\n')+'\n');console.log(JSON.stringify(e));};
try{
 for(const s of plan.sessions){
  check();const folder=join(dir,s.id);mkdirSync(folder);let model,handle,retired=false,released=false,error=null,calls=[];
  try{
   const measuredFetch=async(url,opts)=>{
    if(opts?.method!=='POST'||!String(url).endsWith('/v1/chat/completions'))return fetch(url,opts);
    const row={request:JSON.parse(opts.body)},started=performance.now();calls.push(row);
    save(join(folder,'dispatch-'+calls.length+'.json'),{utc:new Date().toISOString(),...row});
    try{const response=await fetch(url,opts),text=await response.text();row.status=response.status;row.body=text;row.ms=performance.now()-started;return {ok:response.ok,status:response.status,text:async()=>text};}
    catch(e){row.error=e.message;row.ms=performance.now()-started;throw e;}
   };
   model=await LocalModel.loadOwned({modelKey:'qwen3.5-9b',contextLength:8192,fetchImpl:measuredFetch,lockPath:join(folder,'model.lock'),recoveryLog:e=>event({session:s.id,recovery:e}),loadImpl:async({modelKey,id,contextLength})=>{
    lastStarted=Date.now();event({session:s.id,event:'load_started',instance:id,deadline_utc:new Date(lastStarted+plan.load_deadline_ms).toISOString()});
    handle=await loadWithDeadline(client,modelKey,{identifier:id,config:{contextLength,maxParallelPredictions:1,contextCheckpoints:s.checkpoints},verbose:false},plan.load_deadline_ms);
   }});
   const metadata=await (await fetch('http://127.0.0.1:1234/api/v1/models')).json();
   const instance=metadata.models.flatMap(m=>m.loaded_instances).find(i=>i.id===model.model);assert.ok(instance);
   const sdk=await handle.getLoadConfig();save(join(folder,'loaded-metadata.json'),metadata);save(join(folder,'sdk-load-config.json'),sdk);
   assert.deepEqual(instance.config,{...plan.expected_rest_config,context_checkpoints:s.checkpoints});assert.deepEqual(sdk,{...plan.expected_sdk_config,contextCheckpoints:s.checkpoints});
   const c=plan.case,raw=await model.generate({role:'assess',lesson:c.task_key.slice(0,2),message:c.answer,assessment:{task_key:c.task_key}},{signal:AbortSignal.timeout(60000),maxTokens:192});
   let result=null,validationError=null;try{result=validateAssessment(raw,c.answer);}catch(e){validationError=e.message;}
   save(join(folder,'assessment.json'),{id:c.id,raw,result,validationError,calls});assert.equal(calls.length,2);for(const call of calls){assert.equal(call.status,200);assert.equal(JSON.parse(call.body).choices[0].finish_reason,'stop');}
   event({session:s.id,event:'assessment_terminal',actual:result?.checks??null});
  }catch(e){error=e.message;save(join(folder,'failure.json'),{error,calls,provisioning_instance:e.instanceId??null});}
  finally{
   if(model){try{if(model.state.phase==='idle'){model.coordinator.begin();model.quarantineActive();}retired=await model.retireOwnedInstance();
    const until=Date.now()+3000;while(retired&&model.state.phase==='proof_wait'&&Date.now()<until){await new Promise(r=>setTimeout(r,100));model.coordinator.recover();}
    released=retired&&model.state.phase==='idle'&&!existsSync(join(folder,'model.lock'));
   }catch(e){error??=e.message;}}
   const row={session:s.id,instance:model?.model??null,error,retirement_proven:retired,lock_released:released,calls:calls.length};save(join(folder,'summary.json'),row);results.push(row);event({event:'session_complete',...row});
  }
  if(error||!retired||!released){failure=error??'Retirement/lock release not proven';break;}
 }
}catch(e){failure=e.message;event({event:'failure',error:failure});}
finally{try{await client[Symbol.asyncDispose]();disposed=true;event({event:'sdk_disposed'});}catch(e){failure??=e.message;}}
// Intentionally retain a real timer after dispose to expose the previous late-abort failure.
if(!failure){const until=lastStarted+plan.load_deadline_ms+plan.post_deadline_margin_ms;while(Date.now()<until){await new Promise(r=>setTimeout(r,Math.min(10000,until-Date.now())));event({event:'post_dispose_alive',remaining_ms:Math.max(0,until-Date.now())});}}
check();const response=await fetch('http://127.0.0.1:1234/api/v1/models',{signal:AbortSignal.timeout(3000)});assert.ok(response.ok);const metadata=await response.json();save(join(dir,'models-after.json'),metadata);
const ids=metadata.models.flatMap(m=>m.loaded_instances.map(i=>i.id)),allAbsent=results.every(r=>r.instance&&!ids.includes(r.instance));
const summary={complete:!failure&&disposed&&allAbsent&&results.length===2,failure,disposed,post_dispose_survived_beyond_deadline:!failure&&Date.now()>=lastStarted+plan.load_deadline_ms+plan.post_deadline_margin_ms,all_owned_instances_absent:allAbsent,sessions:results,automatic_retries:0,protocol_sha256:hash(readFileSync(planPath))};save(join(dir,'summary.json'),summary);event({event:'complete',...summary});if(!summary.complete)process.exitCode=2;
