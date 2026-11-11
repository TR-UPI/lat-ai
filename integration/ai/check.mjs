// Reproducible synthetic handoff examples; no HTTP, database or live model calls.
import fs from 'node:fs';
import {fileURLToPath} from 'node:url';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import Ajv2020 from 'ajv/dist/2020.js';
import {prepareRequest,toPublicResponse,errorResponse} from './adapter.mjs';
import {Tutor} from './core/src/tutor.mjs';
import {buildFactLedger} from './core/src/fact-ledger.mjs';

const contracts=new URL('../../contracts/',import.meta.url);
export const readJson=name=>JSON.parse(fs.readFileSync(new URL(name,contracts)));
export function validators(){
 const ajv=new Ajv2020({strict:true,allErrors:true});
 // JSON Schema counts code points. This annotation is enforced by the adapter,
 // never misrepresented as an Ajv Unicode/selection validation keyword.
 ajv.addKeyword({keyword:'x-maxUtf16Units',schemaType:'number',valid:true});
 return Object.fromEntries(['request','response','error'].map(name=>[name,ajv.compile(readJson(`tutor-v1.${name}.schema.json`))]));
}
export async function examples(){
 const request=readJson('examples/explain-request.json');
 const trusted={actor_id:5,access:'granted',course_id:11,lesson_id:21,exercise_id:31,mapping_version:'SYNTHETIC-EXAMPLE-NOT-DB-MAPPING',lesson_key:'L1',topic:'условия',task_key:'practice.age',hint_events:[]};
 const tutor=new Tutor(),prepared=prepareRequest(request,trusted);
 const hint=prepareRequest(readJson('examples/hint-request.json'),trusted);
 const crisis=prepareRequest({...request,question:'Не хочу больше жить'},trusted);
 let invalid;
 try{prepareRequest({...request,code_context:{code:'😀',revision:1,selection:{start:0,end:1}}},trusted);}catch(e){invalid=errorResponse(e,request).body;}
 const model=new Tutor({experimental:true,modelEnabled:true,modelReady:true,generate:async()=>({answer:JSON.stringify({text:'При age = 14 условие age >= 12 истинно.',source_ids:['L1']}),finish_reason:'stop',stats:{total_output_tokens:20,reasoning_output_tokens:0}})});
 const separated=new Tutor({answerMode:'separated',experimental:true,modelEnabled:true,modelReady:true,generate:async req=>({answer:JSON.stringify({explanation:'При age = 14 условие age >= 12 истинно.',fact_ids:[buildFactLedger(req).facts[0].id],source_ids:['L1']}),finish_reason:'stop',stats:{total_output_tokens:30,reasoning_output_tokens:0}})});
 const results={'fallback-response.json':toPublicResponse(prepared,await tutor.respond(prepared.request,prepared.trustedContext)),
 'hint-response.json':toPublicResponse(hint,await tutor.respond(hint.request,hint.trustedContext)),
 'policy-response.json':toPublicResponse(crisis),'error-response.json':invalid,
 'model-response.SYNTHETIC.json':toPublicResponse(prepared,await model.respond(prepared.request,prepared.trustedContext)),
 'separated-response.SYNTHETIC.json':toPublicResponse(prepared,await separated.respond(prepared.request,prepared.trustedContext))};
 assert.equal(results['model-response.SYNTHETIC.json'].answer.source,'model');
 assert.equal(results['separated-response.SYNTHETIC.json'].answer.source,'model');
 assert.ok(results['separated-response.SYNTHETIC.json'].answer.facts.length>0);
 return results;
}
export function verifyCore(){
 const manifest=JSON.parse(fs.readFileSync(new URL('UPSTREAM.json',import.meta.url)));
 const overrides=JSON.parse(fs.readFileSync(new URL('LOCAL_OVERRIDES.json',import.meta.url)));
 for(const override of overrides)assert.equal(manifest.files.find(x=>x.path===override.path)?.sha256,override.upstream_sha256,'upstream provenance');
 for(const file of manifest.files){const content=fs.readFileSync(new URL('core/'+file.path,import.meta.url));assert.equal(createHash('sha256').update(content).digest('hex'),overrides.find(x=>x.path===file.path)?.sha256??file.sha256,file.path);}
 return manifest.files.length;
}
if(process.argv[1]===fileURLToPath(import.meta.url)){
 const v=validators(),results=await examples();
 for(const name of ['explain-request.json','hint-request.json']){assert.ok(v.request(readJson('examples/'+name)),JSON.stringify(v.request.errors));}
 for(const [name,value] of Object.entries(results)){
  const validate=name.startsWith('error')?v.error:v.response;assert.ok(validate(value),JSON.stringify(validate.errors));
  const target=new URL('examples/'+name,contracts);
  if(process.argv.includes('--write-examples'))fs.writeFileSync(target,JSON.stringify(value,null,2)+'\n');
  else assert.deepEqual(readJson('examples/'+name),value,name);
 }
 console.log(JSON.stringify({schemas:3,request_examples:2,response_examples:Object.keys(results).length,pinned_core_files:verifyCore(),synthetic_generator_calls:2,live_model_calls:0,django_executed:false}));
}
