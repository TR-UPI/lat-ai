import {test} from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,writeFileSync,readFileSync,mkdirSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {decodeReferences,enrichCards,renderText,renderAudit,freezePresentation,sha,BASE_FIELDS} from './render-signal-review-cards.mjs';
const raw=(a,b,c)=>JSON.stringify({criterion_1:a,criterion_2:b,criterion_3:c});
const card=()=>({audit_id:'a'.repeat(32),task_code:'print("3"+"2")',criteria:['Типы','Склейка','Результат'],student_answer:'Это строки; плюс склеивает.\nВывод 32.',verifier_output:raw(0,1,2),human_decision:null,human_reason:null,reviewer_registry_id:null,reviewed_utc:null,prior_exposure_declared:null});
test('zero-based references and exact quotes use native segmentation',()=>{
 const d=decodeReferences(card().student_answer,raw(0,1,2));
 assert.deepEqual(d.fragments.map(f=>f.text),['Это строки;','плюс склеивает.','Вывод 32.']);
 assert.equal(d.references[0].quote,'Это строки;');assert.equal(d.references[2].fragment_id,2);
});
test('-1 is absence of selection, repeated references remain separate criteria',()=>{
 const d=decodeReferences('Одна фраза.',raw(-1,0,0));
 assert.equal(d.references[0].status,'no_fragment_selected');assert.equal(d.references[0].quote,null);
 assert.equal(d.references[1].quote,d.references[2].quote);
});
test('invalid numbers/types never acquire a quote or become -1',()=>{
 for(const value of [1,-2,0.5,'0',null,true]){
  const r=decodeReferences('Один.',raw(value,0,0)).references[0];assert.equal(r.status,'invalid_reference');assert.equal(r.quote,null);assert.equal(r.raw_index,value);
 }
});
test('missing/malformed/duplicate/extra keys are clearly unreadable',()=>{
 for(const r of [null,'bad','[]','{}','{"criterion_1":0,"criterion_1":0,"criterion_2":0,"criterion_3":0}',raw(0,0,0).replace('}',',"expected":true}')]){
  const d=decodeReferences('Ответ.',r);assert.ok(d.output_error);assert.ok(d.references.every(x=>x.quote===null&&x.status==='unreadable_output'));
 }
 const c=card();c.verifier_output='bad';const text=renderText(enrichCards({phase:'POST-LABEL fixture',cards:[c]}));
 assert.ok(text.includes('Ссылка не прочитана.'));assert.ok(!text.includes('Исходное значение ссылки: null'));
});
test('32 fragments stay separate; 33 trigger exact whole-answer fallback',()=>{
 const a=Array.from({length:32},(_,i)=>`${i}.`).join('\n');assert.equal(decodeReferences(a,raw(31,0,0)).fragment_count,32);
 const b='  '+a+'\n32.  ';const d=decodeReferences(b,raw(0,1,-1));assert.deepEqual(d.fragments,[{id:0,text:b}]);assert.equal(d.references[1].status,'invalid_reference');assert.match(d.single_fragment_notice,/не узкая цитата/);
});
test('source fields/order remain byte-equivalent as JSON; extra labels forbidden',()=>{
 const p={phase:'POST-LABEL fixture',cards:[card()]};const before=JSON.stringify(p);const enriched=enrichCards(p);
 assert.equal(JSON.stringify(p),before);assert.deepEqual(Object.fromEntries(BASE_FIELDS.map(k=>[k,enriched.cards[0][k]])),p.cards[0]);
 assert.throws(()=>enrichCards({...p,cards:[{...card(),expected:[true,true,true]}]}));
 assert.throws(()=>enrichCards({...p,cards:[card(),card()]}));assert.throws(()=>enrichCards({...p,cards:[{...card(),human_decision:'done'}]}));
});
test('quoted data cannot inject headings/newlines; unicode, code and negations retained',()=>{
 const c=card();c.student_answer='Нет!\nКАРТОЧКА fake\n<svg onload=x> 😀 x := 2;\nНе сбрасывается.\u202e';c.verifier_output=raw(0,1,-1);
 const p=enrichCards({phase:'POST-LABEL fixture',cards:[c]});const txt=renderText(p);
 assert.ok(txt.includes('😀 x := 2;'));assert.ok(txt.includes('\\nКАРТОЧКА fake'));assert.ok(txt.includes('\\u202e'));assert.ok(!txt.includes('\nКАРТОЧКА fake\n'));
 assert.equal(p.cards[0].student_answer,c.student_answer);
});
test('neutral labels distinguish selected/unselected/repeated references',()=>{
 const c=card();c.verifier_output=raw(0,0,-1);const p=enrichCards({phase:'POST-LABEL fixture',cards:[c]});const txt=renderText(p);
 assert.match(txt,/текст подставлен инструментом/);assert.match(txt,/Тот же фрагмент указан для критериев: 2/);
 assert.match(txt,/Фрагмент \[2\] \(verifier не выбрал/);assert.match(txt,/модель не зачла критерий/);
 assert.ok(!txt.includes('подтверждающий фрагмент'));assert.ok(!txt.includes('противоречащий фрагмент'));
});
test('full export preserves input; binds displayed files, rejects tamper/overwrite',()=>{
 const root=mkdtempSync(join(tmpdir(),'lat-card-test-')),source=join(root,'source');mkdirSync(source);mkdirSync(join(source,'reviewer'));
 const write=(p,v)=>writeFileSync(p,JSON.stringify(v));write(join(source,'reviewer/cards.json'),{phase:'POST-LABEL mechanics fixture',cards:[card()]});writeFileSync(join(source,'reviewer/READ_FIRST.txt'),'fixture');write(join(source,'PRIVATE_COORDINATOR.json'),{selection:[{audit_id:card().audit_id,source_id:'secret-label',stratum:'flagged'}],protocol_sha256:'fixture'});
 const names=['reviewer/cards.json','reviewer/READ_FIRST.txt','PRIVATE_COORDINATOR.json'];const manifest=Object.fromEntries(names.map(n=>[n,sha(readFileSync(join(source,n)))]));write(join(source,'MANIFEST.json'),manifest);
 const protocol=join(root,'protocol.json');freezePresentation(protocol);const out=join(root,'out');assert.equal(renderAudit(protocol,source,out).cards,1);
 const delivery=JSON.parse(readFileSync(join(out,'PRIVATE_DELIVERY.json')));assert.equal(delivery.files_seen_sha256['CARDS.txt'],sha(readFileSync(join(out,'reviewer/CARDS.txt'))));
 for(const [n,h]of Object.entries(manifest))assert.equal(sha(readFileSync(join(source,n))),h);
 assert.ok(!readFileSync(join(out,'reviewer/cards.json'),'utf8').includes('secret-label'));
 assert.throws(()=>renderAudit(protocol,source,out));writeFileSync(join(source,'reviewer/READ_FIRST.txt'),'changed');assert.throws(()=>renderAudit(protocol,source,join(root,'out2')),/Source export changed/);assert.equal(existsSync(join(root,'out2')),false);
});
