import {Tutor} from './tutor.mjs';
import {LocalModel} from './local-model.mjs';
import {appendFileSync} from 'node:fs';
import {StringDecoder} from 'node:string_decoder';
const experimental=process.argv.includes('--experimental');
const model=new LocalModel();
let ready=false;
if(experimental)try{ready=await model.isReady(AbortSignal.timeout(1500));}catch{}
const tutor=new Tutor({experimental,modelEnabled:experimental,modelReady:ready,modelAdapter:model,log:x=>appendFileSync(new URL('../logs/runtime.jsonl',import.meta.url),JSON.stringify(x)+'\n')});
// One UTF-8 JSON request per invocation. stdin is untrusted: it cannot supply trustedContext.
let buffer='',size=0,tooLarge=false;const decoder=new StringDecoder('utf8');
for await(const chunk of process.stdin){size+=chunk.length;if(size>20000){tooLarge=true;break;}buffer+=decoder.write(chunk);}buffer+=decoder.end();
let req;try{if(tooLarge)throw Error();req=JSON.parse(buffer);}catch{req=null;}
console.log(JSON.stringify(await tutor.respond(req)));
