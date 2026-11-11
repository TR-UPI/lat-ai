import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {randomUUID} from 'node:crypto';
import {createBridge} from '../bridge.mjs';
import {rubrics} from '../core/src/assessment.mjs';
const r={actor_id:1,attempt_id:1,digest:'a'.repeat(64),task_key:'L1.types.1'};
const body=()=>({request_id:randomUUID(),answer:'Строки соединяются. Вывод 32.'});
test('assessment replay, conflict and identity do not duplicate generation',async()=>{
 let calls=0;
 const bridge=createBridge({dbPath:':memory:',tutor:{respond:async()=>{calls++;return {path:'model',result:{checks:[true,true,true],rubric_version:'local-assessment-v1'}};}}});
 try{
  const b=body();const results=await Promise.all([bridge.assess(b,r),bridge.assess(b,r)]);
  assert.deepEqual(results[0],results[1]);assert.equal(calls,1);
  assert.equal((await bridge.assess({...b,answer:'Other'},r)).status,409);
  assert.equal((await bridge.assess(b,{...r,digest:'b'.repeat(64)})).status,409);
  assert.equal((await bridge.assess(b,{...r,task_key:'unknown'})).status,400);
  assert.equal((await bridge.assess(b,r)).status,200);assert.equal(calls,1);
 }finally{bridge.close();}
});
test('pending journal after restart refuses unknown retry',async()=>{
 const dir=fs.mkdtempSync(new URL('./assessment-journal-',import.meta.url));
 // Use a portable path rather than URL decoding on Windows.
 const filename=dir+'/journal.sqlite3';let release;
 const b=body();const bridge=createBridge({dbPath:filename,tutor:{respond:()=>new Promise(r=>release=r)}});
 const flight=bridge.assess(b,r);await new Promise(r=>setImmediate(r));bridge.close();release({path:'error',reason:'transport'});await flight;
 let calls=0;const reopened=createBridge({dbPath:filename,tutor:{respond:()=>{calls++;throw Error('must not run');}}});
 try{const result=await reopened.assess(b,r);assert.equal(result.body.reason,'pending_unknown');assert.equal(calls,0);}finally{reopened.close();fs.rmSync(dir,{recursive:true});}
});

test('assessment revision conflict preserves receipt without another generation',async()=>{
 let calls=0;const original=rubrics.assessment_revision;
 const bridge=createBridge({dbPath:':memory:',tutor:{respond:async()=>{calls++;return {path:'model',result:{checks:[true,false,true],rubric_version:rubrics.version}};}}});
 try{
  assert.equal(typeof original,'string');
  const b=body(),first=await bridge.assess(b,r);
  assert.equal(first.status,200);
  rubrics.assessment_revision=original+'-test-change';
  const conflict=await bridge.assess(b,r);
  assert.equal(conflict.status,409);assert.equal(conflict.body.reason,'request_conflict');
  rubrics.assessment_revision=original;
  assert.deepEqual(await bridge.assess(b,r),first);assert.equal(calls,1);
 }finally{rubrics.assessment_revision=original;bridge.close();}
});
