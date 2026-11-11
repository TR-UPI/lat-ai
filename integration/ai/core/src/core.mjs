import {readFileSync} from 'node:fs';
const read=(name)=>JSON.parse(readFileSync(new URL('../data/'+name,import.meta.url),'utf8'));
const catalogue=read('plan-catalogue.json').entries;
const bank=read('quiz-bank.json');
const uniq=a=>[...new Set(a)].sort();
const check=(ok,message)=>{if(!ok)throw new Error(message);};
export function normalizedEvents(events=[]){
 check(Array.isArray(events)&&events.length<=1000,'event count');
 const byId=new Map();
 for(const e of events){
  check(e&&typeof e==='object'&&['id','task_id','concept'].every(k=>typeof e[k]==='string'&&e[k].length>0&&e[k].length<=100),'event identity');
  check(['verified','pending','client_claim'].includes(e.status),'event status');
  check(typeof e.passed==='boolean'&&Number.isInteger(e.hints)&&e.hints>=0&&e.hints<=100,'event result');
  const n={id:e.id,task_id:e.task_id,concept:e.concept,status:e.status,passed:e.passed,hints:e.hints};
  check(!byId.has(e.id)||JSON.stringify(byId.get(e.id))===JSON.stringify(n),'event ID conflict');byId.set(e.id,n);
 }
 return [...byId.values()].sort((a,b)=>a.id.localeCompare(b.id,'en'));
}
export function profile(events=[]){
 const all=normalizedEvents(events),verified=all.filter(e=>e.status==='verified');
 const concepts=uniq(verified.map(e=>e.concept));
 return {observations:concepts.map(concept=>{
  const es=verified.filter(e=>e.concept===concept),ids=predicate=>uniq(es.filter(predicate).map(e=>e.id));
  const task_ids=uniq(es.map(e=>e.task_id));
  return {concept,evidence_ids:ids(()=>true),task_ids,failed_event_ids:ids(e=>!e.passed),unaided_success_event_ids:ids(e=>e.passed&&e.hints===0),assisted_success_event_ids:ids(e=>e.passed&&e.hints>0),unique_tasks:task_ids.length};
 }),unknown:all.length?uniq(all.filter(e=>!concepts.includes(e.concept)).map(e=>e.concept)):['all_requested_concepts'],chronology:'unknown_without_trusted_event_order',mastery_claims:[]};
}
function selectSteps(req){
 check(['L1','L2'].includes(req.lesson),'lesson');
 check(Array.isArray(req.topics)&&req.topics.length>0&&req.topics.length<=5&&req.topics.every(t=>typeof t==='string')&&new Set(req.topics).size===req.topics.length,'topics');
 check(Number.isInteger(req.count)&&req.count>=req.topics.length&&req.count<=8,'count');
 const groups=req.topics.map(topic=>{
  const g=catalogue.filter(e=>e.concept===topic);check(g.length>0,'topic');
  check(g.every(e=>req.lesson==='L2'||e.id.startsWith('L1.')),'lesson prerequisites');return g;
 });
 // Reserve one step for every requested concept, then fill in pedagogical order.
 const steps=[];let remaining=req.count;
 for(let i=0;i<groups.length;i++){
  const take=Math.min(groups[i].length,remaining-(groups.length-i-1));steps.push(...groups[i].slice(0,take));remaining-=take;
 }
 check(remaining===0,'count exceeds catalogue');return steps;
}
function evidence(entry,events){
 const es=events.filter(e=>e.status==='verified'&&e.concept===entry.concept);
 const matching=entry.kind==='diagnostic'?es.filter(e=>!e.passed):entry.kind==='independent'?es.filter(e=>e.passed):es;
 return uniq(matching.map(e=>e.id));
}
export function plan(req,events=[]){
 const es=normalizedEvents(events),selected=selectSteps(req);
 const min=selected.reduce((n,e)=>n+e.min_minutes,0),max=selected.reduce((n,e)=>n+e.max_minutes,0);
 check(Number.isInteger(req.minutes)&&req.minutes>=min&&req.minutes<=max,'infeasible minutes');
 const minutes=selected.map(e=>e.min_minutes);let spare=req.minutes-min;
 while(spare>0)for(let i=selected.length-1;i>=0&&spare>0;i--)if(minutes[i]<selected[i].max_minutes){minutes[i]++;spare--;}
 const result={steps:selected.map((e,i)=>({step_id:e.id,minutes:minutes[i],evidence_ids:evidence(e,es),activity:e.activity})),total_minutes:req.minutes,history_note:'Причина прежней ошибки неизвестна без кода и результата попытки.'};
 validatePlan(result,req,es);return result;
}
export function validatePlan(result,req,events=[]){
 const es=normalizedEvents(events),selected=selectSteps(req);
 check(Array.isArray(result.steps)&&result.steps.length===req.count,'step count');
 check(new Set(result.steps.map(s=>s.step_id)).size===req.count,'duplicate step');
 result.steps.forEach((s,i)=>{
  const e=selected[i];check(s.step_id===e.id,'step order/topic');
  check(Number.isInteger(s.minutes)&&s.minutes>=e.min_minutes&&s.minutes<=e.max_minutes,'minutes range');
  check(JSON.stringify(s.evidence_ids)===JSON.stringify(evidence(e,es)),'unsupported evidence');
 });
 check(Number.isInteger(req.minutes)&&result.total_minutes===req.minutes&&result.steps.reduce((n,s)=>n+s.minutes,0)===req.minutes,'minutes sum');return true;
}
export {hint} from './hint-ladder.mjs';
export function quiz(req){
 check(['L1','L2'].includes(req.lesson),'lesson');
 const candidates=bank.filter(q=>q.lesson===req.lesson);
 check(Number.isInteger(req.count)&&req.count>0&&req.count<=candidates.length,'quiz count');
 return {questions:candidates.slice(0,req.count).map(({id,stem,code,options})=>({id,stem,code,options:[...options]}))};
}
export function gradeQuiz(id,answer){
 const q=bank.find(q=>q.id===id);check(q,'quiz id');check(Number.isInteger(answer)&&answer>=0&&answer<q.options.length,'answer');
 return {id,correct:answer===q.correct_index};
}
