import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {LocalModel} from '../core/src/local-model.mjs';

for(const protocol of ['structured','native'])test(`assessment sampling is isolated from explanation (${protocol})`,async()=>{
 const dir=mkdtempSync(join(tmpdir(),'lat-assessment-'));
 const lockPath=join(dir,'model.lock'),payloads=[];
 const model=new LocalModel({model:'test-instance',protocol,lockPath,fetchImpl:async(url,options)=>{
  if(url.endsWith('/api/v1/models'))return {ok:true,json:async()=>({models:[{loaded_instances:[{id:'test-instance'}]}]})};
  payloads.push(JSON.parse(options.body));
  const response=protocol==='structured'
   ? {choices:[{finish_reason:'stop',message:{content:'{}'}}],usage:{completion_tokens:2,prompt_tokens:10,completion_tokens_details:{reasoning_tokens:0}}}
   : {output:[{type:'message',content:'{}'}],stats:{total_output_tokens:2,reasoning_output_tokens:0}};
  return {ok:true,text:async()=>JSON.stringify(response)};
 }});
 try{
  for(const role of ['assess','explain'])await model.generate({role,lesson:'L1',message:'Объяснение ученика',...(role==='assess'?{assessment:{task_key:'L1.condition.1'}}:{})},{signal:AbortSignal.timeout(2000),maxTokens:192});
  assert.deepEqual(payloads.map(p=>p.temperature),[0,.2]);
  assert.ok(!existsSync(lockPath),'terminal responses release the shared reservation');
  if(protocol==='structured'){
   assert.equal(payloads[0].reasoning_effort,'none');
   assert.equal(payloads[0].max_tokens,192);
   assert.deepEqual(payloads[0].response_format.json_schema.schema.required,['criterion_1','criterion_2','criterion_3']);
   assert.deepEqual(payloads[1].response_format.json_schema.schema.required,['text','source_ids']);
  }
 }finally{rmSync(dir,{recursive:true,force:true});}
});
