import {test} from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync} from 'node:fs';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import vm from 'node:vm';
import {Tutor as OriginalTutor} from '../lat-ai/integration/ai/core/src/tutor.mjs';
const build=JSON.parse(readFileSync(new URL('../lat-ai/.runtime/i02/processes.json',import.meta.url))).build;
const {createLifecycle}=await import(pathToFileURL(resolve(build,'integration/ai/lifecycle.mjs')));
const req={role:'explain',lesson:'L1',topic:'types',message:'Почему это строка?'};
function setup(delay){
 let quarantine=false,posts=0;
 const model={model:'synthetic-only',get state(){return {quarantined:quarantine,phase:quarantine?'quarantined':'idle',retired:false};},isReady:async()=>true,recover:()=>{},quarantineActive:()=>{quarantine=true;},
 generate:(_req,{signal})=>{posts++;return new Promise((resolve,reject)=>{
  const timer=delay===null?null:setTimeout(()=>resolve({answer:JSON.stringify({text:'Кавычки обозначают строковое значение, а не число.',source_ids:['L1']}),finish_reason:'stop',stats:{total_output_tokens:20,reasoning_output_tokens:0}}),delay);
  signal.addEventListener('abort',()=>{clearTimeout(timer);reject(Error('aborted'));},{once:true});
 });}};
 return {life:createLifecycle({loadOwned:async()=>model}),posts:()=>posts};
}
test('original source keeps its 8-second maximum',()=>{
 assert.throws(()=>new OriginalTutor({modelBudgetMs:60000}),/budget/);
 assert.equal(new OriginalTutor().budget,8000);
});
test('only local browser explain and assessment timeouts become 80 seconds',async()=>{
 for(const [file,expected] of [[new URL('../lat-ai/assets/data.js',import.meta.url),[10000,30000]],[resolve(build,'assets/data.js'),[80000,80000]]]){
  const timers=[];const window={};
  vm.runInNewContext(readFileSync(file,'utf8'),{window,URL,Headers,FormData,AbortController,fetch:async()=>new Response('{}'),setTimeout:(_f,ms)=>{timers.push(ms);return 1;},clearTimeout:()=>{}});
  await window.LAT.tutorAsk({});await window.LAT.submitAttempt(1,'Synthetic answer');
  assert.deepEqual(timers,expected);
 }
});
test('two synthetic 11-second answers survive old model and transport deadlines',{timeout:30000},async()=>{
 const s=setup(11000);await s.life.control('enable');
 const first=s.life.respond(req);await new Promise(r=>setTimeout(r,20));const second=s.life.respond(req);
 const results=await Promise.all([first,second]);
 assert.deepEqual(results.map(x=>x.path),['model','model']);
 assert.ok(results[1].metrics.total_ms>21000);assert.equal(s.posts(),2);
 assert.equal(s.life.health().tutor.quarantined,false);
});
test('local 60-second timeout keeps quarantine and never repeats unknown POST',{timeout:65000},async()=>{
 const s=setup(null);await s.life.control('enable');const result=await s.life.respond(req);
 assert.equal(result.reason,'timeout');assert.ok(result.metrics.total_ms>=59900&&result.metrics.total_ms<62000);
 assert.equal((await s.life.respond(req)).reason,'quarantined');assert.equal(s.posts(),1);
});
