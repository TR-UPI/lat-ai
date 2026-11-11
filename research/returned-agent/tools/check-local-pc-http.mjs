import {readFileSync,writeFileSync,appendFileSync,mkdirSync} from 'node:fs';
import {resolve} from 'node:path';
import {randomUUID} from 'node:crypto';
import assert from 'node:assert/strict';
const dir=resolve(process.argv[2]);mkdirSync(dir,{recursive:true});
const record=x=>{console.log(JSON.stringify(x));appendFileSync(resolve(dir,'http.jsonl'),JSON.stringify(x)+'\n');};
const base='http://127.0.0.1:8000/api/v1/';
async function api(path,token,body){const r=await fetch(base+path,{method:body?'POST':'GET',headers:{'Content-Type':'application/json',...(token?{Authorization:'Bearer '+token}:{})},...(body?{body:JSON.stringify(body)}:{}),signal:AbortSignal.timeout(80000)});const data=await r.json();if(!r.ok)throw Error(path+' HTTP '+r.status);return data;}
const creds={email:'review@lad-ai.local',password:'LadAI-Review-2026!'};
const a=(await api('auth/token/',null,creds)).access;
const email='latency-'+randomUUID().slice(0,8)+'@lat-ai.local',password=randomUUID();
await api('auth/register/',null,{email,password,display_name:'Синтетическая проверка задержек'});
const b=(await api('auth/token/',null,{email,password})).access;
const seed=JSON.parse(readFileSync(new URL('../lat-ai/.runtime/i02/seed.json',import.meta.url)));
const rubric=JSON.parse(readFileSync(new URL('../lat-ai/integration/ai/core/data/assessment-rubrics.json',import.meta.url))).tasks;
async function ask(token,index,question,name){
 const c=seed.contexts[index],code=rubric[c.task_key].code;
 const request_id=randomUUID(),start=performance.now();
 const result=await api('tutor/ask/',token,{contract_version:'1.0',request_id,action:'explain',question,course_id:c.course_id,lesson_id:c.lesson_id,exercise_id:c.exercise_id,code_context:{code,revision:1,selection:null}});
 record({name,request_id,http_ms:performance.now()-start,outcome:result.outcome,source:result.answer?.source,reason:result.reason});
 writeFileSync(resolve(dir,name+'.json'),JSON.stringify(result,null,2));
 assert.equal(result.answer?.source,'model',name);return result;
}
await ask(a,0,'Почему получается 32, а не 5?','single');
await Promise.all([ask(a,1,'Объясни порядок проверки условия и выбор ветки.','pair1-a'),ask(b,3,'Объясни изменения s на каждом проходе и почему print после цикла.','pair1-b')]);
await Promise.all([ask(a,2,'Объясни какие значения принимает i и почему правая граница исключена.','pair2-a'),ask(b,3,'Подробно объясни, что происходит до цикла, на каждой итерации и после цикла.','pair2-b')]);
const start=performance.now();const grade=await api('progress/attempts/',b,{exercise:seed.contexts[0].exercise_id,answer:'Оба значения в кавычках являются строками. Оператор плюс соединяет строки, а не складывает числа. Выводится 32.'});
record({name:'assessment',http_ms:performance.now()-start,status:grade.status,score:grade.score,attempt_id:grade.id});
assert.equal(grade.status,'auto_checked');
writeFileSync(resolve(dir,'assessment.json'),JSON.stringify(grade,null,2));
record({event:'complete',synthetic_account:email});
