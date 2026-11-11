import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=resolve(import.meta.dirname,'..'),out=join(root,'outputs/u02-investigation-2026-11-11');
const read=p=>JSON.parse(readFileSync(join(root,p),'utf8').replace(/^\uFEFF/,''));
const sha=bytes=>createHash('sha256').update(bytes).digest('hex');
const save=(name,value)=>writeFileSync(join(out,name),JSON.stringify(value,null,2)+'\n',{flag:'wx'});
const oldCases=read('outputs/assessment-v3-2026-11-11/stability48.json');
const newCases=read('outputs/ai-pilot-integrity-2026-11-11/synthetic-frozen/primary-cases.json');
const u02=newCases.find(c=>c.id==='U02');
const rows=[];
for(const c of oldCases.filter(c=>c.source_id==='U02')){
 assert.equal(c.answer,u02.answer);assert.deepEqual(c.expected,u02.expected);
 const file=`outputs/assessment-v3-2026-11-11/stability48/${c.id}.json`;
 rows.push({file,kind:'historical_stability',data:read(file)});
}
for(let n=1;n<=3;n++){
 const file=`outputs/ai-pilot-integrity-2026-11-11/live-series-${n}/R${n}-U02.json`;
 rows.push({file,kind:'recent_series',data:read(file)});
}
const oldRoot=join(root,'work/assessment-v3d-2026-11-11'),newRoot=join(root,'lat-ai');
const freeze=read('outputs/assessment-v3-2026-11-11/candidate-d-freeze.json');
const files=freeze.files.map(item=>{
 const oldHash=sha(readFileSync(join(oldRoot,item.path))),newHash=sha(readFileSync(join(newRoot,item.path)));
 assert.equal(oldHash,item.sha256,'Historical snapshot changed: '+item.path);
 return {path:item.path,old_sha256:oldHash,current_sha256:newHash,unchanged:oldHash===newHash};
});
const previous=rows[0].data.raw,recent=rows.find(r=>r.kind==='recent_series').data.raw;
async function capture(source,label){
 const {LocalModel}=await import(pathToFileURL(join(source,'integration/ai/core/src/local-model.mjs')));
 const requests=[];let index=0;
 const model=new LocalModel({model:'u02-capture-only',lockPath:join(out,label+'.lock'),fetchImpl:async(url,options)=>{
  if(url.endsWith('/api/v1/models'))return {ok:true,json:async()=>({models:[{loaded_instances:[{id:'u02-capture-only'}]}]})};
  assert.ok(url.endsWith('/v1/chat/completions'));assert.equal(options.method,'POST');
  requests.push({url,method:options.method,body:JSON.parse(options.body)});
  const p=index++===0?previous.candidate:previous.verification;
  return {ok:true,text:async()=>JSON.stringify({choices:[{message:{content:p.answer},finish_reason:p.finish_reason}],usage:{prompt_tokens:p.stats.input_tokens,completion_tokens:p.stats.total_output_tokens,completion_tokens_details:{reasoning_tokens:p.stats.reasoning_output_tokens}}})};
 }});
 const raw=await model.generate({role:'assess',lesson:'L1',message:u02.answer,assessment:{task_key:u02.task_key}},{signal:AbortSignal.timeout(60000),maxTokens:192});
 assert.equal(requests.length,2);assert.equal(raw.candidate.answer,previous.candidate.answer);
 save(label+'-reconstructed-requests.json',requests);return requests;
}
const oldRequests=await capture(oldRoot,'historical'),newRequests=await capture(newRoot,'current');
assert.deepEqual(oldRequests,newRequests,'Reconstructed requests differ');
const {validateAssessment,validateCandidate}=await import(pathToFileURL(join(newRoot,'integration/ai/core/src/assessment.mjs')));
const {validateAssessment:verify}=await import(pathToFileURL(join(newRoot,'integration/ai/core/src/assessment-verifier.mjs')));
const matrix=[];
for(const [proposalName,proposal] of [['historical',previous.candidate],['recent',recent.candidate]]){
 for(const [verifierName,verifier] of [['historical',previous.verification],['recent',recent.verification]]){
  let result=null,error=null;try{result=validateAssessment({candidate:proposal,verification:verifier,task_key:u02.task_key},u02.answer);}catch(e){error=e.message;}
  matrix.push({proposal:proposalName,verifier:verifierName,candidate_checks:validateCandidate(proposal,u02.answer).checks,verifier_checks:verify(verifier,u02.answer).checks,actual:result?.checks??null,error});
 }
}
const history=rows.map(({file,kind,data})=>({file,kind,file_sha256:sha(readFileSync(join(root,file))),candidate:JSON.parse(data.raw.candidate.answer),verification:JSON.parse(data.raw.verification.answer),candidate_checks:validateCandidate(data.raw.candidate,u02.answer).checks,verifier_checks:verify(data.raw.verification,u02.answer).checks,actual:data.actual,error:data.error,candidate_tokens:data.raw.candidate.stats,verification_tokens:data.raw.verification.stats}));
save('offline-analysis.json',{answer:u02.answer,answer_sha256:sha(u02.answer),author_expected:u02.expected,source_comparison:files,reconstructed_requests_equal:true,request_hashes:newRequests.map(r=>sha(JSON.stringify(r.body))),history,crossed_raw_matrix:matrix,limits:'Historical HTTP payload bytes and model weights were not archived; equality is reconstructed from SHA-verified source and exact saved answer, with constant model ID. No live inference here. Author labels are not independent teacher validation.'});
console.log(JSON.stringify({historical:history.filter(r=>r.kind==='historical_stability').length,recent:history.filter(r=>r.kind==='recent_series').length,requests_equal:true,crossed_matrix:matrix}));
