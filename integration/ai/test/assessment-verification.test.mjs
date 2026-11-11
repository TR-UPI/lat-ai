import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,rmSync,existsSync} from 'node:fs';
import {join} from 'node:path';
import {tmpdir} from 'node:os';
import {LocalModel} from '../core/src/local-model.mjs';
import {validateAssessment} from '../core/src/assessment.mjs';
import {assessmentInput as verifierInput} from '../core/src/assessment-verifier.mjs';
const req={role:'assess',lesson:'L1',message:'Строки соединяются. Итог 32.',assessment:{task_key:'L1.types.1'}};
const proposed={criterion_1:{start:'S1',end:'S1',counter:null},criterion_2:{start:'S1',end:'S1',counter:null},criterion_3:{start:'S2',end:'S2',counter:null}};
const verified={criterion_1:0,criterion_2:0,criterion_3:1};
const raw=answer=>({answer:JSON.stringify(answer),finish_reason:'stop',stats:{input_tokens:10,total_output_tokens:30,reasoning_output_tokens:0}});
const fixture=behavior=>{
 const dir=mkdtempSync(join(tmpdir(),'lat-verified-')),lockPath=join(dir,'model.lock'),posts=[];
 const model=new LocalModel({model:'test',lockPath,fetchImpl:async(url,options)=>{
  if(url.endsWith('/api/v1/models'))return {ok:true,json:async()=>({models:[{loaded_instances:[{id:'test'}]}]})};
  posts.push(JSON.parse(options.body));
  const response=await behavior(posts.length,options);
  return {ok:true,text:async()=>JSON.stringify({choices:[{finish_reason:response.finish_reason,message:{content:response.answer}}],usage:{prompt_tokens:response.stats.input_tokens,completion_tokens:response.stats.total_output_tokens,completion_tokens_details:{reasoning_tokens:response.stats.reasoning_output_tokens}}})};
 }});
 return {model,posts,lockPath,close:()=>rmSync(dir,{recursive:true,force:true})};
};
test('verification sees the original answer, not the proposed result; accounting includes both calls',async()=>{
 const f=fixture(async n=>raw(n===1?proposed:verified));
 try{
  const result=await f.model.generate(req,{signal:AbortSignal.timeout(3000),maxTokens:192});
  assert.deepEqual(validateAssessment(result,req.message).checks,[true,true,true]);
  assert.equal(f.posts.length,2);assert.deepEqual(JSON.parse(f.posts[1].messages[1].content),verifierInput(req));
  assert.notEqual(f.posts[0].messages[0].content,f.posts[1].messages[0].content);
  assert.equal(result.stats.total_output_tokens,60);assert.equal(result.stats.input_tokens,20);
  assert.ok(!existsSync(f.lockPath));
 }finally{f.close();}
});
test('same total score with different criterion decisions is still a disagreement',()=>{
 const candidate={...proposed,criterion_3:{start:null,end:null,counter:null}};
 assert.throws(()=>validateAssessment({candidate:raw(candidate),verification:raw({criterion_1:0,criterion_2:-1,criterion_3:1})},req.message),/disagreement/);
});
test('missing, truncated or reasoning verification never releases a candidate grade',()=>{
 for(const verification of [null,{...raw(verified),finish_reason:'length'},{...raw(verified),stats:{total_output_tokens:30,reasoning_output_tokens:1}}])assert.throws(()=>validateAssessment({candidate:raw(proposed),verification},req.message));
});
test('malformed proposal stops without another inference or a grade',async()=>{
 const f=fixture(async()=>raw({...proposed,criterion_1:{start:'S99',end:'S99',counter:null}}));
 try{const result=await f.model.generate(req,{signal:AbortSignal.timeout(3000)});assert.equal(f.posts.length,1);assert.throws(()=>validateAssessment(result,req.message));assert.ok(!existsSync(f.lockPath));}finally{f.close();}
});
test('abort after first terminal response prevents verification dispatch',async()=>{
 const controller=new AbortController();const f=fixture(async()=>{controller.abort();return raw(proposed);});
 try{await assert.rejects(f.model.generate(req,{signal:controller.signal}));assert.equal(f.posts.length,1);assert.ok(!existsSync(f.lockPath));assert.equal(f.model.state.quarantined,false);}finally{f.close();}
});
test('unknown verification transport retains quarantine and never retries',async()=>{
 const f=fixture(async n=>{if(n===2)throw Error('connection lost after dispatch');return raw(proposed);});
 try{await assert.rejects(f.model.generate(req,{signal:AbortSignal.timeout(3000)}));assert.equal(f.posts.length,2);assert.equal(f.model.state.quarantined,true);assert.ok(existsSync(f.lockPath));}finally{f.close();}
});
