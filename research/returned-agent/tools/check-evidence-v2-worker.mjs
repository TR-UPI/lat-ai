import {readFileSync,mkdirSync,writeFileSync,appendFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {randomUUID,createHash} from 'node:crypto';
import assert from 'node:assert/strict';
const root=resolve(import.meta.dirname,'..'),base=resolve(root,'outputs/assessment-evidence-v2-2026-11-11');
const dir=resolve(process.argv[2]);mkdirSync(dir);
const secret=readFileSync(resolve(root,'lat-ai/.runtime/i02/ipc-secret.txt'),'utf8').trim();
const headers={'Content-Type':'application/json','X-LAD-IPC':secret};
const read=p=>JSON.parse(readFileSync(resolve(base,p),'utf8'));
const cases=[...read('holdout32.json').filter(c=>['H02','H06','H14','H30'].includes(c.id)),read('regression96.json').find(c=>c.id==='U22')];
const rows=[];
async function run(c){
 const body={answer:c.answer,request_id:randomUUID()},resolved={actor_id:900000011,attempt_id:900000011+cases.indexOf(c),task_key:c.task_key,digest:createHash('sha256').update('synthetic-ai-only:'+c.id).digest('hex')};
 const payload=JSON.stringify({body,resolved});const start=performance.now();
 const response=await fetch('http://127.0.0.1:8372/assess',{method:'POST',headers,body:payload,signal:AbortSignal.timeout(70000)});
 const result=await response.json();const ms=performance.now()-start;
 const unavailable=response.status===503&&result.outcome==='unavailable'&&result.reason==='invalid_output'&&!Object.hasOwn(result,'checks');
 const correct=response.status===200&&result.outcome==='assessed'&&JSON.stringify(result.checks)===JSON.stringify(c.expected)&&result.evidence.every((q,i)=>result.checks[i]?q.length>0&&c.answer.includes(q):q==='');
 const accepted=c.id==='U22'?unavailable:correct||unavailable;
 const replayStart=performance.now();
 // Only replay a received terminal receipt; never retry an unknown POST.
 const replayResponse=await fetch('http://127.0.0.1:8372/assess',{method:'POST',headers,body:payload,signal:AbortSignal.timeout(5000)});
 const replay=await replayResponse.json();assert.deepEqual(replay,result);assert.equal(replayResponse.status,response.status);
 const row={id:c.id,status:response.status,result,ms,replay_ms:performance.now()-replayStart,accepted,correct,unavailable};
 rows.push(row);appendFileSync(resolve(dir,'events.jsonl'),JSON.stringify(row)+'\n');console.log(JSON.stringify(row));
 assert.ok(accepted,c.id+' unexpected grade or transport outcome');
}
// Two simultaneous callers exercise the existing shared queue with two-stage inference.
await Promise.all(cases.slice(0,2).map(run));
for(const c of cases.slice(2))await run(c);
const health=await (await fetch('http://127.0.0.1:8372/health',{headers,signal:AbortSignal.timeout(5000)})).json();
assert.equal(health.tutor.ready,true);assert.equal(health.tutor.busy,false);assert.equal(health.tutor.quarantined,false);
writeFileSync(resolve(dir,'summary.json'),JSON.stringify({cases:rows.length,accepted:rows.filter(r=>r.accepted).length,correct:rows.filter(r=>r.correct).length,abstained:rows.filter(r=>r.unavailable).length,max_ms:Math.max(...rows.map(r=>r.ms)),health,note:'Private AI worker only; synthetic AI journal entries. No backend accounts or student attempt rows created. First two calls concurrent. Each received terminal receipt replayed once.'},null,2));
