import {readFileSync,openSync,readSync,closeSync,fstatSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {execFileSync} from 'node:child_process';
import assert from 'node:assert/strict';

export function fileFingerprint(path){
 const fd=openSync(path,'r'),hash=createHash('sha256'),buffer=Buffer.alloc(8*1024*1024);
 try{const before=fstatSync(fd);let bytes=0,n;while((n=readSync(fd,buffer,0,buffer.length,null))>0){hash.update(buffer.subarray(0,n));bytes+=n;}
  const after=fstatSync(fd);assert.equal(after.size,before.size,'Weights changed while hashing');assert.equal(after.mtimeMs,before.mtimeMs,'Weights changed while hashing');assert.equal(bytes,before.size);
  return {path,bytes,sha256:hash.digest('hex')};
 }finally{closeSync(fd);}
}
export function captureEnvironment(settings){
 if(typeof settings?.weights_path!=='string'||typeof settings?.runtime_preferences_path!=='string')throw Error('Explicit weights and runtime preferences paths required');
 const runtime=JSON.parse(readFileSync(settings.runtime_preferences_path,'utf8').replace(/^\uFEFF/,''));
 const engine=runtime.formatDefaults?.gguf,version=runtime.versions?.[engine];
 if(!engine||!version)throw Error('Selected GGUF runtime version missing');
 const cli=execFileSync('lms',['--version'],{encoding:'utf8',windowsHide:true,timeout:15000}).trim();
 const gpu=execFileSync('nvidia-smi',['--query-gpu=name,driver_version,memory.total','--format=csv,noheader'],{encoding:'utf8',windowsHide:true,timeout:15000}).trim();
 return {weights:fileFingerprint(settings.weights_path),runtime:{selected_engine:engine,selected_version:version,cli_version:cli,limitation:'Selected runtime preferences, not engine binary attestation.'},gpu,node:process.version,platform:process.platform,arch:process.arch};
}

export function makeOrders(ids,seed){
 if(ids.length<3||new Set(ids).size!==ids.length||typeof seed!=='string'||!seed.trim())throw Error('At least 3 unique cases and an explicit order seed required');
 const keyed=ids.map(id=>({id,key:createHash('sha256').update(seed+'\0'+id).digest('hex')})).sort((a,b)=>a.key.localeCompare(b.key)||a.id.localeCompare(b.id)).map(x=>x.id);
 // Distinct by construction, deterministic before inference, independent of labels.
 return [keyed,[...keyed].reverse(),[...keyed.slice(1),keyed[0]]];
}

export function verifyOrders(orders,ids){
 if(!Array.isArray(orders)||orders.length!==3)throw Error('Three execution orders required');
 const expected=[...ids].sort();
 for(const order of orders){if(!Array.isArray(order)||order.length!==ids.length||JSON.stringify([...order].sort())!==JSON.stringify(expected))throw Error('Execution order must be a complete permutation');}
 if(new Set(orders.map(x=>JSON.stringify(x))).size!==3)throw Error('Execution orders must differ');
}
