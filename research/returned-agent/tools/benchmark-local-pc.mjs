import {mkdirSync,appendFileSync,writeFileSync} from 'node:fs';
import {resolve} from 'node:path';
import {LocalModel} from '../lat-ai/integration/ai/core/src/local-model.mjs';
import {validateAnswer} from '../lat-ai/integration/ai/core/src/validation.mjs';
import {validateAssessment} from '../lat-ai/integration/ai/core/src/assessment.mjs';

const dir=resolve(process.argv[2]);mkdirSync(dir,{recursive:true});
const record=x=>{appendFileSync(resolve(dir,'measurements.jsonl'),JSON.stringify({at:new Date().toISOString(),...x})+'\n');console.log(JSON.stringify(x));};
const cases=[
 ['strings',{role:'explain',lesson:'L1',topic:'types',message:'Почему здесь получается 32, а не 5?',code_context:{code:'print("3" + "2")',revision:1,selection:null}}],
 ['condition',{role:'explain',lesson:'L1',topic:'условия',message:'Объясни пошагово, какую ветку выберет программа и почему.',code_context:{code:'x = 2\nif x == 2:\n    print("да")\nelse:\n    print("нет")',revision:1,selection:null}}],
 ['range',{role:'explain',lesson:'L2',topic:'range',message:'Какие значения примет i и почему число 5 не выводится?',code_context:{code:'for i in range(2, 5):\n    print(i)',revision:1,selection:null}}],
 ['accumulator',{role:'explain',lesson:'L2',topic:'накопитель',message:'Объясни, как меняется s на каждом проходе и почему print стоит после цикла.',code_context:{code:'s = 0\nfor i in range(1, 4):\n    s = s + i\nprint(s)',revision:1,selection:null}}],
 ['grade-strings',{role:'assess',lesson:'L1',topic:'types',message:'Оба значения в кавычках являются строками. Плюс соединяет строки, а не складывает числа. Будет выведено 32.',assessment:{task_key:'L1.types.1'}}],
 ['grade-condition',{role:'assess',lesson:'L1',topic:'условия',message:'x равен 2, поэтому проверка x == 2 истинна. Выполняется if и выводится да, else не выполняется.',assessment:{task_key:'L1.condition.1'}}],
 ['grade-range',{role:'assess',lesson:'L2',topic:'range',message:'Переменная i принимает значения 2, 3, 4. Правая граница 5 не входит в range. print выводит каждое число на новой строке.',assessment:{task_key:'L2.range.1'}}],
 ['grade-accumulator',{role:'assess',lesson:'L2',topic:'накопитель',message:'s равна 0 до начала цикла и не сбрасывается. При прибавлении 1, 2 и 3 сумма становится 1, 3, 6. print без отступа выполняется один раз после цикла и выводит 6.',assessment:{task_key:'L2.accumulator.1'}}],
];
let model;
const comment='# Учебный комментарий о строках, числах и последовательности действий.\n';
const longCode=comment.repeat(53)+'print("3" + "2")';
const longQuestion='Почему результат 32, а не 5? Ответь кратко, в двух предложениях. '+('Меня интересуют типы значений в кавычках, смысл операции плюс и результат вывода; комментарии не выполняются. '.repeat(16));
const extended=[
 ['long-code',{role:'explain',lesson:'L1',topic:'types',message:'Почему этот код выводит 32? Объясни кратко.',code_context:{code:longCode,revision:1,selection:null}}],
 ['long-code-question',{role:'explain',lesson:'L1',topic:'types',message:longQuestion,code_context:{code:longCode,revision:1,selection:null}}],
 ['long-code-question-warm',{role:'explain',lesson:'L1',topic:'types',message:longQuestion,code_context:{code:longCode,revision:1,selection:null}}]
];
try{
 const start=performance.now();
 model=await LocalModel.loadOwned({modelKey:'qwen3.5-9b',contextLength:8192,lockPath:resolve(dir,'model.lock'),recoveryLog:event=>appendFileSync(resolve(dir,'recovery.jsonl'),JSON.stringify(event)+'\n')});
 record({event:'loaded',instance:model.model,load_ms:performance.now()-start});
 for(const [name,req] of (process.argv.includes('--extended')?extended:[...cases,...cases.slice(0,4).map(([n,r])=>[n+'-warm',r])])){
  const started=performance.now();record({event:'start',name});
  try{
   const result=await model.generate(req,{signal:AbortSignal.timeout(180000),maxTokens:192});
   let valid=true,validation_error=null;
   try{req.role==='assess'?validateAssessment(result,req.message):validateAnswer(result,req.lesson);}catch(e){valid=false;validation_error=e.message;}
   record({event:'result',name,ms:performance.now()-started,valid,validation_error,finish_reason:result.finish_reason,stats:result.stats});
   writeFileSync(resolve(dir,name+'.json'),JSON.stringify(result,null,2));
  }catch(e){record({event:'error',name,ms:performance.now()-started,error:e.message});throw e;}
 }
}finally{
 if(model){
  if(model.state.phase==='idle'){model.coordinator.begin();model.quarantineActive();}
  const stopped=await model.retireOwnedInstance();record({event:'retired',instance:model.model,proven:stopped});
  if(!stopped)process.exitCode=2;
 }
}
