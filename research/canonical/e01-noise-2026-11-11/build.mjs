import fs from 'node:fs';import {createHash} from 'node:crypto';import assert from 'node:assert/strict';
import {partitionFacts,REVIEW_NOTICE,detailsLabel} from './presentation.mjs';
const url=p=>new URL(p,import.meta.url),read=p=>JSON.parse(fs.readFileSync(url(p),'utf8'));
const inputs=read('inputs.json'),freeze=read('freeze.json');
const sha=p=>createHash('sha256').update(fs.readFileSync(url(p))).digest('hex');
assert.equal(sha('inputs.json'),freeze.inputs_sha256);assert.equal(sha('PLAN.txt'),freeze.plan_sha256);
const rows=[];
for(const variant of ['original','trace'])for(const entry of inputs){
 const facts=entry[variant].facts,before=JSON.stringify(facts),p=partitionFacts(facts,{role:'explain'});
 assert.equal(JSON.stringify(facts),before);assert.deepEqual(p.all,facts);
 const byId=new Map([...p.primary,...p.details].map(f=>[f.id,f]));assert.equal(byId.size,facts.length);
 assert.deepEqual(facts.map(f=>byId.get(f.id)),facts);
 assert.deepEqual(partitionFacts(facts,{role:'hint'}).primary,facts);
 assert.ok(p.details.every(f=>['catalogue_scope','catalogue_rule'].includes(f.kind)));
 for(const f of facts.filter(f=>!['catalogue_scope','catalogue_rule'].includes(f.kind)))assert.ok(p.primary.includes(f));
 const full=facts.map(f=>f.text).join('\n').length,visible=p.primary.map(f=>f.text).join('\n').length;
 rows.push({cohort:entry.cohort,id:entry.id,variant,total_facts:facts.length,visible_facts:p.primary.length,collapsed_facts:p.details.length,full_fact_chars:full,visible_fact_chars:visible,initial_chars_with_notice_and_summary:visible+REVIEW_NOTICE.length+(p.details.length?detailsLabel(p.details.length).length:0),baseline_chars_with_notice:full+REVIEW_NOTICE.length,full_payload_unchanged:true,trace_visible:facts.filter(f=>f.kind==='computed_trace').every(f=>p.primary.includes(f))});
}
const summaries={};
for(const variant of ['original','trace'])for(const cohort of ['historical','development']){
 const r=rows.filter(r=>r.variant===variant&&r.cohort===cohort),sum=k=>r.reduce((s,x)=>s+x[k],0);
 summaries[variant+'_'+cohort]={cases:r.length,collapsed_cases:r.filter(x=>x.collapsed_facts).length,collapsed_facts:sum('collapsed_facts'),mean_full_fact_chars:sum('full_fact_chars')/r.length,mean_visible_fact_chars:sum('visible_fact_chars')/r.length,initial_reduction_pct:100*(1-sum('initial_chars_with_notice_and_summary')/sum('baseline_chars_with_notice')),fact_reduction_pct:100*(1-sum('visible_fact_chars')/sum('full_fact_chars')),full_payload_unchanged:true};
}
fs.writeFileSync(url('comparison.json'),JSON.stringify({passed:true,primary:'original_*; trace_* compatibility only',holdout:false,model_calls:0,summaries,rows},null,2));
const module=fs.readFileSync(url('presentation.mjs'),'utf8').replace(/export /g,'');
const data=JSON.stringify(inputs).replace(/</g,'\\u003c').replace(/\u2028/g,'\\u2028').replace(/\u2029/g,'\\u2029');
const html=`<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline';"><title>LAD AI — сравнение отображения фактов</title><style>
*{box-sizing:border-box}body{margin:0;background:#f6f7f9;color:#172b3d;font:16px/1.55 system-ui,sans-serif}main{max-width:1200px;margin:auto;padding:24px}h1{font-size:1.7rem;margin:0 0 8px}h2{font-size:1.15rem}label{display:block;font-weight:600;margin:12px 0 4px}select,button{font:inherit;max-width:100%;padding:8px}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#eaf0f4;padding:12px}.columns{display:grid;grid-template-columns:1fr 1fr;gap:20px}.card{background:white;border:1px solid #ccd6de;border-radius:10px;padding:18px;min-width:0}li{white-space:pre-wrap;overflow-wrap:anywhere;margin:10px 0}ul{padding-left:22px}.notice{border-left:4px solid #a86d12;background:#fff4dd;padding:10px;font-size:.92rem}details{margin-top:18px;background:#eef3f7;padding:12px;border-radius:6px}summary{cursor:pointer;font-weight:600}summary:focus-visible,select:focus-visible{outline:3px solid #176c9b;outline-offset:3px}.small{font-size:.9rem;color:#3b5263}.controls{display:flex;flex-wrap:wrap;gap:18px}.question{white-space:pre-wrap;overflow-wrap:anywhere}@media(max-width:720px){main{padding:12px}.columns{grid-template-columns:1fr}.card{padding:12px}}@media print{details>ul{display:block!important}summary{display:block}.controls{display:none}.columns{display:block}.card{break-inside:avoid}}
</style><main><h1>LAD AI · сравнение отображения</h1><p>Одинаковые факты, два способа показа. Это эксперимент для взрослого оценщика; живой модели здесь нет.</p><div class="controls"><div><label for="case">Пример</label><select id="case"></select></div><div><label for="variant">Набор фактов</label><select id="variant"><option value="original">Исходные факты — основной эксперимент</option><option value="trace">С трассой — проверка совместимости</option></select></div></div><h2>Вопрос и код</h2><div id="question" class="question"></div><pre id="code" hidden></pre><p id="measure" class="small"></p><div class="columns"><section class="card"><h2>Все факты сразу</h2><div id="before"></div></section><section class="card"><h2>Справка свёрнута</h2><div id="after"></div></section></div><p class="small">Меньше текста на первом экране не доказывает лучшее понимание. Раскройте справку: исходные формулировки и оговорки сохранены.</p></main><script type="application/json" id="data">${data}</script><script type="module">${module}
const inputs=JSON.parse(document.getElementById('data').textContent),cases=document.getElementById('case'),variant=document.getElementById('variant');
for(const [i,c] of inputs.entries()){const option=document.createElement('option');option.value=String(i);option.textContent=(c.cohort==='historical'?'Прежний':'Новый dev')+' '+c.id;cases.append(option);}
function show(){const c=inputs[Number(cases.value)],facts=c[variant.value].facts;document.getElementById('question').textContent=c.request.message;const code=document.getElementById('code');code.hidden=!c.request.code_context;code.textContent=c.request.code_context?.code??'';renderFacts(document.getElementById('before'),facts,{role:'explain',collapsed:false});const p=renderFacts(document.getElementById('after'),facts,{role:'explain'});document.getElementById('measure').textContent='Фактов сразу: '+p.primary.length+' из '+facts.length+'. В раскрываемой справке: '+p.details.length+'.';}
cases.addEventListener('change',show);variant.addEventListener('change',show);show();
</script></html>`;
fs.writeFileSync(url('PREVIEW.html'),html);
console.log(JSON.stringify(summaries,null,2));
