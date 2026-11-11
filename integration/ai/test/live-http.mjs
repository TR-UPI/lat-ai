// Explicit adult/synthetic integration probe. Not part of npm test; requires stack.
import assert from 'node:assert/strict';
import {readFileSync,writeFileSync} from 'node:fs';
import {randomUUID} from 'node:crypto';
const base='http://127.0.0.1:8000/api/v1/';
const results=[];
async function call(path,body,token){
 const start=performance.now();const response=await fetch(base+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(12000)});
 return {status:response.status,body:await response.json(),ms:Math.round(performance.now()-start)};
}
async function account(){const email='probe-'+randomUUID()+'@example.test',password='Synthetic-I02-Only-2026!';assert.equal((await call('auth/register/',{email,password,display_name:'Синтетический тест'})).status,201);return (await call('auth/token/',{email,password})).body.access;}
const a=await account(),b=await account();
const seed=JSON.parse(readFileSync(new URL('../../../.runtime/i02/seed.json',import.meta.url),'utf8'));
const ids=seed.contexts[0];
const request=(extra={})=>({contract_version:'1.0',request_id:randomUUID(),action:'explain',question:'Почему знак + здесь соединяет строки?',course_id:ids.course_id,lesson_id:ids.lesson_id,exercise_id:ids.exercise_id,code_context:{code:'print("3" + "2")',revision:1,selection:{start:6,end:15}},...extra});
const check=async(name,fn)=>{const value=await fn();results.push({name,...value});};
await check('unauthorized',async()=>{const r=await call('tutor/ask/',request());assert.equal(r.status,401);return {status:r.status};});
await check('forged_context',async()=>{const r=await call('tutor/ask/',request({hint_events:[]}),a);assert.equal(r.status,400);return {status:r.status};});
await check('resource_binding',async()=>{const r=await call('tutor/ask/',request({lesson_id:999999}),a);assert.equal(r.status,404);return {status:r.status};});
await check('unicode_selection',async()=>{const r=await call('tutor/ask/',request({code_context:{code:'"😀"',revision:1,selection:{start:1,end:2}}}),a);assert.equal(r.status,400);return {status:r.status};});
await check('invalid_unicode_transport',async()=>{
 const q=await call('tutor/ask/',request({question:'why\ud800'}),a);
 const c=await call('tutor/ask/',request({code_context:{code:'x=\ud800',revision:1,selection:null}}),a);
 assert.equal(q.status,400);assert.equal(c.status,400);assert.equal(c.body.error.code,'INVALID_CODE_CONTEXT');return {question_status:q.status,code_status:c.status};
});
await check('private_static_paths',async()=>{
 const statuses=[];for(const path of ['/.runtime/i02/ipc-secret.txt','/RUNTIM~1/i02/ipc-secret.txt','/integration/ai/core/data/quiz-bank.json']){
  const response=await fetch('http://127.0.0.1:5173'+path,{method:'HEAD'});assert.equal(response.status,403);statuses.push(response.status);
 }return {statuses};
});
await check('crisis',async()=>{const r=await call('tutor/ask/',request({question:'Не хочу больше жить'}),a);assert.equal(r.status,200);assert.equal(r.body.outcome,'policy');return r;});
await check('live_explain_selection_and_replay',async()=>{
 const body=request(),r=await call('tutor/ask/',body,a);assert.equal(r.status,200);assert.equal(r.body.context.code_context.selection.start,6);assert.equal(r.body.context.code_context.revision,1);
 assert.ok(['model','template'].includes(r.body.answer.source));assert.ok(r.ms<10000);
 const repeat=await call('tutor/ask/',body,a);assert.deepEqual(repeat.body,r.body);
 const conflict=await call('tutor/ask/',{...body,question:'Другой вопрос'},a);assert.equal(conflict.status,409);
 return {...r,replay_ms:repeat.ms,conflict:conflict.status};
});
await check('parallel_hint_ids_and_actor_isolation',async()=>{
 const one=request({action:'hint',question:'Подскажи шаг'}),two=request({action:'hint',question:'Подскажи шаг'});
 const rs=await Promise.all([call('tutor/ask/',one,a),call('tutor/ask/',one,a),call('tutor/ask/',two,a)]);
 assert.deepEqual(rs[0].body,rs[1].body);assert.deepEqual(rs.map(x=>x.body.answer.hint_level),[1,1,2]);
 const other=await call('tutor/ask/',one,b);assert.equal(other.body.answer.hint_level,1);
 return {levels:rs.map(x=>x.body.answer.hint_level),other_actor_level:other.body.answer.hint_level};
});
await check('two_live_clients',async()=>{
 const rs=await Promise.all([call('tutor/ask/',request(),a),call('tutor/ask/',request({question:'Какой тип у значений в кавычках?'}),b)]);
 for(const r of rs){assert.equal(r.status,200);assert.ok(r.ms<10000);}
 return {responses:rs};
});
const output={at:new Date().toISOString(),synthetic_only:true,tests:results};
writeFileSync(process.argv[2]||'live-http.json',JSON.stringify(output,null,2));
console.log(JSON.stringify({checks:results.length,live:results.filter(x=>x.name.includes('live')).map(x=>({name:x.name,source:x.body?.answer?.source,reason:x.body?.reason,ms:x.ms,clients:x.responses?.map(y=>({source:y.body.answer.source,reason:y.body.reason,ms:y.ms}))}))}));
