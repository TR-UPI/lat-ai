// Closed arithmetic on small literal built-in range calls, NEVER eval/exec.
// These facts concern the expression, not surrounding code or shadowed names.
export function rangeFacts(text){
 if(typeof text!=='string'||text.length>4000)return [];
 if(/\brange[ \t]*=|\bdef[ \t]+range\b/u.test(text))return [];
 const matches=[...text.matchAll(/(?<![\p{ID_Continue}.])range[ \t\r\n]*\(([^()]*)\)/gu)];if(matches.length>3)return [];
 const result=[];
 for(const m of matches){
  if(text.slice(0,m.index).replace(/[ \t\r\n]+$/,'').endsWith('.')||/[^\d,+\- \t\r\n]/.test(m[1]))continue;
  const tokens=m[1].split(',').map(x=>x.trim());
  if(tokens.length<1||tokens.length>3||tokens.some(t=>!/^[-+]?(?:0|[1-9]\d*)$/.test(t)))continue;
  const args=tokens.map(Number);if(args.some(n=>!Number.isSafeInteger(n)||Math.abs(n)>1000000))continue;
  const start=args.length===1?0:args[0],stop=args.length===1?args[0]:args[1],step=args[2]??1;
  const base={expression:m[0],assumption:'standard_unshadowed_Python_range',scope:'expression_only_not_program_execution',start,stop,step};
  if(step===0){result.push({...base,error:'ValueError',stage:'range_construction_before_iterations'});continue;}
  const count=Math.max(0,Math.ceil((stop-start)/step));if(count>20)continue;
  const values=Array.from({length:count},(_,k)=>start+k*step),next=start+count*step;
  result.push({...base,values,stop_excluded:true,allowed_condition:step>0?'value < stop':'value > stop',next_candidate:next,next_relation_to_stop:next===stop?'equal':next<stop?'less':'greater'});
 }
 return result;
}
