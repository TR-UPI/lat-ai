// Context completion only: never creates or changes a criterion decision.
// These two compound requirements belong to the existing mapped if/else task.
export function completeEvidenceContext(assessment,records,fragments,answer,taskKey){
 if(taskKey!=='L1.condition.1')return assessment;
 let cursor=0;const parts=fragments.map(text=>{const start=answer.indexOf(text,cursor);if(start<0)throw Error('evidence offset');cursor=start+text.length;return {text,start,end:cursor};});
 const evidence=[...assessment.evidence];
 // Accept explicit assignment notation, but not comparisons or prefixes of other numbers.
 const requirements=[[/\bx\s*(?::=|:|=(?!=)|равен|равно|содержит)\s*2\b(?![.,]\d)/iu],[/\bif\b/iu,/\belse\b/iu],[]];
 for(let i=0;i<3;i++){
  if(!assessment.checks[i])continue;
  let first=Number(records['criterion_'+(i+1)].start.slice(1))-1,last=Number(records['criterion_'+(i+1)].end.slice(1))-1;
  for(const pattern of requirements[i]){
   if(pattern.test(answer.slice(parts[first].start,parts[last].end)))continue;
   const matches=parts.map((part,index)=>pattern.test(part.text)?index:null).filter(index=>index!==null);
   // Ambiguous context is not guessed; no whole-answer fallback.
   if(matches.length===1){first=Math.min(first,matches[0]);last=Math.max(last,matches[0]);}
  }
  evidence[i]=answer.slice(parts[first].start,parts[last].end);
 }
 return {...assessment,evidence};
}
