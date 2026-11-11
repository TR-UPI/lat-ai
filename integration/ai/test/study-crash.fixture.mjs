import {createBridge} from '../bridge.mjs';

const [, ,dbPath,requestJson]=process.argv;
const tutor={study(){
 process.send('dispatched');
 return new Promise(()=>{});
}};
createBridge({dbPath,tutor}).study(JSON.parse(requestJson),{actor_id:'1'});
setInterval(()=>{},1000);
