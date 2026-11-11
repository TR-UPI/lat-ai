import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import assert from 'node:assert/strict';
import {LMStudioClient} from '../work/u02-runtime-sdk/node_modules/@lmstudio/sdk/dist/index.mjs';
import {LocalModel} from '../lat-ai/integration/ai/core/src/local-model.mjs';
const root=resolve(import.meta.dirname,'..'),out=join(root,'outputs/u02-runtime-controls-2026-11-11/checkpoint-probe');mkdirSync(out);
const client=new LMStudioClient({baseUrl:'ws://127.0.0.1:1234'});let model,handle,retired=false;
const save=(name,value)=>writeFileSync(join(out,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
try{
 model=await LocalModel.loadOwned({modelKey:'qwen3.5-9b',contextLength:8192,lockPath:join(out,'model.lock'),loadImpl:async({modelKey,id,contextLength})=>{
  handle=await client.llm.load(modelKey,{identifier:id,config:{contextLength,maxParallelPredictions:1,contextCheckpoints:0},verbose:false,signal:AbortSignal.timeout(120000)});
 }});
 const response=await fetch('http://127.0.0.1:1234/api/v1/models');assert.ok(response.ok);
 const metadata=(await response.json()).models.find(m=>m.loaded_instances?.some(i=>i.id===model.model));assert.ok(metadata);
 const instance=metadata.loaded_instances.find(i=>i.id===model.model);save('loaded-metadata.json',metadata);save('sdk-load-config.json',await handle.getLoadConfig());
 assert.equal(instance.config.context_checkpoints,0);assert.equal(instance.config.context_length,8192);assert.equal(instance.config.parallel,1);
 const previous=JSON.parse(readFileSync(join(root,'outputs/u02-investigation-2026-11-11/order-live/C1/loaded-model.json'),'utf8')).models[0].loaded_instances[0].config;
 assert.deepEqual({...instance.config,context_checkpoints:32},previous,'Other visible settings changed');
 save('result.json',{checkpoints_zero_applied:true,other_visible_load_settings_equal:true,inference_requests:0,instance:model.model});console.log('Checkpoint0 applied; all other visible load settings match previous CLI. No inference sent.');
}finally{
 if(model){if(model.state.phase==='idle'){model.coordinator.begin();model.quarantineActive();}retired=await model.retireOwnedInstance();save('retirement.json',{proven:retired,instance:model.model});}
 await client[Symbol.asyncDispose]();if(!retired)process.exitCode=2;
}
