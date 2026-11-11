import {createStudyBridge} from './study-bridge.mjs';
import {DatabaseSync} from 'node:sqlite';
import {createHash} from 'node:crypto';
import {ContractError,prepareRequest,toPublicResponse,errorResponse,fingerprintRequest} from './adapter.mjs';
import {createAssessmentBridge} from './assessment-bridge.mjs';
import {createAssessmentReceipt} from './assessment-receipt.mjs';

// One local worker owns this journal. No prompts/code/tokens in operational logs.
// Completed envelopes are private replay data; pending rows are never retried.
export function createBridge({dbPath,tutor,log=()=>{}}) {
 const db=new DatabaseSync(dbPath);
 try{db.exec(`PRAGMA locking_mode=EXCLUSIVE; PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
 BEGIN EXCLUSIVE; COMMIT;
 CREATE TABLE IF NOT EXISTS requests(actor INTEGER NOT NULL, rid TEXT NOT NULL,
 digest TEXT NOT NULL, mapping TEXT NOT NULL, result TEXT, PRIMARY KEY(actor,rid));
 CREATE TABLE IF NOT EXISTS hints(actor INTEGER NOT NULL, exercise INTEGER NOT NULL,
 mapping TEXT NOT NULL, rid TEXT NOT NULL, task TEXT NOT NULL, level INTEGER NOT NULL,
 PRIMARY KEY(actor,rid));`);}catch(error){db.close();throw error;}
 const flights=new Map(),lanes=new Map();let closed=false;
 const mappingHash=r=>createHash('sha256').update(JSON.stringify([r.course_id,r.lesson_id,r.exercise_id??null,r.mapping_version??null,r.lesson_key??null,r.topic??null,r.task_key??null])).digest('hex');
 const events=(r,mapping)=>db.prepare('SELECT rid,task,level FROM hints WHERE actor=? AND exercise=? AND mapping=? ORDER BY rowid').all(r.actor_id,r.exercise_id,mapping).map(x=>({id:x.rid,task_id:x.task,kind:'hint',status:'verified',level:x.level}));
 async function execute(body,r,digest,mapping) {
  const existing=db.prepare('SELECT * FROM requests WHERE actor=? AND rid=?').get(r.actor_id,body.request_id);
  if(existing){
   if(existing.digest!==digest||existing.mapping!==mapping)throw new ContractError('REQUEST_ID_CONFLICT');
   if(!existing.result)throw new ContractError('AI_UNAVAILABLE');
   return JSON.parse(existing.result);
  }
  const history=body.action==='hint'?[...(r.hint_events??[]),...events(r,mapping)]:[];
  const prepared=prepareRequest(body,{...r,hint_events:history});
  db.prepare('INSERT INTO requests(actor,rid,digest,mapping) VALUES(?,?,?,?)').run(r.actor_id,body.request_id,digest,mapping);
  let response;
  try {
   response={status:200,body:toPublicResponse(prepared,prepared.policy?null:await tutor.respond(prepared.request,prepared.trustedContext))};
  } catch(error) {response=errorResponse(error,body);}
  db.exec('BEGIN IMMEDIATE');
  try {
   db.prepare('UPDATE requests SET result=? WHERE actor=? AND rid=?').run(JSON.stringify(response),r.actor_id,body.request_id);
   if(response.status===200&&response.body.outcome==='answer'&&response.body.answer.source==='catalogue'){
    db.prepare('INSERT INTO hints(actor,exercise,mapping,rid,task,level) VALUES(?,?,?,?,?,?)').run(r.actor_id,body.exercise_id,mapping,body.request_id,r.task_key,response.body.answer.hint_level);
   }
   db.exec('COMMIT');
  }catch(error){db.exec('ROLLBACK');throw error;}
  try{log({type:'answer',request_id:body.request_id,status:response.status,outcome:response.body.outcome??'error',source:response.body.answer?.source??null});}catch{}
  return response;
 }
 async function ask(input,resolved){
  try {
   if(closed)throw new ContractError('AI_UNAVAILABLE');
   const body=structuredClone(input),r=structuredClone(resolved);
   // Reauthorize and validate even if a same-ID result/flight is present.
   prepareRequest(body,r);
   const digest=fingerprintRequest(body),mapping=mappingHash(r),key=JSON.stringify([r.actor_id,body.request_id]);
   const active=flights.get(key);
   if(active){if(active.digest!==digest||active.mapping!==mapping)throw new ContractError('REQUEST_ID_CONFLICT');return await active.promise;}
   const lane=body.action==='hint'?JSON.stringify([r.actor_id,body.exercise_id]):key;
   const previous=lanes.get(lane)??Promise.resolve();
   const promise=previous.catch(()=>{}).then(()=>execute(body,r,digest,mapping));
   flights.set(key,{digest,mapping,promise});lanes.set(lane,promise);
   try{return await promise;}finally{flights.delete(key);if(lanes.get(lane)===promise)lanes.delete(lane);}
  } catch(error){return errorResponse(error,input);}
 }
 const assess=createAssessmentBridge({db,tutor,log});
 const assessmentReceipt=createAssessmentReceipt({db});
 let study;
 try{study=createStudyBridge({db,tutor,log});}catch(error){db.close();throw error;}
 return {ask,assess,assessmentReceipt,...study,close(){if(!closed){closed=true;db.close();}}};
}
