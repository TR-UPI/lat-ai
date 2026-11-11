import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {makeInput,parseAnswer} from './eval-lib.mjs';
const root=new URL('./',import.meta.url),[model,split,version='v1']=process.argv.slice(2);
if(!/^shag-gold-(4b|9b)$/.test(model||'')||!['dev','holdout'].includes(split)||!/^v[12]$/.test(version))throw Error('Explicit known model/split/version required');
const suiteText=await readFile(new URL('suite.json',root),'utf8'),suite=JSON.parse(suiteText),protocol=JSON.parse(await readFile(new URL('protocol.json',root),'utf8'));
const prompt=await readFile(new URL(`prompt-${version}.txt`,root),'utf8');
const hash=s=>createHash('sha256').update(s).digest('hex');
if(hash(suiteText)!==protocol.sha256['suite.json'])throw Error('Suite changed');
if(version==='v1'&&hash(prompt)!==protocol.sha256['prompt-v1.txt'])throw Error('Prompt changed');
await mkdir(new URL('results/',root),{recursive:true});
const dest=new URL(`results/${model}-${split}-${version}.json`,root);
try{await readFile(dest);throw Error('Existing result must not be overwritten')}catch(e){if(e.code!=='ENOENT')throw e}
if(split==='holdout'){
 const freeze=JSON.parse(await readFile(new URL('freeze.json',root),'utf8'));
 if(freeze.prompt_sha256!==hash(prompt)||freeze.suite_sha256!==hash(suiteText))throw Error('Holdout requires frozen prompt and suite');
}
const config={model,temperature:.2,top_p:.8,top_k:20,min_p:0,repeat_penalty:1,max_output_tokens:1400,reasoning:'off',store:false,stream:false,integrations:[],system_prompt:prompt};
const report={model,split,version,startedAt:new Date().toISOString(),suite_sha256:hash(suiteText),prompt_sha256:hash(prompt),config,protocol,planned:suite.cases.filter(c=>c.split===split).length*(split==='dev'?1:2),answers:[]};
await writeFile(dest,JSON.stringify(report,null,2),'utf8');
async function request(input){
 const t=performance.now();
 try{
 const r=await fetch('http://127.0.0.1:1234/api/v1/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({...config,input}),signal:AbortSignal.timeout(120000)});
 const data=await r.json();
 if(!r.ok)throw Error(`HTTP ${r.status}: ${JSON.stringify(data)}`);
 return {...parseAnswer(data,1400),raw:data,latencyMs:Math.round(performance.now()-t)};
 }catch(e){return {error:e.message,latencyMs:Math.round(performance.now()-t),complete:false,jsonValid:false}}
}
report.warmup=await request('ROLE: explain\nTASK: Ответь JSON {"text":"Готов","sources":[]}');
if(report.warmup.error){await writeFile(dest,JSON.stringify(report,null,2));throw Error('Warmup failed '+report.warmup.error)}
for(let rep=1;rep<=(split==='dev'?1:2);rep++){
 let cases=suite.cases.filter(c=>c.split===split);if(rep===2)cases.reverse();
 for(const c of cases){const input=makeInput(suite,c),result=await request(input);report.answers.push({id:c.id,role:c.role,rep,input,...result});await writeFile(dest,JSON.stringify(report,null,2),'utf8');console.log(`${model} ${split} ${c.id} r${rep} ${result.error||(!result.jsonValid?'INVALID JSON':!result.complete?'INCOMPLETE':'OK')} ${result.latencyMs}ms`);}
}
report.finishedAt=new Date().toISOString();await writeFile(dest,JSON.stringify(report,null,2),'utf8');
console.log('Completed '+report.answers.length+'/'+report.planned+' responses; semantic scoring pending.');
