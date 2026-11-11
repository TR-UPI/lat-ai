import {readFileSync,writeFileSync,existsSync} from 'node:fs';
import {resolve,join} from 'node:path';
import {createHash} from 'node:crypto';
import assert from 'node:assert/strict';
import {fileFingerprint} from './assessment-environment.mjs';
const root=resolve(import.meta.dirname,'..'),out=join(root,'outputs/u02-runtime-controls-2026-11-11'),live=join(out,'checkpoint-live');
const read=p=>JSON.parse(readFileSync(p,'utf8').replace(/^\uFEFF/,''));
const save=(p,v)=>writeFileSync(p,JSON.stringify(v,null,2)+'\n',{flag:'wx'});
const sha=p=>createHash('sha256').update(readFileSync(p)).digest('hex');
const plan=read(join(out,'checkpoint-protocol.json')),sessions=[];let completed=0,posts=0;
assert.equal(sha(join(root,'tools/diagnose-u02-checkpoints.mjs')),plan.script_sha256);
for(const s of plan.sessions){const folder=join(live,s.id),summary=read(join(folder,'summary.json')),meta=read(join(folder,'loaded-model.json'));assert.equal(summary.retirement_proven,true);assert.equal(summary.error,null);
 for(const [n,id]of s.order.entries()){const row=read(join(folder,`${n+1}-${id}.json`));assert.equal(row.calls.length,2);for(const c of row.calls){assert.equal(c.http_status,200);assert.equal(c.response_body.choices[0].finish_reason,'stop');posts++;}completed++;}
 sessions.push({session:s.id,instance:meta.loaded_instances[0].id,retirement_proven:true,summary_sha256:sha(join(folder,'summary.json')),lock_file_retained:existsSync(join(folder,'model.lock'))});
}
const response=await fetch('http://127.0.0.1:1234/api/v1/models',{signal:AbortSignal.timeout(3000)});assert.ok(response.ok);const metadata=await response.json();
const loadedIds=metadata.models.flatMap(m=>m.loaded_instances.map(i=>i.id));assert.ok(sessions.every(s=>!loadedIds.includes(s.instance)));
const weights=fileFingerprint(plan.model_fingerprint.path);assert.equal(weights.sha256,plan.model_fingerprint.sha256.toLowerCase());save(join(live,'weights-after-recovery.json'),{...weights,measured_utc:new Date().toISOString(),note:'Separate read-only audit after abnormal exit, NOT the missing in-process post-run fingerprint.'});
save(join(out,'checkpoint-recovery-audit.json'),{audited_utc:new Date().toISOString(),process_exit_code:1,process_completed_normally:false,in_process_final_summary_exists:existsSync(join(live,'summary.json')),terminal_assessments:completed,terminal_model_posts:posts,sessions,all_owned_instances_absent_now:true,weights_before_after_match:true,checkpoint_log_sha256:sha(join(out,'checkpoint-live.log')),actions:'Read-only artifact/GET/hash audit. No inference retry, no lock removal, no SDK reload. Last diagnostic lock preserved as evidence.',failure:'SDK load AbortSignal.timeout listener sent cancel after WebSocket transport disposal; global final summary and in-process after fingerprint absent.'});console.log(JSON.stringify({terminal_assessments:completed,terminal_model_posts:posts,owned_instances_absent:true,normal_process_exit:false}));
