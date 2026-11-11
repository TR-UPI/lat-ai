import {readFileSync,writeFileSync,mkdirSync,readdirSync,lstatSync} from 'node:fs';
import {resolve,join,basename} from 'node:path';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';

export const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
const read=path=>JSON.parse(readFileSync(path,'utf8').replace(/^\uFEFF/,''));
const save=(path,value)=>writeFileSync(path,JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const required=['responses.frozen.json','review-A.frozen.json','review-B.frozen.json','adjudication.frozen.json','primary-cases.json','repeat1.json','repeat2.json','repeat3.json'];
const equal=(a,b)=>JSON.stringify(a)===JSON.stringify(b);
const toolNames=['frozen-assessment-run.mjs','prepare-assessment-run.mjs','run-frozen-assessment.mjs','analyze-frozen-pilot.py','assessment-statistics.py'];
const toolHashes=()=>Object.fromEntries(toolNames.map(name=>[name,hash(readFileSync(join(import.meta.dirname,name)))]));
export function sourceHashes(root){
 const result={};
 function walk(relative){
  const path=join(root,relative);if(lstatSync(path).isSymbolicLink())throw Error('Symlink in frozen source');
  if(lstatSync(path).isDirectory()){for(const n of readdirSync(path).sort())walk(relative+'/'+n);}
  else result[relative]=hash(readFileSync(path));
 }
 for(const folder of ['integration/ai/core/src','integration/ai/core/data'])walk(folder);
 return result;
}
function checkCases(cases,rubrics){
 if(!Array.isArray(cases)||!cases.length)throw Error('Empty cases');
 const ids=new Set();
 for(const c of cases){
  if(typeof c.id!=='string'||!/^[-a-zA-Z0-9.]+$/.test(c.id)||ids.has(c.id)||typeof c.answer!=='string'||!c.answer.trim()||c.answer.length>4000||!Object.hasOwn(rubrics.tasks,c.task_key)||!Array.isArray(c.expected)||c.expected.length!==3||c.expected.some(x=>typeof x!=='boolean'))throw Error('Invalid cases');
  ids.add(c.id);
 }
}
function frozenDataset(folder,rubrics){
 const manifest=read(join(folder,'freeze.json'));
 if(!['real_student','synthetic_smoke'].includes(manifest.data_origin)||!equal(Object.keys(manifest.files_sha256??{}).sort(),[...required].sort()))throw Error('Unsupported freeze manifest');
 const hashes={'freeze.json':hash(readFileSync(join(folder,'freeze.json')))};
 for(const name of required){
  const value=hash(readFileSync(join(folder,name)));if(value!==manifest.files_sha256[name])throw Error('Frozen dataset changed: '+name);hashes[name]=value;
 }
 const primary=read(join(folder,'primary-cases.json'));checkCases(primary,rubrics);
 if(manifest.unique_cases!==primary.length||manifest.sha256!==hashes['primary-cases.json'])throw Error('Primary manifest mismatch');
 const series=[];
 for(let n=1;n<=3;n++){
  const cases=read(join(folder,'repeat'+n+'.json'));checkCases(cases,rubrics);
  if(cases.length!==primary.length)throw Error('Series size mismatch');
  for(let i=0;i<cases.length;i++){
   const c=cases[i],p=primary[i];
   if(c.id!==`R${n}-${p.id}`||c.source_id!==p.id||c.repeat!==n||!equal({...c,id:p.id,source_id:undefined,repeat:undefined},{...p,source_id:undefined,repeat:undefined}))throw Error('Series differs from primary/order');
  }
  series.push(cases);
 }
 return {manifest,hashes,series};
}
export function freezeRun(sourceRoot,frozenDir,reviewedRubrics,settings,newPlan){
 const root=resolve(sourceRoot),folder=resolve(frozenDir);
 const rubricPath=join(root,'integration/ai/core/data/assessment-rubrics.json');
 if(hash(readFileSync(rubricPath))!==hash(readFileSync(reviewedRubrics)))throw Error('Reviewed rubric differs from executable rubric');
 if(settings?.model_key!=='qwen3.5-9b'||typeof settings.environment_note!=='string'||!settings.environment_note.trim()||typeof settings.model_identity_note!=='string'||!settings.model_identity_note.trim())throw Error('Record model identity and local environment; only current model is supported');
 const dataset=frozenDataset(folder,read(rubricPath));
 const plan={format:1,created_utc:new Date().toISOString(),source_root:root,frozen_dir:folder,data_origin:dataset.manifest.data_origin,node_version:process.version,platform:process.platform,arch:process.arch,source_sha256:sourceHashes(root),dataset_sha256:dataset.hashes,config:{model_key:settings.model_key,context_length:8192,parallel:1,budget_ms:60000,max_tokens:192},declarations:{environment_note:settings.environment_note,model_identity_note:settings.model_identity_note,limitation:'Operator declarations, not independent proof of model weights or hardware.'},primary_series:1,series:[1,2,3]};
 plan.tool_sha256=toolHashes();save(newPlan,plan);writeFileSync(newPlan+'.sha256',hash(readFileSync(newPlan))+'\n',{flag:'wx'});return plan;
}
export function verifyRun(planFile,series){
 if(![1,2,3].includes(series))throw Error('Series must be 1, 2 or 3');
 const bytes=readFileSync(planFile);if(hash(bytes)!==readFileSync(planFile+'.sha256','utf8').trim())throw Error('Plan hash mismatch');
 const plan=read(planFile);
 if(plan.format!==1||plan.primary_series!==1||!equal(plan.series,[1,2,3])||plan.node_version!==process.version||plan.platform!==process.platform||plan.arch!==process.arch)throw Error('Plan/runtime mismatch');
 if(!equal(plan.tool_sha256,toolHashes()))throw Error('Evaluation tools changed since freeze');
 if(!equal(plan.config,{model_key:'qwen3.5-9b',context_length:8192,parallel:1,budget_ms:60000,max_tokens:192}))throw Error('Unsupported frozen config');
 if(!equal(sourceHashes(plan.source_root),plan.source_sha256))throw Error('AI source changed since freeze');
 const rubrics=read(join(plan.source_root,'integration/ai/core/data/assessment-rubrics.json'));
 const dataset=frozenDataset(plan.frozen_dir,rubrics);
 if(!equal(dataset.hashes,plan.dataset_sha256)||plan.data_origin!==dataset.manifest.data_origin)throw Error('Frozen inputs changed since plan');
 return {plan,cases:dataset.series[series-1],plan_sha256:hash(bytes)};
}
export async function runSeries(planFile,series,outDir,deps={}){
 // All provenance checks precede imports, model loading and directory creation.
 const verified=verifyRun(planFile,series),{plan,cases,plan_sha256}=verified;
 const dir=resolve(outDir);mkdirSync(dir);
 save(join(dir,'provenance.json'),{plan_sha256,series,primary:series===1,data_origin:plan.data_origin,config:plan.config,node_version:process.version,started_utc:new Date().toISOString()});
 const events=[];let stages=[],model,rows=[],failure=null,retired=false;
 const event=value=>{events.push({at:new Date().toISOString(),...value});writeFileSync(join(dir,'events.jsonl'),events.map(e=>JSON.stringify(e)).join('\n')+'\n');};
 const fetchImpl=deps.fetchImpl??fetch;
 const measuredFetch=async(url,options)=>{
  if(options?.method!=='POST'||!String(url).endsWith('/v1/chat/completions'))return fetchImpl(url,options);
  const start=performance.now(),stage=stages.length===0?'proposal':'verification';
  let response;
  try{response=await fetchImpl(url,options);}catch(error){stages.push({stage,ms:performance.now()-start,terminal_body:false,transport_error:true});throw error;}
  if(!response.ok){stages.push({stage,ms:performance.now()-start,http_status:response.status,terminal_body:false});return response;}
  return {ok:true,text:async()=>{let terminal=false;try{const text=await response.text();terminal=true;return text;}finally{stages.push({stage,ms:performance.now()-start,http_status:response.status,terminal_body:terminal});}}};
 };
 try{
  let loadModel=deps.loadModel,validate=deps.validate;
  if(!loadModel){const {LocalModel}=await import(pathToFileURL(join(plan.source_root,'integration/ai/core/src/local-model.mjs')));loadModel=options=>LocalModel.loadOwned(options);}
  if(!validate){({validateAssessment:validate}=await import(pathToFileURL(join(plan.source_root,'integration/ai/core/src/assessment.mjs'))));}
  model=await loadModel({modelKey:plan.config.model_key,contextLength:plan.config.context_length,fetchImpl:measuredFetch,lockPath:join(dir,'model.lock'),recoveryLog:value=>event({event:'recovery',detail:value})});
  event({event:'loaded',instance:model.model});
  for(const c of cases){
   // Detect on-disk changes during a run as well. Never silently use another revision.
   verifyRun(planFile,series);stages=[];const started=performance.now();
   let raw,result=null,error=null;
   try{raw=await model.generate({role:'assess',lesson:c.task_key.slice(0,2),message:c.answer,assessment:{task_key:c.task_key}},{signal:AbortSignal.timeout(plan.config.budget_ms),maxTokens:plan.config.max_tokens});}
   catch(e){
    const row={id:c.id,source_id:c.source_id,task_key:c.task_key,expected:c.expected,actual:null,status:'transport_unknown',diagnosis:'transport_unknown',error:e.message,ms:performance.now()-started,stages:[...stages],result:null};
    rows.push(row);save(join(dir,c.id+'.json'),row);event({event:'stopped_unknown',id:c.id,error:e.message});throw e;
   }
   try{result=validate(raw,c.answer);}catch(e){error=e.message;}
   let counters=[];try{counters=Object.entries(JSON.parse(raw.candidate.answer)).filter(([,v])=>v?.counter!=null).map(([criterion,v])=>({criterion,fragment:v.counter}));}catch{}
   const flags=[...(counters.length?['model_reports_contradiction']:[]),...(error?[error==='assessment disagreement'?'review_disagreement':'technical_invalid_output']:[])];
   const row={id:c.id,source_id:c.source_id,task_key:c.task_key,expected:c.expected,actual:result?.checks??null,status:result?'assessed':'refused',diagnosis:error==='assessment disagreement'?'review_disagreement':error?'technical_invalid_output':counters.length?'model_reports_contradiction':'assessed',diagnostic_flags:flags,counters,error,raw,result,ms:performance.now()-started,stages:[...stages]};
   rows.push(row);save(join(dir,c.id+'.json'),row);event({event:'case',id:c.id,status:row.status});
  }
  verifyRun(planFile,series);
 }catch(e){failure=e.message;event({event:'run_error',error:failure});}
 finally{
  if(model){try{if(model.state.phase==='idle'){model.coordinator.begin();model.quarantineActive();}retired=await model.retireOwnedInstance();event({event:'retired',proven:retired,instance:model.model});}catch(e){event({event:'retirement_error',error:e.message});failure??='Retirement failed: '+e.message;}}
  if(model&&!retired)failure??='Owned model retirement not proven';
 }
 const completed=rows.filter(r=>r.status!=='transport_unknown');
 const summary={format:1,plan_sha256,series,primary:series===1,status:failure?'incomplete':'complete',failure,planned:cases.length,attempted:rows.length,completed:completed.length,not_run:cases.slice(rows.length).map(c=>c.id),transport_unknown:rows.filter(r=>r.status==='transport_unknown').map(c=>c.id),correct:completed.filter(r=>equal(r.actual,r.expected)).length,wrong:completed.filter(r=>r.actual!==null&&!equal(r.actual,r.expected)).length,refusals:completed.filter(r=>r.actual===null).length,retirement_proven:retired,retry_performed:false};
 // Bind every result to the report so comparison cannot silently read edited rows.
 summary.result_sha256=Object.fromEntries(rows.map(r=>[r.id+'.json',hash(readFileSync(join(dir,r.id+'.json')))]));
 save(join(dir,'summary.json'),summary);event({event:'summary',...summary});return summary;
}
