import test from 'node:test';
import assert from 'node:assert/strict';
import {loadWithDeadline,MAX_LOAD_DEADLINE_MS} from './sdk-load-with-deadline-v2.mjs';
const wait=ms=>new Promise(r=>setTimeout(r,ms));
test('invalid deadlines rejected before SDK dispatch or timer creation',async()=>{
 for(const ms of [MAX_LOAD_DEADLINE_MS+1,Number.MAX_SAFE_INTEGER,Infinity,NaN,0,-1,0.5,1.5,'120000']){
  let calls=0;await assert.rejects(loadWithDeadline({llm:{load:async()=>{calls++;}}},'fixture',{},ms));assert.equal(calls,0);
 }
});
test('maximum valid integer and default delay allow immediate successful load',async()=>{
 for(const ms of [MAX_LOAD_DEADLINE_MS,undefined]){
  let signal;assert.equal(await loadWithDeadline({llm:{load:async(_,o)=>{signal=o.signal;return 'ok';}}},'fixture',{},ms),'ok');assert.equal(signal.aborted,false);
 }
});
test('success and synchronous failure both clear the cancellation timer',async()=>{
 for(const fail of [false,true]){
  let aborts=0;const client={llm:{load:(_,o)=>{o.signal.addEventListener('abort',()=>aborts++);if(fail)throw Error('sync-failure');return Promise.resolve('ok');}}};
  if(fail)await assert.rejects(loadWithDeadline(client,'fixture',{},10),/sync-failure/);else await loadWithDeadline(client,'fixture',{},10);
  await wait(30);assert.equal(aborts,0);
 }
});
test('pending cooperative mock rejects once on abort without retry',async()=>{
 let calls=0,aborts=0;const client={llm:{load:(_,o)=>{calls++;return new Promise((_,reject)=>o.signal.addEventListener('abort',()=>{aborts++;reject(o.signal.reason);},{once:true}));}}};
 await assert.rejects(loadWithDeadline(client,'fixture',{},10),/SDK load deadline exceeded/);assert.equal(calls,1);assert.equal(aborts,1);
});
test('caller cannot substitute the managed signal',async()=>{
 let calls=0;await assert.rejects(loadWithDeadline({llm:{load:()=>calls++}},'fixture',{signal:new AbortController().signal}),/owns/);assert.equal(calls,0);
});
test('mechanism control: uncancelled old signal fires after success while managed timer does not',async()=>{
 let oldLate=0,newLate=0;const oldSignal=AbortSignal.timeout(10);await Promise.resolve('loaded');
 oldSignal.addEventListener('abort',()=>oldLate++);
 await loadWithDeadline({llm:{load:async(_,o)=>{o.signal.addEventListener('abort',()=>newLate++);return 'loaded';}}},'fixture',{},10);
 await wait(40);assert.equal(oldLate,1);assert.equal(newLate,0);
 // A mock mechanism control; not a reproduction of SDK transport failure or a live timeout.
});
