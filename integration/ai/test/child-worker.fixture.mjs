// Fault-injection fixture only: no model, no production test switches.
import {appendFileSync} from 'node:fs';
import {join} from 'node:path';
import {createBridge} from '../bridge.mjs';
import {createWorkerServer} from '../worker-http.mjs';
import {contextMetadata} from '../core/src/code-context.mjs';
const dir=process.argv[2];
const bridge=createBridge({dbPath:join(dir,'replay.sqlite3'),tutor:{async respond(request){
 appendFileSync(join(dir,'calls.txt'),'called\n');
 await new Promise(resolve=>setTimeout(resolve,500));
 return {role:'explain',path:'model',reason:'ok',result:{text:'Синтетический ответ для проверки доставки.'},code_context:contextMetadata(request)};
}}});
const server=createWorkerServer({secret:'t'.repeat(64),bridge,health:()=>({fixture:true})});
server.listen(0,'127.0.0.1',()=>process.stdout.write(JSON.stringify({port:server.address().port})+'\n'));
