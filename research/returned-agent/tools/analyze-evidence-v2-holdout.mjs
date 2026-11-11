import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {validateAssessment as baselineValidator} from '../outputs/assessment-evidence-v2-2026-11-11/source-before/integration/ai/core/src/assessment.mjs';
import {segments,validateCandidate} from '../work/assessment-evidence-v2h-2026-11-11/integration/ai/core/src/assessment.mjs';
const base=new URL('../outputs/assessment-evidence-v2-2026-11-11/',import.meta.url);
const read=p=>JSON.parse(readFileSync(new URL(p,base),'utf8'));
const cases=read('holdout32.json'),oracle=read('holdout-counter-oracle.json');
for(const [name,key,validator] of [['holdout-v1-verification','verification',baselineValidator],['holdout-g-proposal','candidate',validateCandidate]]){
 mkdirSync(new URL(name+'/',base));
 for(const c of cases){
  const recorded=read('candidate-h-holdout/'+c.id+'.json'),raw=recorded.raw[key];let result=null,error=null;
  try{result=validator(raw,c.answer);}catch(e){error=e.message;}
  const row={id:c.id,task_key:c.task_key,expected:c.expected,actual:result?.checks??null,match:JSON.stringify(result?.checks)===JSON.stringify(c.expected),ms:null,error,raw,result,provenance:'Live '+key+' stage of H; no separate run; stage latency not instrumented.'};
  writeFileSync(new URL(name+'/'+c.id+'.json',base),JSON.stringify(row,null,2));
 }
 writeFileSync(new URL(name+'/PROVENANCE.txt',base),'Extracted from the fresh live H run. The verification stage uses frozen evidence-v1 source/prompt/rubrics, original answer only, without the proposal. It is not a separate randomized baseline run. Stage timing was not recorded.\n');
}
const counters=oracle.cases.map(o=>{
 const c=cases.find(c=>c.id===o.id),r=read('candidate-h-holdout/'+c.id+'.json');
 const record=JSON.parse(r.raw.candidate.answer)['criterion_'+o.criterion],id=record.counter;
 const text=id?segments(c.answer)[Number(id.slice(1))-1]:null;
 return {...o,selected_counter:id,text,match:typeof text==='string'&&o.required_counter_anchors.every(a=>text.includes(a)),final_actual:r.actual};
});
writeFileSync(new URL('holdout-counter-audit.json',base),JSON.stringify({matched:counters.filter(c=>c.match).length,total:counters.length,cases:counters},null,2));
writeFileSync(new URL('holdout31-sensitivity.json',base),JSON.stringify(cases.filter(c=>c.id!=='H23'),null,2));
const review=cases.map(c=>{
 const r=read('candidate-h-holdout/'+c.id+'.json');
 return [c.id+' | '+c.task_key+' | '+c.category,'ANSWER: '+c.answer,'EXPECTED: '+JSON.stringify(c.expected),'ACTUAL: '+JSON.stringify(r.actual)+' | '+r.error,'EVIDENCE: '+JSON.stringify(r.result?.evidence),'PROPOSAL: '+r.raw.candidate.answer,'VERIFICATION: '+r.raw.verification?.answer].join('\n');
}).join('\n\n');
writeFileSync(new URL('holdout-review.txt',base),review+'\n');
console.log(JSON.stringify({cases:cases.length,counters_matched:counters.filter(c=>c.match).length,counters_total:counters.length}));
