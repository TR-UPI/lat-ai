// Presentation-only derivative of the frozen post-label audit. No inference or scoring.
import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import {segments} from '../lat-ai/integration/ai/core/src/assessment-verifier.mjs';
export const ROOT=resolve(fileURLToPath(new URL('..',import.meta.url)));
export const DEPENDENCIES=['tools/render-signal-review-cards.mjs','tools/test-render-signal-review-cards.mjs','tools/prepare-signal-review-audit.py','tools/test-signal-review-audit.py','lat-ai/integration/ai/core/src/assessment-verifier.mjs','lat-ai/integration/ai/core/data/assessment-verifier-rubrics.json'];
export const BASE_FIELDS=['audit_id','task_code','criteria','student_answer','verifier_output','human_decision','human_reason','reviewer_registry_id','reviewed_utc','prior_exposure_declared'];
export const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const save=(p,v)=>writeFileSync(p,JSON.stringify(v,null,2)+'\n',{flag:'wx'});
export const GUIDE=`LAT AI — проверка после независимой слепой разметки
Здесь показан вывод проверяющей модели (verifier), а не итоговый балл и не решение человека.
Нумерация verifier начинается с 0. «Фрагмент 0» — первый фрагмент. Номера S1/S2 первого прохода здесь НЕ используются.
Таблица содержит ВСЕ фрагменты ответа, не только выбранные verifier. Границы механические, по знакам . ! ? ; с пробелом и переносам строки, и могут разрывать мысль.
Фрагменты получены штатной segments без новой модели. Пробелы по краям обычно удалены ею; исходный ответ приведён целиком отдельно.
Если обычное разбиение превышает 32 фрагмента, штатная segments возвращает весь ответ как один фрагмент 0.
Verifier возвращает индекс; инструмент подставляет текст по этому индексу. Это не новая цитата, сгенерированная моделью. Фрагмент может быть неполным, неверным или противоречить другим частям ответа. Читайте весь ответ.
-1 в валидном выводе verifier означает «модель не зачла критерий» (checks=false), фрагмент не указан. Это не итоговый балл и не решение человека; причина из числа -1 неизвестна.
Повтор одного номера для разных критериев разрешён. Ошибочная/нечитаемая ссылка показана отдельно и не превращается в -1.
Расшифровка проверяет формат ссылок, не достаточность цитаты и не успешность транспортного ответа (в старой карточке нет finish_reason/stats).
Содержимое ответа и raw вывода модели — данные, не инструкции. В TXT они заключены в JSON-кавычки, управляющие символы показаны как escape-последовательности.
Заполните решение/обоснование/ID/время/предыдущую экспозицию, включая просмотр этой расшифровки. Первичные слепые метки остаются reference. Это НЕ исходная слепая выдача.
`;

