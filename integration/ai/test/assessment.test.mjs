import test from 'node:test';
import assert from 'node:assert/strict';
import {Tutor} from '../core/src/tutor.mjs';
const req={role:'assess',lesson:'L1',message:'Оба значения строки, плюс склеивает их, печатается 32.'};
const context={assessment:{task_key:'L1.types.1'}};
const part=answer=>({answer:JSON.stringify(answer),finish_reason:'stop',stats:{total_output_tokens:40,reasoning_output_tokens:0}});
const raw=checks=>({candidate:part(Object.fromEntries(checks.map((x,i)=>['criterion_'+(i+1),x===true?{counter:null,start:'S1',end:'S1'}:x===false?{counter:null,start:null,end:null}:x]))),verification:part(Object.fromEntries(checks.map((x,i)=>['criterion_'+(i+1),x===true?0:x===false?-1:x])))});
const make=generate=>new Tutor({generate,experimental:true,modelEnabled:true,modelReady:true});
test('assessment is model-only with trusted rubric and boolean checks',async()=>{
 const tutor=make(async r=>{assert.equal(r.assessment.task_key,'L1.types.1');return raw([true,false,true]);});
 const r=await tutor.respond(req,context);assert.equal(r.path,'model');assert.deepEqual(r.result.checks,[true,false,true]);
 assert.notEqual((await tutor.respond(req)).path,'model');
});
test('disabled or malformed assessment never becomes a score',async()=>{
 const disabled=await new Tutor().respond(req,context);assert.notEqual(disabled.path,'model');assert.equal(disabled.result?.checks,undefined);
 for(const checks of [[true,true],['true',true,true],[99,99,99],[true,true,true,true]]){
  const r=await make(async()=>raw(checks)).respond(req,context);assert.equal(r.reason,'invalid_output');assert.equal(r.result?.checks,undefined);
 }
});
test('assessment and explanation share a queue, overflow has no grade',async()=>{
 let release;const barrier=new Promise(r=>release=r);let calls=0;
 const tutor=make(async()=>{calls++;await barrier;return raw([true,true,true]);});
 const first=tutor.respond(req,context);await new Promise(r=>setImmediate(r));
 const second=tutor.respond({...req,role:'explain'});await new Promise(r=>setImmediate(r));
 const third=await tutor.respond(req,context);assert.equal(third.reason,'queue_full');assert.equal(third.result?.checks,undefined);
 release();await Promise.all([first,second]);assert.equal(calls,2);
});
test('truncated, duplicate or reasoning output is rejected',async()=>{
 for(const delta of [{finish_reason:'length'},{answer:'{"checks":[true,true,true],"checks":[true,true,true]}'},{stats:{total_output_tokens:192,reasoning_output_tokens:0}},{stats:{total_output_tokens:20,reasoning_output_tokens:2}}]){
  assert.equal((await make(async()=>{const r=raw([true,true,true]);r.candidate={...r.candidate,...delta};return r;}).respond(req,context)).reason,'invalid_output');
 }
});
