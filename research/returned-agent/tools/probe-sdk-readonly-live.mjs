// Live SDK connection/disposal observation ONLY. Contains no model load/unload/inference calls.
import {readFileSync,writeFileSync,mkdirSync,appendFileSync} from 'node:fs';
import {resolve,join} from 'node:path';import {createHash} from 'node:crypto';import assert from 'node:assert/strict';
import {LMStudioClient} from '../work/u02-runtime-sdk/node_modules/@lmstudio/sdk/dist/index.mjs';
import {refuseUnverifiedExperiment} from './sdk-isolation-policy.mjs';
const ROOT=resolve(import.meta.dirname,'..'),OUT=join(ROOT,'outputs/sdk-isolation-live-2026-11-11');
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const save=(p,v)=>writeFileSync(p,JSON.stringify(v,null,2)+'\n',{flag:'wx'});
const files=['tools/probe-sdk-readonly-live.mjs','tools/sdk-isolation-policy.mjs','tools/test-sdk-isolation-policy.mjs','tools/inspect-sdk-isolation.ps1','tools/sdk-load-with-deadline-v2.mjs','work/u02-runtime-sdk/node_modules/@lmstudio/sdk/dist/index.mjs','work/u02-runtime-sdk/package-lock.json'];
const protocol=join(OUT,'readonly-protocol.json');
if(process.argv[2]==='freeze'){
 save(protocol,{utc:new Date().toISOString(),scope:'READ_ONLY_LIVE_SDK_CONNECTION_NOT_LOAD_TEST',endpoint:'ws://127.0.0.1:1234',hold_after_dispose_ms:5000,files_sha256:Object.fromEntries(files.map(n=>[n,sha(join(ROOT,n))])),assertions:['Explicit endpoint, getInfo, downloaded and loaded metadata only.','No load/unload/inference; no helper load call; no forced abort.','Dispose client and observe 5s, which does NOT reproduce load-deadline lifecycle.','Compare shared loaded IDs/configs at observations, not continuous noninterference proof.']});
 writeFileSync(protocol+'.sha256',sha(protocol)+'\n',{flag:'wx'});console.log('Read-only SDK protocol frozen');process.exit(0);
}
assert.equal(process.argv[2],'run');const p=read(protocol);assert.equal(sha(protocol),readFileSync(protocol+'.sha256','utf8').trim());
for(const [n,h]of Object.entries(p.files_sha256))assert.equal(sha(join(ROOT,n)),h,n);
const dir=join(OUT,'readonly-live');mkdirSync(dir);
const event=v=>{const row={utc:new Date().toISOString(),...v};appendFileSync(join(dir,'events.jsonl'),JSON.stringify(row)+'\n');console.log(JSON.stringify(row));};
const get=async name=>{const response=await fetch('http://127.0.0.1:1234/api/v1/models',{redirect:'error',signal:AbortSignal.timeout(5000)});const body=await response.text();writeFileSync(join(dir,name+'.json'),body,{flag:'wx'});assert.ok(response.ok);return JSON.parse(body);};
const loaded=value=>value.models.flatMap(m=>m.loaded_instances.map(i=>({key:m.key,...i}))).sort((a,b)=>a.id.localeCompare(b.id));
let client,disposed=false,failure=null,before,after,service;
try{
 before=await get('shared-before');event({event:'rest_before'});
 client=new LMStudioClient({baseUrl:p.endpoint});
 service=await client.system.getInfo();save(join(dir,'sdk-service.json'),service);event({event:'sdk_getInfo_complete'});
 const disk=await client.system.listDownloadedModels();save(join(dir,'sdk-downloaded-models.json'),disk);event({event:'sdk_disk_list_complete'});
 const handles=await client.llm.listLoaded();const infos=[];for(const h of handles)infos.push(await h.getModelInfo());save(join(dir,'sdk-loaded-models.json'),infos);event({event:'sdk_loaded_metadata_complete',count:infos.length});
}catch(e){failure={name:e.name,message:e.message};event({event:'failure',...failure});}
finally{if(client)try{await client[Symbol.asyncDispose]();disposed=true;event({event:'sdk_disposed'});}catch(e){failure??={name:e.name,message:e.message};}}
if(disposed){await new Promise(r=>setTimeout(r,p.hold_after_dispose_ms));event({event:'alive_after_dispose',observed_ms:p.hold_after_dispose_ms});}
try{after=await get('shared-after');}catch(e){failure??={name:e.name,message:e.message};}
const inv=read(join(OUT,'inventory-before.json'));
const gate=refuseUnverifiedExperiment({candidate_endpoint:null,shared_endpoint:p.endpoint,listener_identity_verified:false,process_created_by_this_run:false,separate_profile_verified:false,shared_state_writes_excluded:false,job_containment_verified:false,no_breakaway_children_verified:false,free_bytes:inv.free_physical_bytes,required_bytes:2740937888+1073741824,normal_load_control_completed:false});
save(join(dir,'isolation-gate.json'),gate);
const same=!!before&&!!after&&JSON.stringify(loaded(before))===JSON.stringify(loaded(after));
const result={scope:p.scope,read_only_sdk_completed:!failure&&disposed&&same,failure,disposed,shared_loaded_metadata_equal_at_two_observations:same,shared_runtime_pid:service?.pid??null,load_unload_inference_calls:0,helper_load_exercised:false,isolated_normal_load_status:'NOT_RUN',forced_abort_status:'NOT_RUN',isolation_gate:gate.status,protocol_sha256:sha(protocol),limitation:'Live SDK read calls and disposal only; no load/deadline/abort result and no claim of continuous runtime state.'};
save(join(dir,'summary.json'),result);event({event:'complete',...result});if(!result.read_only_sdk_completed)process.exitCode=2;
