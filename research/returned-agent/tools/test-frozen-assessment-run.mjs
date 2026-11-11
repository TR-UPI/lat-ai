import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtempSync,mkdirSync,writeFileSync,readFileSync,existsSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
import {freezeRun,verifyRun,runSeries,hash} from './frozen-assessment-run.mjs';
function fixture(){
 const dir=mkdtempSync(join(tmpdir(),'lat-frozen-')),source=join(dir,'source'),data=join(dir,'frozen');
 mkdirSync(join(source,'integration/ai/core/src'),{recursive:true});mkdirSync(join(source,'integration/ai/core/data'));mkdirSync(data);
 writeFileSync(join(source,'integration/ai/core/src/model.mjs'),'// fixture only');
 const rubric=join(source,'integration/ai/core/data/assessment-rubrics.json');
 writeFileSync(rubric,JSON.stringify({version:'fixture',tasks:{'L1.types.1':{code:'print(1)',criteria:['a','b','c']}}}));
 const cases=[1,2,3].map(n=>({id:'P'+n,task_key:'L1.types.1',answer:'synthetic fixture '+n,expected:[true,true,true]}));
 const files={};
 for(const name of ['responses','review-A','review-B','adjudication'])files[name+'.frozen.json']={fixture:true};
 files['primary-cases.json']=cases;
 for(let n=1;n<=3;n++)files['repeat'+n+'.json']=cases.map(c=>({...c,id:`R${n}-${c.id}`,source_id:c.id,repeat:n}));
 const hashes={};for(const [name,value] of Object.entries(files)){writeFileSync(join(data,name),JSON.stringify(value));hashes[name]=hash(readFileSync(join(data,name)));}
 writeFileSync(join(data,'freeze.json'),JSON.stringify({data_origin:'synthetic_smoke',unique_cases:3,sha256:hashes['primary-cases.json'],files_sha256:hashes}));
 const plan=join(dir,'plan.json');freezeRun(source,data,rubric,{model_key:'qwen3.5-9b',environment_note:'test fixture',model_identity_note:'stub, not real model'},plan);
 return {dir,source,data,plan,rubric};
}
function fake({failAt=0,retire=true,bodyFail=false}={}){
 let calls=0,loads=0,retireCalls=0;
 return {counts:()=>({calls,loads,retireCalls}),deps:{
  loadModel:async options=>{loads++;return {model:'owned-fixture',state:{phase:'idle'},coordinator:{begin(){}},quarantineActive(){},retireOwnedInstance:async()=>{retireCalls++;return retire;},generate:async req=>{
   calls++;assert.deepEqual(Object.keys(req).sort(),['assessment','lesson','message','role']);
   if(failAt===calls){const response=await options.fetchImpl('http://test/v1/chat/completions',{method:'POST'});await response.text();}
   return {checks:[true,true,true]};
  }};},validate:raw=>({checks:raw.checks,evidence:['a','b','c']}),fetchImpl:async()=>{if(bodyFail)return {ok:true,status:200,text:async()=>{throw Error('lost response body');}};throw Error('lost response');}
 }};
}
test('valid frozen plan verifies all three series',()=>{const f=fixture();for(let n=1;n<=3;n++)assert.equal(verifyRun(f.plan,n).cases[0].id,`R${n}-P1`);});
test('mutated source is rejected before model loading or output creation',async()=>{const f=fixture(),stub=fake();writeFileSync(join(f.source,'integration/ai/core/src/model.mjs'),'changed');await assert.rejects(runSeries(f.plan,1,join(f.dir,'run'),stub.deps),/source changed/);assert.equal(stub.counts().loads,0);assert.equal(existsSync(join(f.dir,'run')),false);});
test('changed input labels or plan are rejected',()=>{const f=fixture();writeFileSync(join(f.data,'repeat1.json'),'[]');assert.throws(()=>verifyRun(f.plan,1),/dataset changed/);const g=fixture();writeFileSync(g.plan,readFileSync(g.plan,'utf8')+' ');assert.throws(()=>verifyRun(g.plan,1),/Plan hash/);});
test('series case/order changes rejected even if local freeze hash is edited',()=>{const f=fixture();const p=join(f.data,'repeat1.json');const cases=JSON.parse(readFileSync(p));cases.reverse();writeFileSync(p,JSON.stringify(cases));const m=JSON.parse(readFileSync(join(f.data,'freeze.json')));m.files_sha256['repeat1.json']=hash(readFileSync(p));writeFileSync(join(f.data,'freeze.json'),JSON.stringify(m));assert.throws(()=>verifyRun(f.plan,1),/Series differs/);});
test('reviewed rubric mismatch blocks plan',()=>{const f=fixture(),review=join(f.dir,'review.json');writeFileSync(review,'{}');assert.throws(()=>freezeRun(f.source,f.data,review,{},join(f.dir,'new.json')),/Reviewed rubric/);});
test('complete run saves records, checksums and retirement, never passes expected to model',async()=>{const f=fixture(),stub=fake(),out=join(f.dir,'run');const r=await runSeries(f.plan,1,out,stub.deps);assert.equal(r.status,'complete');assert.equal(r.correct,3);assert.equal(Object.keys(r.result_sha256).length,3);assert.deepEqual(stub.counts(),{loads:1,calls:3,retireCalls:1});await assert.rejects(runSeries(f.plan,1,out,stub.deps),/EEXIST/);assert.equal(stub.counts().calls,3);});
test('transport loss is saved; remaining cases not dispatched; no retry',async()=>{const f=fixture(),stub=fake({failAt:2}),out=join(f.dir,'run');const r=await runSeries(f.plan,1,out,stub.deps);assert.equal(r.status,'incomplete');assert.equal(r.completed,1);assert.deepEqual(r.transport_unknown,['R1-P2']);assert.deepEqual(r.not_run,['R1-P3']);assert.equal(stub.counts().calls,2);const row=JSON.parse(readFileSync(join(out,'R1-P2.json')));assert.equal(row.status,'transport_unknown');assert.equal(row.stages[0].transport_error,true);assert.equal(r.retry_performed,false);});
test('model disagreement is a refusal with no score; counters retained separately',async()=>{const f=fixture(),stub=fake();stub.deps.validate=()=>{throw Error('assessment disagreement');};const r=await runSeries(f.plan,2,join(f.dir,'run'),stub.deps);assert.equal(r.status,'complete');assert.equal(r.refusals,3);assert.equal(r.correct,0);});
test('unproven retirement prevents a complete result',async()=>{const f=fixture(),stub=fake({retire:false});const r=await runSeries(f.plan,3,join(f.dir,'run'),stub.deps);assert.equal(r.status,'incomplete');assert.equal(r.retirement_proven,false);assert.equal(r.correct,3);});
test('load failure still has an explicit incomplete report and all cases not run',async()=>{const f=fixture();const r=await runSeries(f.plan,1,join(f.dir,'run'),{loadModel:async()=>{throw Error('load failed');},validate:()=>{}});assert.equal(r.attempted,0);assert.equal(r.not_run.length,3);assert.equal(r.status,'incomplete');});
test('response body loss records stage duration and prevents dispatch of later cases',async()=>{const f=fixture(),stub=fake({failAt:1,bodyFail:true}),out=join(f.dir,'run');const r=await runSeries(f.plan,1,out,stub.deps);assert.equal(r.status,'incomplete');assert.equal(r.attempted,1);const row=JSON.parse(readFileSync(join(out,'R1-P1.json')));assert.equal(row.stages[0].terminal_body,false);assert.ok(row.stages[0].ms>=0);assert.equal(stub.counts().calls,1);});
