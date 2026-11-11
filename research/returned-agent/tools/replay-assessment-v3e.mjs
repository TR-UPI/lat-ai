import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import assert from 'node:assert/strict';
import {validateAssessment} from '../lat-ai/integration/ai/core/src/assessment.mjs';
const old=new URL('../outputs/assessment-v3-2026-11-11/',import.meta.url);
const out=new URL('../outputs/ai-continuation-2026-11-11/',import.meta.url);
const read=p=>JSON.parse(readFileSync(new URL(p,old),'utf8'));
mkdirSync(new URL('replay160/',out));let count=0,changes=[],correct=0,wrong=0,refusals=0;
for(const [file,folder] of [['regression128-with-evidence.json','candidate-d-replay'],['holdout32.json','holdout32']]){
 for(const c of read(file)){
  const previous=read(folder+'/'+c.id+'.json');let result=null,error=null;
  try{result=validateAssessment(previous.raw,c.answer);}catch(e){error=e.message;}
  assert.deepEqual(result?.checks??null,previous.actual,'Decision changed: '+c.id);
  if(JSON.stringify(result?.evidence??null)!==JSON.stringify(previous.result?.evidence??null))changes.push({id:c.id,before:previous.result?.evidence,after:result?.evidence});
  if(!result)refusals++;else if(JSON.stringify(result.checks)===JSON.stringify(c.expected))correct++;else wrong++;
  if(c.id==='V11')assert.ok(result.evidence[0].includes('x := 2;')&&result.evidence[0].includes('проверка x==2 := True;'));
  writeFileSync(new URL('replay160/'+c.id+'.json',out),JSON.stringify({...previous,result,error,actual:result?.checks??null,ms:null,stages:undefined,provenance:'Known-data deterministic replay of saved model output; NOT new inference/holdout.'},null,2));count++;
 }
}
assert.equal(count,160);assert.deepEqual(changes.map(c=>c.id),['V11']);
const report={cases:count,decision_changes:0,correct,wrong,refusals,evidence_changes:changes,scope:'Known-data regression replay. Does not establish real-student accuracy or neural improvement.'};
writeFileSync(new URL('replay160-summary.json',out),JSON.stringify(report,null,2));console.log(JSON.stringify(report));
