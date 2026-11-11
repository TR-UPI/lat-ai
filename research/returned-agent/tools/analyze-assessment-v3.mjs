import {readFileSync,mkdirSync,writeFileSync,copyFileSync} from 'node:fs';
import {validateAssessment as previousValidate} from '../outputs/assessment-v3-2026-11-11/source-before/integration/ai/core/src/assessment.mjs';
const base=new URL('../outputs/assessment-v3-2026-11-11/',import.meta.url);
const read=p=>JSON.parse(readFileSync(new URL(p,base),'utf8'));
mkdirSync(new URL('stability48/',base));let all=[];
for(const session of [1,2]){
 const cases=read('stability-session'+session+'.json');all.push(...cases);
 for(const c of cases)copyFileSync(new URL('stability-session'+session+'/'+c.id+'.json',base),new URL('stability48/'+c.id+'.json',base));
}
writeFileSync(new URL('stability48.json',base),JSON.stringify(all,null,2));
writeFileSync(new URL('stability48/PROVENANCE.txt',base),'Two separate model loads, 8 preselected known answers repeated3 times each in each load. Same frozen D code, rotating order.48 calls but only8 unique texts, not48 independent validation cases. Session2 records stage timings; session1 does not.\n');
const cases=read('holdout32.json');mkdirSync(new URL('holdout-h-same-raw/',base));const review=[];let changed=0;
for(const c of cases){
 const row=read('holdout32/'+c.id+'.json');let result=null,error=null;
 try{result=previousValidate(row.raw,c.answer);}catch(e){error=e.message;}
 if(JSON.stringify(result?.checks??null)!==JSON.stringify(row.actual))throw Error('Decision changed in D: '+c.id);
 if(JSON.stringify(result?.evidence)!==JSON.stringify(row.result?.evidence))changed++;
 writeFileSync(new URL('holdout-h-same-raw/'+c.id+'.json',base),JSON.stringify({...row,result,actual:result?.checks??null,error,ms:null,stages:undefined,provenance:'Same live model responses as D; previous H postprocessing replay, not an independent baseline run.'},null,2));
 review.push([c.id+' | '+c.category+' | '+c.task_key,'ANSWER: '+c.answer,'EXPECTED: '+JSON.stringify(c.expected),'ACTUAL: '+JSON.stringify(row.actual)+' / '+row.diagnosis,'EVIDENCE: '+JSON.stringify(row.result?.evidence),'COUNTERS: '+JSON.stringify(row.counters)].join('\n'));
}
writeFileSync(new URL('holdout-h-same-raw/PROVENANCE.txt',base),'Previous H validator applied to the same fresh D model responses. Prompts and decisions are unchanged; only deterministic citation context differs. This is not a separate model run and has no standalone latency.\n');
writeFileSync(new URL('holdout-review.txt',base),review.join('\n\n')+'\n');
writeFileSync(new URL('holdout31-sensitivity.json',base),JSON.stringify(cases.filter(c=>c.id!=='V31'),null,2));
const queue=cases.map(c=>({c,r:read('holdout32/'+c.id+'.json')})).filter(({r})=>r.actual===null||!r.match).map(({c,r})=>({id:c.id,task_key:c.task_key,answer:c.answer,author_expected:c.expected,actual:r.actual,reason:r.diagnosis,counters:r.counters,teacher_decision:null,teacher_notes:''}));
writeFileSync(new URL('manual-review-queue.json',base),JSON.stringify({source:'synthetic diagnostics only, not real student pilot',cases:queue},null,2));
console.log(JSON.stringify({stability_calls:all.length,unique_stability_answers:new Set(all.map(c=>c.source_id)).size,holdout:cases.length,decision_changes:0,evidence_changes:changed,manual_review_cases:queue.length}));
