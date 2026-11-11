import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {randomUUID,createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=resolve(import.meta.dirname,'..'),dir=resolve(process.argv[2]);mkdirSync(dir);
const secret=readFileSync(resolve(root,'lat-ai/.runtime/i02/ipc-secret.txt'),'utf8').trim();
const headers={'Content-Type':'application/json','X-LAD-IPC':secret};
const old=resolve(root,'outputs/assessment-v3-2026-11-11');
const cases=[...JSON.parse(readFileSync(resolve(old,'regression128-with-evidence.json'),'utf8')),...JSON.parse(readFileSync(resolve(old,'holdout32.json'),'utf8'))];
async function post(path,payload){const r=await fetch('http://127.0.0.1:8372'+path,{method:'POST',headers,body:JSON.stringify(payload),signal:AbortSignal.timeout(70000)});return {status:r.status,body:await r.json()};}
const rows=[];
for(const id of ['V11','N05']){
 const c=cases.find(c=>c.id===id),payload={body:{request_id:randomUUID(),answer:c.answer},resolved:{actor_id:900000013,attempt_id:900000013+rows.length,digest:createHash('sha256').update('synthetic-v3e:'+id).digest('hex'),task_key:c.task_key}};
 const before=await post('/assess/receipt',payload);assert.equal(before.body.state,'not_found');assert.equal(before.body.assessment_revision,'2026-11-11-evidence-v3e-context');
 const started=performance.now();const terminal=await post('/assess',payload);const ms=performance.now()-started;
 // Save observations before assertions. Never retry a failed/unknown inference.
 const row={id,ms,terminal};rows.push(row);writeFileSync(resolve(dir,id+'.json'),JSON.stringify(row,null,2));
 assert.equal(terminal.status,200);assert.deepEqual(terminal.body.checks,c.expected);
 if(id==='V11')assert.ok(terminal.body.evidence[0].includes('x := 2;')&&terminal.body.evidence[0].includes('проверка x==2 := True;'));
 else for(let i=0;i<3;i++)assert.ok(c.evidence_anchors[i].every(a=>terminal.body.evidence[i].includes(a)));
 const receipt=await post('/assess/receipt',payload);assert.deepEqual(receipt.body.receipt,terminal);
 row.receipt_exact=true;writeFileSync(resolve(dir,id+'.json'),JSON.stringify(row,null,2));console.log(JSON.stringify(row));
}
writeFileSync(resolve(dir,'summary.json'),JSON.stringify({passed:rows.length,scope:'Two known synthetic live smoke cases, not unseen validation; AI worker only, no Django writes.'},null,2));
