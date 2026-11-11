import {readFileSync,writeFileSync,readdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=resolve(import.meta.dirname,'..'),out=join(root,'outputs/u02-investigation-2026-11-11');
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const current=await import(pathToFileURL(join(root,'lat-ai/integration/ai/core/src/assessment.mjs')));
const historical=await import(pathToFileURL(join(root,'work/assessment-v3d-2026-11-11/integration/ai/core/src/assessment.mjs')));
const offline=read(join(out,'offline-analysis.json'));const sourceBefore=read(join(root,'outputs/ai-pilot-integrity-2026-11-11/source-and-package-audit.json')).after_sha256;
for(const [name,expected] of Object.entries(sourceBefore))assert.equal(sha(readFileSync(join(root,'lat-ai',name))),expected,'Project source changed: '+name);
const configs=[],targets=[],assessments=[];let sessions=0;
for(const [name,base] of [['fresh_loads',out],['B-A-B',join(out,'crossover')],['A-B-A',join(out,'reverse-crossover')]]){
 const plan=read(join(base,'order-protocol.json')),summary=read(join(base,'order-live/summary.json'));assert.equal(summary.complete,true);assert.equal(summary.error,null);
 assert.equal(summary.protocol_sha256,sha(readFileSync(join(base,'order-protocol.json'))));
 for(const session of plan.sessions){
  const dir=join(base,'order-live',session.id),terminal=read(join(dir,'summary.json'));
  assert.equal(terminal.retirement_proven,true);assert.equal(terminal.error,null);sessions++;
  const meta=read(join(dir,'loaded-model.json'));assert.equal(meta.models.length,1);configs.push({session:session.id,model_key:meta.models[0].key,quantization:meta.models[0].quantization,config:meta.models[0].loaded_instances[0].config});
  const files=readdirSync(dir).filter(f=>/^(?:\d+-)?(?:U02|N05|U15|V11)\.json$/.test(f));assert.equal(files.length,session.order.length);
  for(const file of files){
   const row=read(join(dir,file));assessments.push({cohort:name,session:session.id,id:row.id,actual:row.actual,ms:row.ms});
   assert.equal(row.calls.length,2);for(const call of row.calls){assert.equal(call.http_status,200);assert.equal(call.response_body.choices[0].finish_reason,'stop');}
   if(row.id!=='U02')continue;
   const replay=validator=>{try{return {result:validator(row.raw,offline.answer),error:null};}catch(e){return {result:null,error:e.message};}};
   assert.deepEqual(replay(current.validateAssessment),replay(historical.validateAssessment),'Validators differ on U02');
   assert.deepEqual(row.verification_checks,[false,true,true]);assert.equal(row.answer_sha256,offline.answer_sha256);
   assert.deepEqual(row.calls.map(c=>c.normalized_sha256),offline.request_hashes);
   targets.push({cohort:name,session:session.id,file:file,actual:row.actual,candidate:row.candidate_checks,verification:row.verification_checks,proposal_ms:row.calls[0].ms,verification_ms:row.calls[1].ms,model_instance:row.calls[0].request_body.model,response_ids:row.calls.map(c=>c.response_body.id),evidence:row.result?.evidence??null,path:join(dir,file)});
  }
 }
}
assert.equal(sessions,8);assert.equal(assessments.length,27);assert.equal(targets.length,12);
assert.ok(configs.every(c=>JSON.stringify(c.config)===JSON.stringify(configs[0].config)));
const fresh=targets.filter(r=>r.cohort==='fresh_loads').sort((a,b)=>a.session.localeCompare(b.session));
const cross=Object.fromEntries(['B-A-B','A-B-A'].map(name=>[name,targets.filter(r=>r.cohort===name).sort((a,b)=>a.file.localeCompare(b.file))]));
const verdict=actual=>actual===null?'refused':JSON.stringify(actual)==='[false,true,true]'?'undergraded':'other';
const result={source_files_unchanged:Object.keys(sourceBefore).length,prompts_and_rubrics_unchanged:true,sessions,assessments:assessments.length,chat_completion_posts:assessments.length*2,target_U02_observations:targets.length,fresh_loads:fresh.map(r=>({session:r.session,outcome:verdict(r.actual),candidate:r.candidate,verification:r.verification})),within_instance:Object.fromEntries(Object.entries(cross).map(([name,rows])=>[name,rows.map(r=>({step:r.file,outcome:verdict(r.actual),model_instance:r.model_instance}))])),normalized_payloads_equal:true,old_and_current_validator_results_equal:true,loaded_configs_equal:true,loaded_config:configs[0],targets,all_assessments:assessments,limits:'Behavioral dependency on prior inference and persistence within a loaded instance. Does not isolate cache/checkpoint implementation from numerical effects. Historical GGUF hash unavailable; current GGUF fingerprint recorded. Known synthetic examples, not general quality validation.'};
writeFileSync(join(out,'investigation-summary.json'),JSON.stringify(result,null,2)+'\n',{flag:'wx'});console.log(JSON.stringify({sessions,assessments:assessments.length,fresh_loads:result.fresh_loads,within_instance:result.within_instance}));
