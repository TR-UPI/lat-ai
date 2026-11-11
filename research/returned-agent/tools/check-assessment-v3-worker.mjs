import {readFileSync,mkdirSync,writeFileSync,appendFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {randomUUID,createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=resolve(import.meta.dirname,'..'),dir=resolve(process.argv[2]);mkdirSync(dir);
const secret=readFileSync(resolve(root,'lat-ai/.runtime/i02/ipc-secret.txt'),'utf8').trim();
const headers={'Content-Type':'application/json','X-LAD-IPC':secret};
const all=JSON.parse(readFileSync(resolve(root,'outputs/assessment-v3-2026-11-11/regression128-with-evidence.json'),'utf8'));
const rows=[];
async function post(path,payload){const r=await fetch('http://127.0.0.1:8372'+path,{method:'POST',headers,body:JSON.stringify(payload),signal:AbortSignal.timeout(70000)});return {status:r.status,body:await r.json()};}
for(const id of ['N05','U15','U02']){
 const c=all.find(c=>c.id===id),payload={body:{request_id:randomUUID(),answer:c.answer},resolved:{actor_id:900000012,attempt_id:900000012+rows.length,digest:createHash('sha256').update('synthetic-v3:'+id).digest('hex'),task_key:c.task_key}};
 const before=await post('/assess/receipt',payload);assert.equal(before.body.state,'not_found');
 const started=performance.now(),flight=post('/assess',payload);let pending;
 for(let i=0;i<20;i++){pending=await post('/assess/receipt',payload);if(pending.body.state==='pending_unknown')break;await new Promise(r=>setTimeout(r,50));}
 assert.equal(pending.body.state,'pending_unknown');assert.equal(pending.body.receipt,undefined);
 const terminal=await flight;const ms=performance.now()-started;
 if(id!=='U02'){
  assert.equal(terminal.status,200);assert.deepEqual(terminal.body.checks,c.expected);
  for(let i=0;i<3;i++)assert.ok(c.evidence_anchors[i].every(a=>terminal.body.evidence[i].includes(a)),id+' incomplete citation');
 }else{assert.ok(terminal.status===503&&terminal.body.reason==='invalid_output'||terminal.status===200&&JSON.stringify(terminal.body.checks)===JSON.stringify(c.expected));}
 for(let i=0;i<3;i++){const receipt=await post('/assess/receipt',payload);assert.equal(receipt.status,200);assert.equal(receipt.body.state,'completed');assert.deepEqual(receipt.body.receipt,terminal);}
 assert.equal((await post('/assess/receipt',{...payload,body:{...payload.body,answer:'Other answer'}})).status,409);
 const foreign=await post('/assess/receipt',{...payload,resolved:{...payload.resolved,actor_id:900000099}});assert.equal(foreign.body.state,'not_found');assert.equal(foreign.body.receipt,undefined);
 const row={id,ms,terminal,not_found_before:true,pending_during:true,exact_receipt_reads:3,identity_conflict:true,actor_isolation:true};rows.push(row);appendFileSync(resolve(dir,'events.jsonl'),JSON.stringify(row)+'\n');console.log(JSON.stringify(row));
}
const health=await (await fetch('http://127.0.0.1:8372/health',{headers,signal:AbortSignal.timeout(5000)})).json();
assert.equal(health.tutor.ready,true);assert.equal(health.tutor.busy,false);assert.equal(health.tutor.quarantined,false);
writeFileSync(resolve(dir,'summary.json'),JSON.stringify({cases:rows.length,passed:rows.length,health,note:'Private AI only; synthetic journal identities, no Django accounts/attempts. Each original POST sent once; receipt lookup never repeats generation.'},null,2));
