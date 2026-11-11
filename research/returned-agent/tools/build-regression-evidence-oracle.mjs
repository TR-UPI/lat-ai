import {readFileSync,writeFileSync} from 'node:fs';
import {segments} from '../work/assessment-evidence-v2b-2026-11-11/integration/ai/core/src/assessment.mjs';
const base=new URL('../outputs/assessment-evidence-v2-2026-11-11/',import.meta.url);
const cases=JSON.parse(readFileSync(new URL('regression96.json',base),'utf8'));
const spans={
 'L1.types.1-1':'1 1 2','L1.types.1-3':'- - 1',
 'L1.condition.1-1':'1 2 2','L1.condition.1-3':'- - 1',
 'L2.range.1-1':'1 2 3','L2.range.1-3':'- 1 -',
 'L2.accumulator.1-1':'1 2 3','L2.accumulator.1-3':'1 - -',
 N01:'1 2 3',N02:'1 2 2',N03:'1 2-3 3',N04:'1 2 3',N05:'1 2-3 2',N06:'1 2 3',N07:'1 2 -',N08:'1 2 -',N09:'- - 1',N14:'- 1 2',N15:'1 - 2',N16:'1 2 -',N17:'1 2 3',N18:'1 2 -',N19:'- - 1',N20:'1 2 3',N21:'1 2 -',N22:'1 2 3',N23:'1 2 3'
};
const u=`1 2 3
2 2 1
1 2 3
1 2 3
1 - -
1 1 -
1 - 2
- - 1
- - -
- - -
- - -
1 1 1
1 2 3
1 1 1
1-2 3-4 5
1 2 3
1-2 - -
- 1-2 -
1 - 2
1 2 -
- - -
1 2 -
- - -
1 1 1
1 2 3
1 2 1
1 2 3
1 2 3
1 - -
- 1-2 -
1 - 2
1 2 -
- - -
1 1 -
- - -
1 1 2
1 3 4
2 3 1
1 2-4 5
1 2 3
1 - -
- 1 -
1 - 2
- 1 2
- - -
1 2 -
- - -
1 2 3`.split('\n');
u.forEach((s,i)=>spans['U'+String(i+1).padStart(2,'0')]=s);
const oracle=cases.map(c=>{
 const parts=segments(c.answer),tokens=(spans[c.id]??'- - -').split(' ');
 const anchors=tokens.map((t,i)=>{
  if(t==='-'){if(c.expected[i])throw Error('Missing positive label '+c.id);return [];}
  if(!c.expected[i])throw Error('Unexpected positive '+c.id);
  const [a,b=a]=t.split('-').map(Number);if(a<1||b>parts.length||a>b)throw Error('Range '+c.id);
  return parts.slice(a-1,b);
 });
 return {id:c.id,required_fragments:anchors};
});
writeFileSync(new URL('regression-evidence-oracle.json',base),JSON.stringify({method:'Author-labelled minimum sufficient original fragments. Every required fragment must occur in the returned quote. Longer continuous quotes are accepted and their length is measured. This controlled coverage oracle is not a general entailment proof.',cases:oracle},null,2));
console.log(JSON.stringify({cases:oracle.length,positive_criteria:oracle.flatMap(x=>x.required_fragments).filter(x=>x.length).length}));
