// Display all existing human-review cases/series, without resampling or inference.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {join} from 'node:path';
import {ROOT,enrichCards,renderText,sha} from './render-signal-review-cards.mjs';
const source=join(ROOT,'outputs/sdk-fix-and-history-scan-2026-11-11/LAT-AI-PILOT-AND-HISTORY-REVIEW/HISTORY_CASES.json');
const old=JSON.parse(readFileSync(source,'utf8'));const cards=[],mapping=[];
for(const c of old.cases)for(const r of c.raw_by_series){
 const audit_id=sha(`historical-view:${c.id}:${r.series}`).slice(0,32);
 cards.push({audit_id,task_code:c.task_code,criteria:c.criteria,student_answer:c.student_answer,verifier_output:r.verifier,human_decision:null,human_reason:null,reviewer_registry_id:null,reviewed_utc:null,prior_exposure_declared:null});
 mapping.push({audit_id,known_author_case:c.id,series:r.series});
}
const out=join(ROOT,'outputs/review-card-fragments-2026-11-11/history-cards');mkdirSync(out);
const payload=enrichCards({phase:'ИЗВЕСТНАЯ АВТОРСКАЯ ДИАГНОСТИКА: прежние 8 случаев × 3 серии. Это 8 текстов, не 24 независимые работы; НЕ реальный пилот, НЕ слепой reference. Здесь только verifier, не итог двух проходов.',cards});
writeFileSync(join(out,'cards.json'),JSON.stringify(payload,null,2)+'\n',{flag:'wx'});
writeFileSync(join(out,'CARDS.txt'),renderText(payload),{flag:'wx'});
writeFileSync(join(out,'COORDINATOR_INDEX.json'),JSON.stringify({source_sha256:sha(readFileSync(source)),mapping},null,2)+'\n',{flag:'wx'});
writeFileSync(join(out,'COORDINATOR_INDEX.txt'),'Координатору: открытая диагностика известных авторских текстов. Не выдавать в слепую фазу.\n'+mapping.map(m=>`${m.known_author_case} | серия ${m.series} | ${m.audit_id}`).join('\n')+'\n',{flag:'wx'});
console.log(JSON.stringify({known_texts:old.cases.length,display_cards:cards.length,model_calls:0}));
