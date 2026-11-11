import test from 'node:test';
import assert from 'node:assert/strict';
import {completeEvidenceContext} from '../core/src/assessment-evidence-context.mjs';
import {segments} from '../core/src/assessment.mjs';
const record=(a,b=a)=>({start:'S'+a,end:'S'+b,counter:null});
function complete(answer,records,checks=[true,true,true],task='L1.condition.1'){
 const parts=segments(answer);const evidence=checks.map((ok,i)=>ok?parts.slice(Number(records['criterion_'+(i+1)].start.slice(1))-1,Number(records['criterion_'+(i+1)].end.slice(1))).join(' '):'');
 const result=completeEvidenceContext({checks,evidence,rubric_version:'local-assessment-v1'},records,parts,answer,task);
 assert.deepEqual(result.checks,checks);return result;
}
test('fills the missing variable value without confusing comparison with assignment',()=>{
 const answer='x: 2;  x == 2: True; if исполняется; else пропускается; экран: да.';
 const r=complete(answer,{criterion_1:record(2),criterion_2:record(3,4),criterion_3:record(5)});
 assert.equal(r.evidence[0],'x: 2;  x == 2: True;');
});
test('fills the other branch from a unique original fragment and preserves CRLF',()=>{
 const answer='x равен 2, проверка истинна.\r\nif выводит да.\r\nelse пропускается.';
 const r=complete(answer,{criterion_1:record(1),criterion_2:record(3),criterion_3:record(2)});
 assert.equal(r.evidence[1],'if выводит да.\r\nelse пропускается.');
 assert.equal(r.evidence[2],'if выводит да.');
});
test('missing or ambiguous context is never invented and false checks stay empty',()=>{
 const answer='if исполняется. if не исполняется. else пропускается.';
 const r=complete(answer,{criterion_1:record(1),criterion_2:record(3),criterion_3:record(1)},[false,true,false]);
 assert.deepEqual(r.evidence,['','else пропускается.','']);
 const absent='Условие истинно. else пропускается.';
 assert.equal(complete(absent,{criterion_1:record(1),criterion_2:record(2),criterion_3:record(1)},[false,true,false]).evidence[1],'else пропускается.');
});
test('other tasks and complete evidence remain unchanged',()=>{
 const answer='x равен 2 и сравнение истинно. if выполняется, else пропускается. Вывод да.';
 const records={criterion_1:record(1),criterion_2:record(2),criterion_3:record(3)};
 const r=complete(answer,records);assert.deepEqual(r.evidence,segments(answer));
 assert.deepEqual(complete(answer,records,[true,true,true],'L2.range.1').evidence,segments(answer));
});

test('explicit assignment notation completes the original citation; comparisons and other numbers do not',()=>{
 const records={criterion_1:record(2),criterion_2:record(3,4),criterion_3:record(5)};
 for(const prefix of ['x := 2','x: 2','x = 2','x равен 2']){
  const answer=prefix+'; проверка истинна; if выбран; else пропущен; вывод да.';
  assert.equal(complete(answer,records).evidence[0],prefix+'; проверка истинна;');
 }
 for(const prefix of ['x == 2','x != 2','x <= 2','x = 20','x = 2.5','x := 2.5','x = 2e3','x = 2_000']){
  const answer=prefix+'; проверка истинна; if выбран; else пропущен; вывод да.';
  assert.equal(complete(answer,records).evidence[0],'проверка истинна;');
 }
});

test('notation completion preserves CRLF and refuses to guess between duplicate assignments',()=>{
 const records={criterion_1:record(2),criterion_2:record(3),criterion_3:record(3)};
 const answer='x := 2;\r\nпроверка x==2 := True;\r\nif выбран, else пропущен, вывод да.';
 assert.equal(complete(answer,records).evidence[0],'x := 2;\r\nпроверка x==2 := True;');
 const duplicate='x := 2; проверка истинна; x := 2; if выбран, else пропущен.';
 assert.equal(complete(duplicate,records).evidence[0],'проверка истинна;');
});
