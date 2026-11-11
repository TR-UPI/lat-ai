import {createHash} from 'node:crypto';
import {rubrics} from './core/src/assessment.mjs';

// Shared identity for dispatch and read-only receipt lookup. No inference here.
export function assessmentIdentity(input,resolved){
 const body=structuredClone(input),r=structuredClone(resolved);
 if(!body||Object.keys(body).sort().join(',')!=='answer,request_id'||typeof body.request_id!=='string'||!/^[0-9a-f-]{36}$/i.test(body.request_id)||typeof body.answer!=='string'||!body.answer.trim()||body.answer.length>4000||!r||Object.keys(r).sort().join(',')!=='actor_id,attempt_id,digest,task_key'||![r.actor_id,r.attempt_id].every(x=>Number.isSafeInteger(x)&&x>0)||!/^[0-9a-f]{64}$/.test(r.digest)||!Object.hasOwn(rubrics.tasks,r.task_key))throw Error('invalid assessment identity');
 const digest=createHash('sha256').update(JSON.stringify([body.answer,r.attempt_id,r.digest,r.task_key,rubrics])).digest('hex');
 return {body,resolved:r,digest};
}

export function createAssessmentReceipt({db}){
 return function receipt(input,resolved){
  let identity;
  const fail=(reason,status)=>({status,body:{contract_version:'1.0',request_id:identity?.body.request_id??null,outcome:'unavailable',reason}});
  try{identity=assessmentIdentity(input,resolved);}catch{return fail('invalid_request',400);}
  try{
   const row=db.prepare('SELECT digest,result FROM assessments WHERE actor=? AND rid=?').get(identity.resolved.actor_id,identity.body.request_id);
   if(row&&row.digest!==identity.digest)return fail('request_conflict',409);
   let result;
   if(row?.result){
    result=JSON.parse(row.result);
    if(!result||!Number.isInteger(result.status)||result.status<100||result.status>599||result.body?.contract_version!=='1.0'||result.body.request_id!==identity.body.request_id||!['assessed','unavailable'].includes(result.body.outcome))throw Error('invalid receipt');
   }
   return {status:200,body:{contract_version:'1.0',request_id:identity.body.request_id,state:!row?'not_found':result?'completed':'pending_unknown',assessment_revision:rubrics.assessment_revision,...(result?{receipt:result}:{})}};
  }catch{return fail('receipt_unavailable',503);}
 };
}
