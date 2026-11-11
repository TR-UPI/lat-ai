import {readFileSync,mkdirSync,writeFileSync,copyFileSync} from 'node:fs';
import {validateAssessment} from '../work/assessment-evidence-v2h-2026-11-11/integration/ai/core/src/assessment.mjs';
const base=new URL('../outputs/assessment-evidence-v2-2026-11-11/',import.meta.url);
const read=name=>JSON.parse(readFileSync(new URL(name,base),'utf8'));
const cases=read('regression96.json'),probe=new Set(read('probe16.json').map(c=>c.id));
mkdirSync(new URL('candidate-g-regression/',base));mkdirSync(new URL('candidate-h-replay/',base));
for(const c of cases){
 const origin=(probe.has(c.id)?'candidate-g-probe/':'candidate-g-remaining/')+c.id+'.json';
 const first=read(origin),second=read('baseline96/'+c.id+'.json');
 copyFileSync(new URL(origin,base),new URL('candidate-g-regression/'+c.id+'.json',base));
 const raw={candidate:first.raw,verification:second.raw};let result=null,error=null;
 try{result=validateAssessment(raw,c.answer);}catch(e){error=e.message;}
 const row={id:c.id,expected:c.expected,actual:result?.checks??null,match:JSON.stringify(result?.checks)===JSON.stringify(c.expected),ms:null,error,raw,result,provenance:{mode:'deterministic replay, no new inference',candidate:origin,verification:'baseline96/'+c.id+'.json'}};
 writeFileSync(new URL('candidate-h-replay/'+c.id+'.json',base),JSON.stringify(row,null,2));
}
writeFileSync(new URL('candidate-g-regression/PROVENANCE.txt',base),'96 unique cases = 16 diagnostic cases + 80 remaining cases, with the same frozen G source. One G result per case; no cherry-picking. Live logs remain in the two original run folders.\n');
writeFileSync(new URL('candidate-h-replay/PROVENANCE.txt',base),'Offline validation of the agreement gate using recorded G proposal and recorded evidence-v1 response for the same case. This is not a fresh live evaluation of H. No H latency is inferred. New holdout32 will execute both prompts live.\n');
console.log(JSON.stringify({merged_live_g:cases.length,offline_h_replays:cases.length}));
