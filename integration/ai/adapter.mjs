// Library boundary only. The caller must authenticate, authorize, resolve mappings,
// serialize hint operations and persist replay/events. This file opens no socket.
import {createHash} from 'node:crypto';
import {isDeepStrictEqual} from 'node:util';
import {validateCodeContext, contextMetadata} from './core/src/code-context.mjs';
import {hasVisibleText, routeDetails} from './core/src/safety-router.mjs';
import {policyText} from './core/src/policy.mjs';
import {hintTask, hintProgress} from './core/src/hint-ladder.mjs';

export const CONTRACT_VERSION = '1.0';
const uuid = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/;
const publicKeys = new Set(['contract_version','request_id','action','question','course_id','lesson_id','exercise_id','mode','document_ids','code_context']);
const fallbackReasons = new Set(['disabled','cold','unconfigured','quarantined','retired','timeout','transport','queue_full','queue_budget','invalid_output']);
const policyReasons = new Set(['crisis','privacy','health','boundaries','refusal','solution_request','support','off_topic','untrusted_claim','untrusted_document']);
const topics = {L1: new Set(['types','строки','условия','отступы']), L2: new Set(['range','накопитель','условия','отступы'])};
const errors = {
 INVALID_REQUEST: [400,'Проверь поля и размер вопроса.'],
 CONTRACT_VERSION_REQUIRED: [400,'Нужна версия контракта ИИ.'],
 INVALID_CODE_CONTEXT: [400,'Проверь размер кода и границы выделения. Текст не обрезан.'],
 AUTH_REQUIRED: [401,'Войди в платформу, чтобы продолжить.'],
 CONTEXT_NOT_AVAILABLE: [404,'Этот учебный контекст недоступен.'],
 REQUEST_ID_CONFLICT: [409,'Этот запрос уже использован с другим содержимым.'],
 PAYLOAD_TOO_LARGE: [413,'Запрос слишком большой. Текст не обрезан.'],
 UNSUPPORTED_MODE: [422,'Работа ИИ с личными документами пока не подключена.'],
 UNSUPPORTED_CONTEXT: [422,'Помощник пока не подключён к этому учебному материалу.'],
 UNSUPPORTED_TASK: [422,'Для этого задания пока нет подключённой лестницы подсказок.'],
 RATE_LIMITED: [429,'Слишком много запросов. Попробуй позже.'],
 INVALID_CORE_RESPONSE: [502,'Не удалось подготовить корректный ответ помощника.'],
 HINT_HISTORY_UNAVAILABLE: [503,'Не удалось получить историю подсказок. Попробуй позже.'],
 AI_UNAVAILABLE: [503,'Помощник сейчас недоступен.']
};
export class ContractError extends Error {
 constructor(code) {
  const known=Object.hasOwn(errors,code)?code:'AI_UNAVAILABLE';
  super(errors[known][1]); this.code=known; this.status=errors[known][0];
 }
}
const requireThat=(condition,code='INVALID_REQUEST')=>{if(!condition)throw new ContractError(code);};
const object=x=>x!==null&&typeof x==='object'&&!Array.isArray(x)&&[Object.prototype,null].includes(Object.getPrototypeOf(x));
const id=x=>Number.isSafeInteger(x)&&x>0;
const text=(x,max)=>typeof x==='string'&&x.length>0&&x.length<=max&&x.isWellFormed();
function freeze(x) {
 if(x&&typeof x==='object'){for(const value of Object.values(x))freeze(value);Object.freeze(x);}return x;
}
function validateBody(input) {
 requireThat(object(input));
 requireThat(Object.keys(input).every(k=>publicKeys.has(k)));
 requireThat(Object.hasOwn(input,'contract_version'),'CONTRACT_VERSION_REQUIRED');
 requireThat(input.contract_version===CONTRACT_VERSION);
 requireThat(typeof input.request_id==='string'&&uuid.test(input.request_id));
 requireThat(['explain','hint'].includes(input.action));
 requireThat(text(input.question,2000)&&hasVisibleText(input.question)&&!/[\p{Cc}]/u.test(input.question.replace(/[\n\r\t]/g,'')));
 requireThat(id(input.course_id)&&id(input.lesson_id));
 requireThat(input.exercise_id===undefined||input.exercise_id===null||id(input.exercise_id));
 requireThat(input.mode===undefined||typeof input.mode==='string');
 requireThat(input.document_ids===undefined||Array.isArray(input.document_ids));
 requireThat((input.mode??'internal')==='internal'&&!(input.document_ids?.length),'UNSUPPORTED_MODE');
 const body={contract_version:CONTRACT_VERSION,request_id:input.request_id,action:input.action,question:input.question,course_id:input.course_id,lesson_id:input.lesson_id,exercise_id:input.exercise_id??null,mode:'internal',document_ids:[]};
 if(input.code_context!==undefined){
  try {
   body.code_context=validateCodeContext(input.code_context);
   requireThat(body.question.length+body.code_context.code.length<=6000,'INVALID_CODE_CONTEXT');
  }catch {throw new ContractError('INVALID_CODE_CONTEXT');}
 }
 return body;
}

