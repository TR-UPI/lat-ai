import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import vm from 'node:vm';
import {createRequire} from 'node:module';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../../../',import.meta.url));
const nativeRequire=createRequire(import.meta.url);
function handler(){
 let captured;
 const http={createServer:fn=>{captured=fn;return {on(){},listen(){},close(){}};}};
 vm.runInNewContext(fs.readFileSync(path.join(root,'server.cjs'),'utf8'),{require:name=>name==='node:http'?http:nativeRequire(name),__dirname:root,Buffer,URIError,console:{log(){},error(){}},process:{on(){},exit(){},exitCode:0}});
 return captured;
}
async function status(url){let code;const res={writeHead:n=>{code=n;},end(){},destroy(){}};await handler()({method:'HEAD',url},res);return code;}
test('static server cannot expose new private AI bank or prompt through direct/encoded/normalized paths',async()=>{
 for(const url of ['/integration/ai/core/data/quiz-bank.json','/integration/ai/core/data/explain-prompt.txt','/%69ntegration/ai/core/data/quiz-bank.json','/assets/../integration/ai/core/data/quiz-bank.json','/INTEGRATION/ai/core/data/quiz-bank.json'])assert.equal(await status(url),403,url);
});
test('public page and script still served by the original static handler',async()=>{
 assert.equal(await status('/index.html'),200);assert.equal(await status('/assets/app.js'),200);
});
test('static allowlist denies runtime short aliases and non-public project files',async()=>{
 for(const url of ['/RUNTIM~1/i02/ipc-secret.txt','/RUNTIM~1/i02/mapping.json','/contracts/examples/explain-request.json','/tools/../.runtime/i02/ipc-secret.txt'])assert.equal(await status(url),403,url);
});
