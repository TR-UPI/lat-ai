// Known author examples and one explicit malformed-output fixture, never real pilot.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {join} from 'node:path';
import {ROOT,enrichCards,renderText,sha} from './render-signal-review-cards.mjs';
const read=p=>JSON.parse(readFileSync(p,'utf8'));
const old=join(ROOT,'outputs/u02-runtime-controls-2026-11-11');
const cases=read(join(old,'known128-frozen/primary-cases.json'));
const rubrics=read(join(ROOT,'lat-ai/integration/ai/core/data/assessment-verifier-rubrics.json')).tasks;
const cards=[],provenance=[];
for(const [id,series]of [['U02',1],['U46',3]]){
 const c=cases.find(x=>x.id===id),path=join(old,`known128-live-${series}`,`R${series}-${id}.json`),r=read(path);
 const audit_id=sha('known-demo-'+id+'-'+series).slice(0,32);
 cards.push({audit_id,task_code:rubrics[c.task_key].code,criteria:rubrics[c.task_key].criteria,student_answer:c.answer,verifier_output:r.raw.verification.answer,human_decision:null,human_reason:null,reviewer_registry_id:null,reviewed_utc:null,prior_exposure_declared:null});
 provenance.push({audit_id,known_case:id,series,source_sha256:sha(readFileSync(path))});
}
cards.push({audit_id:sha('technical-bad-reference-demo').slice(0,32),task_code:'print("3" + "2")',criteria:['Типы значений','Склейка строк','Вывод'],student_answer:'Это строки. На экране 32.',verifier_output:'{"criterion_1":999,"criterion_2":-1,"criterion_3":1}',human_decision:null,human_reason:null,reviewer_registry_id:null,reviewed_utc:null,prior_exposure_declared:null});
provenance.push({audit_id:cards.at(-1).audit_id,technical_fixture:true,not_a_model_response:true});
const out=join(ROOT,'outputs/review-card-fragments-2026-11-11',process.argv[2]??'demo');mkdirSync(out);
const p=enrichCards({phase:'POST-LABEL DEMO: два известных авторских ответа и один технический пример; НЕ реальный пилот и НЕ новая оценка качества.',cards});
writeFileSync(join(out,'cards.json'),JSON.stringify(p,null,2)+'\n',{flag:'wx'});
writeFileSync(join(out,'CARDS.txt'),renderText(p),{flag:'wx'});
writeFileSync(join(out,'PRIVATE_DEMO_PROVENANCE.json'),JSON.stringify(provenance,null,2)+'\n',{flag:'wx'});
console.log(JSON.stringify({cards:cards.length,known_author:2,technical_fixture:1,model_calls:0}));
