import test from 'node:test';
import assert from 'node:assert/strict';
import {validators,examples,readJson,verifyCore} from '../check.mjs';
import {prepareRequest,toPublicResponse,ContractError,errorResponse,fingerprintRequest} from '../adapter.mjs';
const v=validators();
test('all published examples satisfy schemas and reproduce through actual disabled core',async()=>{
 for(const name of ['explain-request.json','hint-request.json'])assert.ok(v.request(readJson('examples/'+name)),JSON.stringify(v.request.errors));
 for(const [name,data] of Object.entries(await examples())){const validate=name.startsWith('error')?v.error:v.response;assert.ok(validate(data),JSON.stringify(validate.errors));assert.deepEqual(data,readJson('examples/'+name));}
});
test('all declared errors are schema valid; additional properties rejected on either boundary',()=>{
 for(const code of readJson('tutor-v1.error.schema.json').properties.error.properties.code.enum)assert.ok(v.error(errorResponse(new ContractError(code),{}).body));
 assert.equal(v.request({...readJson('examples/explain-request.json'),allowSolution:true}),false);
 assert.equal(v.response({...readJson('examples/fallback-response.json'),raw_prompt:'DO_NOT_EMIT'}),false);
});
test('schema never prevents intended no-exercise crisis hint; runtime still rejects ordinary hint',()=>{
 const b={...readJson('examples/hint-request.json'),exercise_id:null};
 const c={actor_id:5,access:'granted',course_id:11,lesson_id:21,exercise_id:null,mapping_version:'test',lesson_key:'L1',topic:'условия',task_key:null};
 assert.ok(v.request(b));assert.throws(()=>prepareRequest(b,c),e=>e.code==='UNSUPPORTED_TASK');
 const p=prepareRequest({...b,question:'Не хочу больше жить'},c);assert.ok(v.response(toPublicResponse(p)));assert.equal(toPublicResponse(p).outcome,'policy');
});
test('UTF16 validation remains stricter than schema codepoint length',()=>{
 const b={...readJson('examples/explain-request.json'),question:'😀'.repeat(1001)};
 assert.ok(v.request(b));assert.throws(()=>prepareRequest(b,{}),e=>e.code==='INVALID_REQUEST');
});
test('pinned core source/data hashes unchanged',()=>assert.equal(verifyCore(),20));
test('published canonical vectors retain exact normalized request digests',()=>{
 for(const c of readJson('examples/fingerprint-vectors.json').vectors){assert.ok(v.request(c.request));assert.equal(fingerprintRequest(c.request),c.sha256);}
});
