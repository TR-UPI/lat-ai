import {createBridge} from '../bridge.mjs';
const [, ,file,requestId]=process.argv;
createBridge({dbPath:file,tutor:{respond(){process.send({event:'dispatched_to_stub'});return new Promise(()=>{});}}}).assess({request_id:requestId,answer:'Строки склеиваются. Вывод32.'},{actor_id:11,attempt_id:27,digest:'a'.repeat(64),task_key:'L1.types.1'});
setInterval(()=>{},1000);
