import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {validateAssessment} from '../work/assessment-v3d-2026-11-11/integration/ai/core/src/assessment.mjs';
const base=new URL('../outputs/assessment-v3-2026-11-11/',import.meta.url),old=new URL('../outputs/assessment-evidence-v2-2026-11-11/',import.meta.url);
const cases=JSON.parse(readFileSync(new URL('regression128-with-evidence.json',base),'utf8'));
mkdirSync(new URL('candidate-d-replay/',base));let changed=0;
for(const c of cases){
 const name=(c.id.startsWith('H')?'candidate-h-holdout/':'candidate-h-replay/')+c.id+'.json';
 const previous=JSON.parse(readFileSync(new URL(name,old),'utf8'));const raw={...previous.raw,task_key:c.task_key};let result=null,error=null;
 try{result=validateAssessment(raw,c.answer);}catch(e){error=e.message;}
 if(JSON.stringify(result?.checks??null)!==JSON.stringify(previous.actual))throw Error('Unexpected decision change: '+c.id);
 if(JSON.stringify(result?.evidence)!==JSON.stringify(previous.result?.evidence))changed++;
 writeFileSync(new URL('candidate-d-replay/'+c.id+'.json',base),JSON.stringify({id:c.id,task_key:c.task_key,expected:c.expected,actual:result?.checks??null,match:JSON.stringify(result?.checks)===JSON.stringify(c.expected),ms:null,error,raw,result,provenance:'Replay of previous H recorded raw; deterministic evidence completion only, no fresh inference.'},null,2));
}
writeFileSync(new URL('candidate-d-replay/PROVENANCE.txt',base),'Replay of previous known96 H replay and H frozen32 live raw. No fresh inference. Every decision asserted identical, only evidence may expand via explicit unique context.\n');
console.log(JSON.stringify({cases:cases.length,decision_changes:0,evidence_changes:changed}));
