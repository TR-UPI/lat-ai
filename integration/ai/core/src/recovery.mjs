import {randomUUID} from 'node:crypto';
import {existsSync,readFileSync,writeFileSync,unlinkSync} from 'node:fs';

// Cooperative, single-host ownership. No TTL-based deletion or lock stealing.
export class RecoveryCoordinator {
 #owner=randomUUID();#current=null;#timer;#check=null;
 constructor({model,lockPath,recoveryDelayMs=250,log=()=>{}}){
  if(!Number.isFinite(recoveryDelayMs)||recoveryDelayMs<0||recoveryDelayMs>60000)throw Error('recovery delay');
  this.model=model;this.lockPath=lockPath;this.delay=recoveryDelayMs;this.log=log;
 }
 #event(event){try{this.log({event,phase:this.#current?.phase??'idle'});}catch{}}
 #same(op){return this.#current?.op===op;}
 #owns(op){if(!this.#same(op))return false;try{const r=JSON.parse(readFileSync(this.lockPath,'utf8'));return r.owner===op.owner&&r.token===op.token&&r.model===op.model;}catch{return false;}}
 get state(){
  const c=this.#current,foreign=existsSync(this.lockPath)&&!c;
  return {busy:!!c&&['reserved','dispatched'].includes(c.phase),quarantined:foreign||!!c&&!['reserved','dispatched'].includes(c.phase),phase:foreign?'foreign_lock':c?.phase??'idle',recovering:!!this.#check};
 }
 begin(){
  this.recover();if(this.#current||existsSync(this.lockPath))throw Error('persistent quarantine or active request');
  const op=Object.freeze({owner:this.#owner,token:randomUUID(),model:this.model});
  writeFileSync(this.lockPath,JSON.stringify({...op,started_at:new Date().toISOString()}),{flag:'wx'});
  this.#current={op,phase:'reserved',dispatched:false,proof:null};this.#event('reserved');return op;
 }
 dispatch(op){if(!this.#owns(op)||this.#current.phase!=='reserved')throw Error('dispatch cancelled or ownership lost');this.#current.dispatched=true;this.#current.phase='dispatched';this.#event('dispatched');}
 quarantine(op=this.#current?.op){if(this.#same(op)){this.#current.phase='quarantined';this.#event('quarantined');}}
 #release(op){
  if(!this.#owns(op)){if(this.#same(op)){this.#current.phase='quarantined';this.#current.proof=null;}return false;}
  // Cooperating peers never replace another owner's live file; comparison protects
  // delayed callbacks against files replaced before this synchronous operation.
  unlinkSync(this.lockPath);clearTimeout(this.#timer);this.#current=null;this.#event('released');return true;
 }
 prove(op,proof){
  if(!this.#same(op))return false;
  const c=this.#current;if(proof==='not_dispatched'&&c.dispatched)return false;
  if(!['not_dispatched','terminal_response','instance_stopped'].includes(proof))return false;
  if(!this.#owns(op)){this.quarantine(op);return false;}
  if(proof==='not_dispatched'||c.phase==='dispatched'&&proof==='terminal_response')return this.#release(op);
  c.proof=proof;c.phase='proof_wait';c.after=Date.now()+this.delay;this.#event('proof_received');
  clearTimeout(this.#timer);this.#timer=setTimeout(()=>{try{this.recover();}catch{this.quarantine(op);}},this.delay);this.#timer.unref();this.recover();return true;
 }
 recover(){
  const c=this.#current;if(this.#check)return false;
  if(c?.phase==='proof_wait'&&Date.now()>=c.after)return this.#release(c.op);
  return !c&&!existsSync(this.lockPath);
 }
 async recoverWith(check,timeoutMs=5000){
  if(!Number.isFinite(timeoutMs)||timeoutMs<=0||timeoutMs>60000)throw Error('recovery timeout');
  if(this.#check)return this.#check.result;
  const c=this.#current;if(!c||!this.#owns(c.op)||!this.state.quarantined)return false;
  const op=c.op;c.phase='recovery_check';this.#event('recovery_check');
  const flight={};this.#check=flight;let timer;
  const work=Promise.resolve().then(()=>check(op)).then(proved=>{if(!this.#same(op))return false;if(proved===true)return this.prove(op,'instance_stopped');this.quarantine(op);return false;},()=>{this.quarantine(op);return false;}).finally(()=>{clearTimeout(timer);if(this.#check===flight)this.#check=null;this.recover();});
  // A timeout ends the caller's wait, not the underlying check or its ownership.
  flight.result=Promise.race([work,new Promise(resolve=>{timer=setTimeout(()=>resolve(false),timeoutMs);})]);
  return flight.result;
 }
}
