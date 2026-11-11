import test from 'node:test';
import assert from 'node:assert/strict';
import {validateCandidate as validateAssessment,assessmentInput,assessmentSchema,segments} from '../core/src/assessment.mjs';
const ref=x=>x===0?null:'S'+x;
const obj=x=>x.length===3?{counter:typeof x[0]==='boolean'?(x[0]?'S1':null):x[0],start:ref(x[1]),end:ref(x[2])}:x;
const raw=(a,b=[false,0,0],c=[false,0,0])=>({answer:JSON.stringify({criterion_1:obj(a),criterion_2:obj(b),criterion_3:obj(c)}),finish_reason:'stop',stats:{total_output_tokens:40,reasoning_output_tokens:0}});
test('a multi-fragment quote is an exact original substring including CRLF and whitespace',()=>{
 const answer='  Один раз s=0;  сброса нет.\r\n  Затем сумма растёт.  ';
 const result=validateAssessment(raw([false,1,2]),answer);
 assert.deepEqual(result.checks,[true,false,false]);
 assert.equal(result.evidence[0],'Один раз s=0;  сброса нет.');
 assert.equal(validateAssessment(raw([false,1,3]),answer).evidence[0],'Один раз s=0;  сброса нет.\r\n  Затем сумма растёт.');
});
test('contradiction overrides a positive span only for that criterion',()=>{
 const result=validateAssessment(raw([true,1,1],[false,1,1],[false,0,0]),'Утверждение. Противоречие.');
 assert.deepEqual(result.checks,[false,true,false]);assert.deepEqual(result.evidence,['','Утверждение.','']);
});
test('duplicate text offsets preserve the selected occurrence and intervening text',()=>{
 const answer='Повтор. Между. Повтор. Конец.';
 assert.equal(validateAssessment(raw([false,3,4]),answer).evidence[0],'Повтор. Конец.');
});
test('invalid, reversed, partial-zero and untyped spans never become a score',()=>{
 for(const tuple of [[false,0,1],[false,2,1],[false,-1,-1],[false,1,3],[false,1.5,2],['false',1,1],[false,true,1],[false,1],[false,1,1,1]])assert.throws(()=>validateAssessment(raw(tuple),'A. B.'));
 assert.throws(()=>validateAssessment({...raw([false,1,1]),answer:'{"criterion_1":[false,1,1],"criterion_1":[false,1,1],"criterion_2":[false,0,0],"criterion_3":[false,0,0]}'},'A.'));
 assert.throws(()=>validateAssessment({...raw([false,1,1]),answer:'{"criterion_1":0,"criterion_2":-1,"criterion_3":-1}'},'A.'));
});
test('truncation and reasoning fail closed',()=>{
 for(const delta of [{finish_reason:'length'},{stats:{total_output_tokens:192,reasoning_output_tokens:0}},{stats:{total_output_tokens:40,reasoning_output_tokens:1}}])assert.throws(()=>validateAssessment({...raw([false,1,1]),...delta},'A.'));
});
test('fragment cap, named input ids and schema limits agree',()=>{
 const req={message:'A. B.',assessment:{task_key:'L1.types.1'}};
 assert.deepEqual(assessmentInput(req).student_answer,[{id:'S1',text:'A.'},{id:'S2',text:'B.'}]);
 assert.deepEqual(assessmentSchema(req).properties.criterion_1.properties.start.enum,[null,'S1','S2']);
 const long=Array.from({length:33},(_,i)=>`S${i}.`).join('\n');
 assert.equal(segments(long).length,1);assert.equal(validateAssessment(raw([false,1,1]),long).evidence[0],long);
});
