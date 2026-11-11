import {analysisText,contextForModel} from './code-context.mjs';
import {stateFacts} from './state-facts.mjs';import {rangeFacts} from './range-facts.mjs';
export function compactFacts(text){
 const s=stateFacts(text,{includeStructure:true});
 if(s.trace){const t=s.trace;return {scope:t.scope,assumption:t.assumption,program:t.structure,output:t.output,final:t.final};}
 return {program_result:'unknown',assumption:'defined_integer_operands',commands:s.assignments.map(a=>({code:a.expression,effect:a.effect})),...(s.sequence?{sequence:s.sequence}:{})};
}
export function modelInput(req,tuning){
 const context=contextForModel(req),text=analysisText(req);
 const base={lesson_id:req.lesson,lesson:tuning.documents[req.lesson],question:req.message,...(context?{editor_context:context}:{})};
 const ranges=tuning.groundLiteralRanges===true&&req.lesson==='L2'?rangeFacts(text):[];
 if(tuning.compactContext===true){
  const facts=tuning.groundState===true&&req.lesson==='L2'?compactFacts(text):null;
  const rangeContext=tuning.compactRanges===false?ranges:ranges.map(r=>r.error?{expression:r.expression,assumption:r.assumption,scope:r.scope,error:r.error}:{expression:r.expression,assumption:r.assumption,scope:r.scope,values:r.values,stop_excluded:true});
  return {...base,...(ranges.length?{verified_range_facts:rangeContext}:{}),...(facts?{facts}:{})};
 }
 const state=tuning.groundState===true&&req.lesson==='L2'?stateFacts(text):null;
 return {...base,...(ranges.length?{verified_range_facts:ranges}:{}),...(state?{verified_state_facts:state}:{})};
}
