import {assessmentIdentity} from './assessment-receipt.mjs';
// Private IPC only. Same Tutor owns inference; this journal never retries pending work.
export function createAssessmentBridge({db,tutor,log}){
 db.exec('CREATE TABLE IF NOT EXISTS assessments(actor INTEGER NOT NULL,rid TEXT NOT NULL,digest TEXT NOT NULL,result TEXT,PRIMARY KEY(actor,rid))');
 const flights=new Map();
 return async function assess(input,resolved){
  let body,r;
  const failure=(reason,status=503)=>({status,body:{contract_version:'1.0',request_id:body?.request_id??null,outcome:'unavailable',reason}});
  try{
   let digest;try{const identity=assessmentIdentity(input,resolved);body=identity.body;r=identity.resolved;digest=identity.digest;}catch{return failure('invalid_request',400);}
   const key=JSON.stringify([r.actor_id,body.request_id]),active=flights.get(key);
   if(active)return active.digest===digest?await active.promise:failure('request_conflict',409);
   const existing=db.prepare('SELECT digest,result FROM assessments WHERE actor=? AND rid=?').get(r.actor_id,body.request_id);
   if(existing)return existing.digest!==digest?failure('request_conflict',409):existing.result?JSON.parse(existing.result):failure('pending_unknown');
   db.prepare('INSERT INTO assessments(actor,rid,digest) VALUES(?,?,?)').run(r.actor_id,body.request_id,digest);
   const promise=(async()=>{
    let response;
    try{
     const result=await tutor.respond({role:'assess',lesson:r.task_key.slice(0,2),message:body.answer},{assessment:{task_key:r.task_key}});
     response=result.path==='model'?{status:200,body:{contract_version:'1.0',request_id:body.request_id,outcome:'assessed',...result.result}}:failure(result.reason);
    }catch{response=failure('worker_error');}
    db.prepare('UPDATE assessments SET result=? WHERE actor=? AND rid=?').run(JSON.stringify(response),r.actor_id,body.request_id);
    try{log({type:'assessment',request_id:body.request_id,status:response.status,outcome:response.body.outcome});}catch{}
    return response;
   })();
   flights.set(key,{digest,promise});try{return await promise;}finally{flights.delete(key);}
  }catch{return failure('worker_unavailable');}
 };
}
