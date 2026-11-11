// Offline advisory prototype. No model calls, code execution, score or gate writes.
import {segments,validateAssessment} from '../lat-ai/integration/ai/core/src/assessment-verifier.mjs';
export const SIGNAL_REVISION='lexical-review-only-v1-2026-11-11';
// Broad rubric-related vocabulary, NOT sufficient conditions for a correct answer.
export const CUES=Object.freeze({
 'L1.types.1':[/строк|\bstrings?\b/iu,/скле|соедин|конкатенац|\bconcat/iu,/вывод|экран|печата|результат/iu],
 'L1.condition.1':[/услов|истин|равн|==/iu,/ветк|\b(?:if|else)\b/iu,/вывод|экран|печата|результат/iu],
 'L2.range.1':[/значени|числ|перечисл|\brange\b/iu,/границ|включ|входит|не входит|\brange\b/iu,/строк|кажд|отдельн|\bnewline\b/iu],
 'L2.accumulator.1':[/созда|инициализ|до цикл|обнул|нул|начал/iu,/сумм|накоп|прибав|складыв/iu,/после цикл|один раз|без отступ|вне цикл/iu]
});
const base=()=>({revision:SIGNAL_REVISION,advisory_only:true,changes_score:false,changes_gate:false,does_not_clear_other_review_reasons:true,limitations:'Lexical cues can occur in negations, quoted instructions and wrong statements. Flags are questions for a human, not proof of correctness or contradiction. No flag does not establish safety.'});
export function reviewSignals({task_key,student_answer,verification}){
 if(typeof student_answer!=='string'||student_answer.length>4000)throw Error('Expected an answer string of at most 4000 UTF-16 units');
 const cues=Object.hasOwn(CUES,task_key)?CUES[task_key]:null;
 if(!cues)return {...base(),status:'unsupported_task',manual_review_suggested:null,flags:[]};
 let checked,raw;
 try{checked=validateAssessment(verification,student_answer);raw=JSON.parse(verification.answer);}
 catch(e){return {...base(),status:'technical_error',manual_review_suggested:true,flags:[{kind:'technical_invalid_verifier',error:e.message}]};}
 const parts=segments(student_answer),flags=[];
 for(let index=0;index<3;index++){
  const related=parts.map((text,id)=>({id,text})).filter(p=>cues[index].test(p.text));
  const criterion=index+1,selected=raw['criterion_'+criterion];
  if(!checked.checks[index]&&related.length)flags.push({kind:'negative_check_with_related_text',criterion,verifier_fragment_id:-1,related_fragments:related,question:'Does any of this related text actually satisfy the criterion, or is it incorrect/negated?'});
  if(checked.checks[index]&&related.length&&!cues[index].test(parts[selected]))flags.push({kind:'positive_fragment_without_related_cue',criterion,verifier_fragment_id:selected,selected_fragment:parts[selected],related_fragments:related,question:'Does the selected fragment itself support this criterion? Related vocabulary occurs elsewhere.'});
 }
 return {...base(),status:flags.length?'signals_found':'no_signal_found',manual_review_suggested:flags.length>0,flags};
}
