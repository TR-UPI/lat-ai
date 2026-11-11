import test from 'node:test';import assert from 'node:assert/strict';
import {partitionFacts} from './presentation.mjs';
const fact=(id,kind,scope,text=id)=>({id,kind,scope,text,provenance:{method:'closed_integer_analyzer'}});
const scope=fact('scope','catalogue_scope','lesson_coverage_not_student_mastery');
const diagnosis=fact('diagnosis','catalogue_rule','missing_information');
const program=fact('program','computed_program','provided_code_only');
const rule=fact('rule','catalogue_rule','general_rule_not_a_diagnosis');
const limit=fact('limit','analysis_limit','analyzer_did_not_establish_whole_program_result');
const split=(facts,extra={})=>partitionFacts(facts,{role:'explain',...extra});
test('closed complete program permits only scope and boilerplate in details',()=>{
 const rows=[scope,rule,diagnosis,program];const before=structuredClone(rows);const got=split(rows);
 assert.deepEqual(got.primary,[rule,program]);assert.deepEqual(got.details,[scope,diagnosis]);assert.deepEqual(rows,before);
 assert.equal(got.details[0],scope);assert.deepEqual(got.all,rows);
});
test('analysis limit veto keeps warning and all supporting facts visible',()=>{
 assert.deepEqual(split([scope,diagnosis,program,limit]).details,[]);
});
test('no full program: theory and expression facts remain visible',()=>{
 for(const rows of [[scope,rule,diagnosis],[scope,diagnosis,fact('range','computed_range','expression_only_not_program_execution')],[scope,diagnosis]])assert.deepEqual(split(rows).details,[]);
});
test('unknown or hint role never changes disclosure',()=>{
 for(const role of [undefined,'hint','grade','unknown'])assert.deepEqual(partitionFacts([scope,diagnosis,program],{role}).details,[]);
});
test('referenced facts remain visible even when normally collapsible',()=>{
 assert.deepEqual(split([scope,diagnosis,program],{protectedIds:['scope','diagnosis']}).details,[]);
});
test('unknown kinds/scopes and invalid program provenance fail closed',()=>{
 const unknown=fact('u','new_warning','provided_code_only');const wrong=fact('s2','catalogue_scope','different_scope');
 assert.deepEqual(split([scope,unknown,wrong,program]).primary,[unknown,wrong,program]);
 assert.deepEqual(split([scope,{...program,provenance:{method:'unknown'}}]).details,[]);
});
test('trace and conditional assumptions stay visible byte for byte',()=>{
 const trace=fact('trace','computed_trace','provided_code_only','Показано2/10. Пропущено8.');const cond=fact('cond','computed_pair','conditional_sequence_only','Если команды выполняются подряд…');
 assert.deepEqual(split([scope,program,trace,cond]).primary,[program,trace,cond]);
});
test('malformed rows/IDs/options reject without silently deleting evidence',()=>{
 for(const rows of [null,[scope,scope],[{...scope,id:''}],[{...scope,text:4}],[{...scope,kind:3}]])assert.throws(()=>split(rows));
 assert.throws(()=>split([scope,program],{protectedIds:['absent']}));
 assert.throws(()=>split([scope,program],{protectedIds:'scope'}));
});
test('empty data stays empty, hostile text stays literal data',()=>{
 assert.deepEqual(split([]),{primary:[],details:[],all:[]});
 const hostile=fact('x','unknown','unknown','<img src=x onerror=alert(1)>');assert.equal(split([hostile]).primary[0].text,hostile.text);
});
