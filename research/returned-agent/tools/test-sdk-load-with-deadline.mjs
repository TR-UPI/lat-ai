import test from 'node:test';
import assert from 'node:assert/strict';
import {loadWithDeadline} from './sdk-load-with-deadline.mjs';
const wait=ms=>new Promise(r=>setTimeout(r,ms));
test('successful load never receives late cancel after client disposal',async()=>{let aborts=0,signal;const client={llm:{load:async(key,opts)=>{signal=opts.signal;signal.addEventListener('abort',()=>aborts++);return {id:key};}}};assert.deepEqual(await loadWithDeadline(client,'owned-fixture',{},10),{id:'owned-fixture'});await wait(30);assert.equal(aborts,0);assert.equal(signal.aborted,false);});
test('failed load clears deadline too, with no retry',async()=>{let calls=0,aborts=0;const client={llm:{load:async(key,{signal})=>{calls++;signal.addEventListener('abort',()=>aborts++);throw Error('load failed');}}};await assert.rejects(loadWithDeadline(client,'fixture',{},10),/load failed/);await wait(30);assert.equal(calls,1);assert.equal(aborts,0);});
test('pending load gets one abort and no retry',async()=>{let calls=0,aborts=0;const client={llm:{load:(key,{signal})=>{calls++;return new Promise((resolve,reject)=>signal.addEventListener('abort',()=>{aborts++;reject(signal.reason);},{once:true}));}}};await assert.rejects(loadWithDeadline(client,'fixture',{},10),/deadline exceeded/);assert.equal(calls,1);assert.equal(aborts,1);});
test('caller signal cannot override deadline ownership',async()=>{let calls=0;const client={llm:{load:()=>calls++}};await assert.rejects(loadWithDeadline(client,'fixture',{signal:new AbortController().signal}),/owns/);assert.equal(calls,0);});