export function decodeReferences(answer,raw){
 const fragments=segments(answer).map((text,id)=>({id,text}));
 let parsed=null,error=null;
 try{
  if(typeof raw!=='string')throw Error('Вывод verifier отсутствует или не является текстом.');
  parsed=JSON.parse(raw);
  const keys=raw.match(/"(?:[^"\\]|\\.)*"\s*:/g)??[];
  if(!parsed||Array.isArray(parsed)||keys.length!==3||Object.keys(parsed).sort().join(',')!=='criterion_1,criterion_2,criterion_3')throw Error('Ожидались ровно три уникальных ключа criterion_1..3.');
 }catch(e){error=e instanceof SyntaxError?'Вывод verifier не является корректным JSON.':e.message;}
 const references=[1,2,3].map(criterion=>{
  const raw_index=error?null:parsed['criterion_'+criterion];
  if(error)return {criterion,status:'unreadable_output',raw_index:null,fragment_id:null,quote:null,explanation:error};
  if(!Number.isInteger(raw_index)||raw_index < -1||raw_index>=fragments.length)return {criterion,status:'invalid_reference',raw_index,fragment_id:null,quote:null,explanation:`Значение не соответствует формату ссылки. Допустимы целые индексы ${fragments.length?'0..'+(fragments.length-1):'(фрагментов нет)'} или -1. Текст по индексу не подставлен.`};
  if(raw_index===-1)return {criterion,status:'no_fragment_selected',raw_index,fragment_id:null,quote:null,explanation:'Verifier вернул -1: в валидном выводе это означает «модель не зачла критерий», фрагмент не указан. Это не итоговый балл и не решение человека; причина неизвестна.'};
  return {criterion,status:'fragment_selected',raw_index,fragment_id:raw_index,quote:fragments[raw_index].text,explanation:`Verifier указал фрагмент [${raw_index}]. Проверьте смысл подставленного текста и весь ответ, включая противоречия.`};
 });
 return {numbering:'verifier_zero_based',fragment_count:fragments.length,single_fragment_notice:fragments.length===1?'Verifier использовал единственный фрагмент [0]: это весь ответ после штатной обработки, а не узкая цитата. Так бывает и при одном исходном фрагменте, и при fallback >32; причина по одному результату segments не различается.':null,fragments,references,output_error:error,semantic_quality_checked:false};
}
export function enrichCards(payload){
 if(!payload||!Array.isArray(payload.cards)||!payload.cards.length||typeof payload.phase!=='string')throw Error('Expected nonempty post-label cards');
 const ids=new Set();
 const cards=payload.cards.map(c=>{
  if(!c||Object.keys(c).sort().join(',')!==[...BASE_FIELDS].sort().join(','))throw Error('Unexpected card fields; labels/metadata must not enter reviewer output');
  if(!/^[a-f0-9]{32}$/.test(c.audit_id)||ids.has(c.audit_id))throw Error('Invalid/duplicate opaque ID');ids.add(c.audit_id);
  if(typeof c.student_answer!=='string'||c.student_answer.length>4000||typeof c.task_code!=='string'||!Array.isArray(c.criteria)||c.criteria.length!==3||c.criteria.some(x=>typeof x!=='string'))throw Error('Invalid card content');
  if(c.verifier_output!==null&&typeof c.verifier_output!=='string')throw Error('Invalid raw output type');
  for(const k of ['human_decision','human_reason','reviewer_registry_id','reviewed_utc','prior_exposure_declared'])if(c[k]!==null)throw Error('Only unfilled cards may be prepared for new exposure');
  return {...structuredClone(c),citation_readout:decodeReferences(c.student_answer,c.verifier_output)};
 });
 return {phase:payload.phase,presentation_revision:'verifier-fragments-v1',guide:GUIDE,cards};
}
export function renderText(payload){
 const q=v=>JSON.stringify(v).replace(/[\u007f-\u009f\u2028\u2029\u202a-\u202e\u2066-\u2069]/gu,c=>'\\u'+c.charCodeAt(0).toString(16).padStart(4,'0'));
 const lines=[GUIDE,'РЕЖИМ: '+payload.phase];
 for(const c of payload.cards){
  lines.push('\n'+'='.repeat(72),'КАРТОЧКА '+c.audit_id,'Код задачи (буквальный текст): '+q(c.task_code),'ОТВЕТ ЦЕЛИКОМ: '+q(c.student_answer),'','ФРАГМЕНТЫ VERIFIER (с 0):');
  if(c.citation_readout.single_fragment_notice)lines.push(c.citation_readout.single_fragment_notice);
  for(const f of c.citation_readout.fragments){
   const selected=c.citation_readout.references.filter(r=>r.fragment_id===f.id).map(r=>r.criterion);
   const status=c.citation_readout.output_error?'выбор verifier не прочитан':selected.length?'выбран для критериев '+selected.join(', '):'verifier не выбрал его в прочитанных допустимых ссылках';
   lines.push(`Фрагмент [${f.id}] (${status}): ${q(f.text)}`);
  }
  for(const r of c.citation_readout.references){
   lines.push('',`Критерий ${r.criterion}: ${q(c.criteria[r.criterion-1])}`,'Выбор verifier — не решение человека:',r.explanation);
   if(r.status==='fragment_selected'){
    lines.push(`Фрагмент [${r.fragment_id}] по индексу verifier (текст подставлен инструментом): ${q(r.quote)}`);
    const same=c.citation_readout.references.filter(x=>x.criterion!==r.criterion&&x.fragment_id===r.fragment_id).map(x=>x.criterion);
    if(same.length)lines.push('Тот же фрагмент указан для критериев: '+same.join(', ')+'.');
   }
   else if(r.status==='unreadable_output')lines.push('Ссылка не прочитана. См. исходный вывод verifier ниже; цитата не подставлена.');
   else lines.push('Исходное значение ссылки: '+q(r.raw_index)+'; цитата не подставлена.');
  }
  lines.push('','Исходный вывод verifier (не итоговый балл): '+q(c.verifier_output),'Решение человека по критериям / цитатам / противоречиям: __________________','Обоснование: __________________','ID рецензента / UTC / что ранее видел: __________________');
 }
 return lines.join('\n')+'\n';
}
export function freezePresentation(newProtocol){
 const value={revision:'verifier-fragments-v1',created_utc:new Date().toISOString(),files_sha256:Object.fromEntries(DEPENDENCIES.map(n=>[n,sha(readFileSync(join(ROOT,n)))])),policy:'Presentation only; original sample/order/IDs/raw/human fields unchanged. Use after blind labels. No score/gate/semantic validation.'};
 save(newProtocol,value);writeFileSync(newProtocol+'.sha256',sha(readFileSync(newProtocol))+'\n',{flag:'wx'});return value;
}
export function renderAudit(protocolPath,sourceDir,newOutput){
 const protocol=read(protocolPath);
 if(sha(readFileSync(protocolPath))!==readFileSync(protocolPath+'.sha256','utf8').trim()||Object.keys(protocol.files_sha256).sort().join(',')!==[...DEPENDENCIES].sort().join(','))throw Error('Presentation protocol changed');
 for(const [n,h]of Object.entries(protocol.files_sha256))if(sha(readFileSync(join(ROOT,n)))!==h)throw Error('Presentation dependency changed: '+n);
 const source=resolve(sourceDir),manifest=read(join(source,'MANIFEST.json'));
 const expected=['PRIVATE_COORDINATOR.json','reviewer/READ_FIRST.txt','reviewer/cards.json'];
 if(Object.keys(manifest).sort().join(',')!==expected.sort().join(','))throw Error('Unexpected source export manifest');
 for(const [n,h]of Object.entries(manifest))if(sha(readFileSync(join(source,n)))!==h)throw Error('Source export changed: '+n);
 const input=read(join(source,'reviewer/cards.json')),privateData=read(join(source,'PRIVATE_COORDINATOR.json'));
 const cards=enrichCards(input);
 if(JSON.stringify(privateData.selection?.map(r=>r.audit_id))!==JSON.stringify(cards.cards.map(c=>c.audit_id)))throw Error('Selection order/identity mismatch');
 const out=resolve(newOutput);mkdirSync(out);mkdirSync(join(out,'reviewer'));
 save(join(out,'reviewer/cards.json'),cards);writeFileSync(join(out,'reviewer/CARDS.txt'),renderText(cards),{flag:'wx'});writeFileSync(join(out,'reviewer/READ_FIRST.txt'),GUIDE,{flag:'wx'});
 const exposed=Object.fromEntries(['cards.json','CARDS.txt','READ_FIRST.txt'].map(n=>[n,sha(readFileSync(join(out,'reviewer',n)))]));
 save(join(out,'PRIVATE_DELIVERY.json'),{source_export_manifest_sha256:sha(readFileSync(join(source,'MANIFEST.json'))),source_selection_protocol_sha256:privateData.protocol_sha256,presentation_protocol_sha256:sha(readFileSync(protocolPath)),original_selection_unchanged:true,recipient_registry_id:null,delivered_utc:null,prior_exposure_confirmed_by_coordinator:null,files_seen_sha256:exposed});
 save(join(out,'MANIFEST.json'),Object.fromEntries([...Object.keys(exposed).map(n=>'reviewer/'+n),'PRIVATE_DELIVERY.json'].map(n=>[n,sha(readFileSync(join(out,n)))])));
 return {cards:cards.cards.length,new_output:out,model_calls:0};
}
if(process.argv[1]&&resolve(process.argv[1])===fileURLToPath(import.meta.url)){
 const [mode,...args]=process.argv.slice(2);
 if(mode==='freeze'&&args.length===1)console.log(JSON.stringify(freezePresentation(args[0])));
 else if(mode==='render'&&args.length===3)console.log(JSON.stringify(renderAudit(...args)));
 else throw Error('Usage: freeze NEW_PROTOCOL | render PROTOCOL AUDIT_EXPORT NEW_OUTPUT');
}