function canonical(value) {
 if(Array.isArray(value))return value.map(canonical);
 if(value&&typeof value==='object')return Object.fromEntries(Object.keys(value).sort().map(k=>[k,canonical(value[k])]));
 return value;
}
/** Private replay digest, not an authorization check or a public response field. */
export function fingerprintRequest(input) {
 return createHash('sha256').update(JSON.stringify(canonical(validateBody(input))),'utf8').digest('hex');
}

/** resolvedContext is private server state, NEVER request.body or user claims. */
export function prepareRequest(input,resolvedContext) {
 const body=validateBody(input),r=resolvedContext;
 requireThat(object(r)&&id(r.actor_id),'AUTH_REQUIRED');
 requireThat(r.access==='granted'&&r.course_id===body.course_id&&r.lesson_id===body.lesson_id&&(r.exercise_id??null)===body.exercise_id,'CONTEXT_NOT_AVAILABLE');
 const context={course_id:body.course_id,lesson_id:body.lesson_id,exercise_id:body.exercise_id,code_context:contextMetadata({code_context:body.code_context})??null};
 const base={body,context};
 // Authorization precedes policy; supported-lesson mapping and hint history do not.
 const policy=routeDetails(body.question,'',body.code_context?.code??'');
 if(policy.route){
  requireThat(policyReasons.has(policy.route),'INVALID_REQUEST');
  return freeze({...base,policy:{reason:policy.route,text:policyText(policy.route)}});
 }
 requireThat(Object.hasOwn(topics,r.lesson_key)&&topics[r.lesson_key].has(r.topic)&&text(r.mapping_version,100),'UNSUPPORTED_CONTEXT');
 const request={role:body.action,message:body.question,lesson:r.lesson_key,topic:r.topic};
 if(body.code_context!==undefined)request.code_context=body.code_context;
 if(r.task_key!==null&&r.task_key!==undefined){
  requireThat(body.exercise_id!==null&&text(r.task_key,100),'UNSUPPORTED_TASK');request.task_id=r.task_key;
 }
 let trustedContext={};
 if(body.action==='hint'){
  const task=hintTask(r.task_key);
  requireThat(body.exercise_id!==null&&task?.lesson===r.lesson_key&&task?.topic===r.topic,'UNSUPPORTED_TASK');
  requireThat(Array.isArray(r.hint_events),'HINT_HISTORY_UNAVAILABLE');
  try {trustedContext={hintState:hintProgress(r.task_key,structuredClone(r.hint_events)),allowSolution:false};}
  catch {throw new ContractError('HINT_HISTORY_UNAVAILABLE');}
 }
 return freeze({...base,request,trustedContext});
}

function envelope(prepared,{outcome,reason,source,text:answerText,level=null,facts=[]}) {
 return {
  contract_version:CONTRACT_VERSION,request_id:prepared.body.request_id,outcome,reason,
  answer:{text:answerText,source,hint_level:level,explanation_verification:source==='model'?'unverified':'not_applicable',facts,facts_review:facts.length?'not_reviewed_by_teacher':'not_applicable'},
  context:structuredClone(prepared.context)
 };
}
const validAnswerText=value=>text(value,900)&&hasVisibleText(value);
/** Only project an answer already validated by Tutor; never feed raw LLM output. */
export function toPublicResponse(prepared,raw) {
 if(prepared.policy)return envelope(prepared,{outcome:'policy',reason:prepared.policy.reason,source:'policy',text:prepared.policy.text});
 const valid=condition=>requireThat(condition,'INVALID_CORE_RESPONSE');
 valid(object(raw)&&raw.role===prepared.request.role&&object(raw.result));
 valid(isDeepStrictEqual(raw.code_context??null,prepared.context.code_context));
 let source,outcome,level=null,facts=[],answerText=raw.result.text;
 switch(raw.path){
  case 'model':
   valid(raw.role==='explain'&&raw.reason==='ok');source='model';outcome='answer';
   if(raw.result.explanation!==undefined){
    valid(object(raw.result.explanation)&&raw.result.explanation.verification==='unverified'&&Array.isArray(raw.result.facts)&&raw.result.facts.length>0&&raw.result.facts.length<=128);
    answerText=raw.result.explanation.text;
    facts=raw.result.facts.map(f=>{valid(object(f)&&text(f.id,100)&&text(f.text,4000));return {id:f.id,text:f.text};});
   }else valid(raw.result.facts===undefined);
   break;
  case 'catalogue':
   valid(raw.role==='hint'&&raw.reason==='ok'&&Number.isInteger(raw.result.level)&&raw.result.level>=1&&raw.result.level<=3&&raw.result.target_solution===false&&raw.result.task_id===prepared.request.task_id);
   source='catalogue';outcome='answer';level=raw.result.level;break;
  case 'template':
   valid(raw.role==='explain'&&fallbackReasons.has(raw.reason));source='template';outcome='fallback';break;
  case 'refusal':
   valid(policyReasons.has(raw.reason));source='policy';outcome='policy';break;
  default: valid(false);
 }
 valid(validAnswerText(answerText));
 return envelope(prepared,{outcome,reason:raw.reason,source,text:answerText,level,facts});
}

export function errorResponse(error,input) {
 const e=error instanceof ContractError?error:new ContractError('AI_UNAVAILABLE');
 return {status:e.status,body:{contract_version:CONTRACT_VERSION,request_id:typeof input?.request_id==='string'&&uuid.test(input.request_id)?input.request_id:null,error:{code:e.code,message:errors[e.code][1],retryable:false}}};
}
