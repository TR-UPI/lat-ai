export const REVIEW_NOTICE='Факты ещё не проверены преподавателем. Это не подтверждение правильности ответа.';
export const detailsLabel=count=>`Охват урока и общая справка — ${count}. Раскрыть`;
export function partitionFacts(facts,{role,protectedIds=[]}={}){
 if(!Array.isArray(facts)||!Array.isArray(protectedIds))throw Error('Invalid presentation data');
 const ids=new Set();
 for(const f of facts){
  if(!f||typeof f!=='object'||typeof f.id!=='string'||!f.id||ids.has(f.id)||typeof f.text!=='string'||typeof f.kind!=='string'||typeof f.scope!=='string')throw Error('Invalid fact');
  ids.add(f.id);
 }
 if(protectedIds.some(id=>!ids.has(id)))throw Error('Unknown protected fact');
 const protectedSet=new Set(protectedIds);
 const complete=role==='explain'&&facts.some(f=>f.kind==='computed_program'&&f.scope==='provided_code_only'&&f.provenance?.method==='closed_integer_analyzer')&&!facts.some(f=>f.kind==='analysis_limit');
 const primary=[],details=[];
 for(const f of facts){
  const support=(f.kind==='catalogue_scope'&&f.scope==='lesson_coverage_not_student_mastery')||(f.kind==='catalogue_rule'&&f.scope==='missing_information');
  (complete&&support&&!protectedSet.has(f.id)?details:primary).push(f);
 }
 return {primary,details,all:[...facts]};
}
export function renderFacts(host,facts,{role,protectedIds=[],collapsed=true}={}){
 const grouped=partitionFacts(facts,{role,protectedIds}),doc=host.ownerDocument;
 const el=(tag,text)=>{const n=doc.createElement(tag);if(text!==undefined)n.textContent=text;return n;};
 const list=rows=>{const ul=el('ul');for(const f of rows){const li=el('li',f.text);li.dataset.factId=f.id;ul.append(li);}return ul;};
 const nodes=[el('p',REVIEW_NOTICE)];nodes[0].className='notice';
 nodes.push(list(collapsed?grouped.primary:grouped.all));
 if(collapsed&&grouped.details.length){const box=el('details');box.append(el('summary',detailsLabel(grouped.details.length)),list(grouped.details));nodes.push(box);}
 host.replaceChildren(...nodes);return grouped;
}
