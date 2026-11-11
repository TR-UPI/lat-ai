import {readFileSync} from 'node:fs';import {createHash} from 'node:crypto';
import {stateFacts} from './state-facts.mjs';import {rangeFacts} from './range-facts.mjs';import {validateAnswer} from './validation.mjs';
const source=readFileSync(new URL('../data/fact-catalogue.json',import.meta.url),'utf8'),catalogue=JSON.parse(source),catalogueHash=createHash('sha256').update(source).digest('hex');
function freeze(x){if(x&&typeof x==='object'){for(const v of Object.values(x))freeze(v);Object.freeze(x);}return x;}freeze(catalogue);
export function buildFactLedger(req){
 if(!['L1','L2'].includes(req?.lesson)||typeof req.message!=='string'||req.message.length>4000)throw Error('fact request');
 const ledgerId=createHash('sha256').update(JSON.stringify({lesson:req.lesson,topic:req.topic??'',question:req.message,catalogueHash})).digest('hex');
 const facts=[],add=(kind,scope,text,data,provenance)=>facts.push({id:ledgerId.slice(0,16)+'_'+facts.length,kind,scope,text,...(data?{data}:{}),provenance});
 const cat={method:'authored_rule',source:'fact-catalogue.json',source_sha256:catalogueHash,teacher_approved:false};
 const arithmetic={method:'closed_integer_analyzer',assumption:'standard_unshadowed_range_and_print; defined_integer_operands; only_provided_code'};
 add('catalogue_scope','lesson_coverage_not_student_mastery',catalogue.scope[req.lesson],null,cat);
 const allowed=req.lesson==='L1'?['types','строки','условия','отступы']:Object.keys(catalogue.topics);
 if(allowed.includes(req.topic))for(const t of catalogue.topics[req.topic])add('catalogue_rule','general_rule_not_a_diagnosis',t,null,cat);
 add('catalogue_rule','missing_information',catalogue.diagnosis,null,cat);
 if(req.lesson==='L2'){
  if(['отступы','range'].includes(req.topic))add('catalogue_rule','loop_execution_with_defined_arguments',catalogue.L2_loop,null,cat);
  for(const r of rangeFacts(req.message)){
   const text=r.error?`Для стандартного ${r.expression} создание диапазона вызывает ValueError до итераций.`:`Для стандартного ${r.expression} значения по порядку: ${r.values.length?r.values.join(', '):'нет значений'}. Шаг ${r.step}; условие включения значения: ${r.allowed_condition}. Это факт о выражении range, не об исполнении всей программы.`;
   add('computed_range','expression_only_not_program_execution',text,r,arithmetic);
  }
  const s=stateFacts(req.message,{includeStructure:true});
  if(s.trace){
   const t=s.trace;
   add('computed_program','provided_code_only',`В показанном полностью разобранном блоке со свежими целочисленными значениями команды print выведут по порядку: ${t.output.length?t.output.join(', '):'ничего'}. Значения после этого блока: ${Object.entries(t.final).map(([k,v])=>`${k}=${v}`).join(', ')||'нет определённых переменных'}. Это не результат непоказанного окружающего кода.`,{output:t.output,final:t.final,program:t.structure},arithmetic);
   for(const n of t.structure.filter(n=>n.variable))add('computed_loop_binding','provided_code_only',`В показанном цикле перед каждым выполнением тела for задаёт ${n.variable} очередное значение из ${JSON.stringify(n.values)}; затем исполняет команды тела.`,n,arithmetic);
  }else{
   const meanings={replace_with_constant:'заменяет прежнее значение константой',replace_with_current_value:'заменяет прежнее значение текущим значением правой части',add_to_previous:'прибавляет указанное слагаемое к прежнему значению',subtract_from_previous:'вычитает указанную величину из прежнего значения',replace_with_expression:'вычисляет правую часть и сохраняет результат слева'};
   for(const a of s.assignments)add('conditional_assignment','one_assignment_only',`При определённых целочисленных операндах команда ${a.expression} ${meanings[a.effect]}; это одна команда, не итог всей программы.`,a,{...arithmetic,assumption:'defined_integer_operands; this_assignment_executes'});
   if(s.sequence)add('computed_pair','conditional_sequence_only',`Если указанные две команды выполняются подряд с определёнными целыми операндами, сразу после пары ${s.sequence.target}=${s.sequence.final_expression}. Это результат только этой пары, не всей программы; неизвестные переменные в выражении не получили численных значений.`,s.sequence,{...arithmetic,assumption:s.sequence.condition});
   add('analysis_limit','analyzer_did_not_establish_whole_program_result','Этот анализ не установил итог всей программы. Неподдерживаемый или неполный фрагмент не даёт вычисленного результата; отсутствие результата анализатора само по себе не доказывает ошибку Python.',null,{method:'analysis_boundary'});
  }
 }
 return freeze({ledger_id:ledgerId,lesson:req.lesson,facts});
}
export function separatedSchema(ledger,lesson){return {type:'object',properties:{explanation:{type:'string',minLength:10,maxLength:900},fact_ids:{type:'array',items:{type:'string',enum:ledger.facts.map(f=>f.id)},minItems:1,maxItems:3},source_ids:{type:'array',items:{type:'string',enum:[lesson]},minItems:1,maxItems:1}},required:['explanation','fact_ids','source_ids'],additionalProperties:false};}
export function validateSeparated(raw,lesson,ledger,limit=192){
 if(typeof raw?.answer!=='string'||raw.answer.length>5000)throw Error('answer size');
 const parsed=JSON.parse(raw.answer),keys=[...raw.answer.matchAll(/"(?:[^"\\]|\\.)*"\s*:/g)].map(m=>JSON.parse(m[0].slice(0,m[0].lastIndexOf(':')).trim()));
 if(!parsed||Array.isArray(parsed)||Object.keys(parsed).sort().join(',')!=='explanation,fact_ids,source_ids'||keys.length!==3||new Set(keys).size!==3)throw Error('separated schema');
 if(ledger.lesson!==lesson||!Array.isArray(parsed.fact_ids)||parsed.fact_ids.length<1||parsed.fact_ids.length>3||new Set(parsed.fact_ids).size!==parsed.fact_ids.length||parsed.fact_ids.some(id=>!ledger.facts.some(f=>f.id===id)))throw Error('fact references');
 // Reuse the existing text/metadata safety checks on the parsed text only.
 // This is validation, not repair: raw.answer stays byte-for-byte in logs;
 // absent/malformed schema/IDs are rejected above, never synthesized.
 const checked=validateAnswer({...raw,answer:JSON.stringify({text:parsed.explanation,source_ids:parsed.source_ids})},lesson,limit);
 return {facts:structuredClone(ledger.facts),ledger_id:ledger.ledger_id,explanation:{text:checked.text,fact_ids:[...parsed.fact_ids],verification:'unverified'},source_ids:checked.source_ids};
}
export function renderSeparated(result){return 'Факты и границы применимости:\n'+result.facts.map(f=>f.text).join('\n')+'\nПояснение модели (смысл автоматически не проверен):\n'+result.explanation.text;}
