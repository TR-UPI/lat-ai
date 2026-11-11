// DOM contract test double, not a browser or accessibility conformance test.
import test from 'node:test';import assert from 'node:assert/strict';
import {renderFacts,REVIEW_NOTICE} from './presentation.mjs';
class Element{
 constructor(tag,doc){this.tag=tag;this.ownerDocument=doc;this.children=[];this.dataset={};this.text='';}
 set textContent(v){this.text=String(v);this.children=[];}
 get textContent(){return this.text+this.children.map(c=>c.textContent).join('');}
 set innerHTML(v){throw Error('HTML interpolation forbidden');}
 append(...nodes){this.children.push(...nodes);}
 replaceChildren(...nodes){this.text='';this.children=[...nodes];}
}
const document={createElement(tag){assert.ok(['div','p','ul','li','details','summary'].includes(tag));return new Element(tag,document);}};
const make=(id,kind,scope,text)=>({id,kind,scope,text,provenance:{method:'closed_integer_analyzer'}});
const facts=[make('s','catalogue_scope','lesson_coverage_not_student_mastery','<img src=x onerror=alert(1)>'),make('p','computed_program','provided_code_only','Итог <script>alert(2)</script>'),make('t','computed_trace','provided_code_only','Пропущено событий:8')];
const walk=n=>[n,...n.children.flatMap(walk)];
test('renderer preserves literal hostile markup and exact text in native nodes',()=>{
 const host=document.createElement('div');renderFacts(host,facts,{role:'explain'});
 const lis=walk(host).filter(n=>n.tag==='li');assert.equal(lis.length,3);
 for(const f of facts)assert.equal(lis.find(n=>n.dataset.factId===f.id).textContent,f.text);
 assert.equal(walk(host).some(n=>['img','script'].includes(n.tag)),false);
});
test('teacher warning and trace remain outside details; summary first child',()=>{
 const host=document.createElement('div');renderFacts(host,facts,{role:'explain'});
 assert.equal(host.children[0].textContent,REVIEW_NOTICE);
 const box=host.children.find(n=>n.tag==='details');assert.equal(box.children[0].tag,'summary');
 assert.match(box.children[0].textContent,/1/);assert.equal(box.open,undefined);
 assert.ok(host.children[1].children.some(n=>n.dataset.factId==='t'));
});
test('full view has every fact in original order and no collapsed box',()=>{
 const host=document.createElement('div');renderFacts(host,facts,{role:'explain',collapsed:false});
 assert.deepEqual(host.children[1].children.map(n=>n.dataset.factId),facts.map(f=>f.id));
 assert.equal(walk(host).some(n=>n.tag==='details'),false);
});
test('changing case replaces old expanded state; invalid data preserves old view',()=>{
 const host=document.createElement('div');renderFacts(host,facts,{role:'explain'});
 const old=host.children.find(n=>n.tag==='details');old.open=true;
 renderFacts(host,facts,{role:'explain'});const fresh=host.children.find(n=>n.tag==='details');
 assert.notEqual(fresh,old);assert.equal(fresh.open,undefined);
 const before=[...host.children];assert.throws(()=>renderFacts(host,[null],{role:'explain'}));assert.deepEqual(host.children,before);
});
