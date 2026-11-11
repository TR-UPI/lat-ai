const check=(ok,message)=>{if(!ok)throw Error(message)};
const integer=n=>Number.isSafeInteger(n)&&n>=0&&n<=1000;
const generic={
 range:['Какие значения ты ожидаешь увидеть на каждой итерации?','Проверь начало, направление шага и исключённую конечную границу range.'],
 types:['Какие типы у двух значений перед операцией?','Проверь, соединяются здесь строки или складываются числа.'],
 строки:['Что обозначает каждый операнд: строку или число?','Проверь, соединяешь ли строки или складываешь числа.'],
 условия:['Какое условие истинно для выбранного ввода?','Проследи проверки сверху вниз: выполняется первая истинная ветвь if/elif.'],
 накопитель:['Каково значение переменной после каждого шага?','Проверь, сохраняется ли значение между итерациями или сбрасывается.'],
 отступы:['Какие строки относятся к одному блоку?','Сравни отступы строк тела и строки после блока.']
};
const tasks={
 'L1.types.1':{lesson:'L1',topic:'types',analogy:'В другом примере "6" + "1" даёт "61": две строки соединяются. Примени это правило к своему примеру.',solution:'В print("3" + "2") оба значения — строки. Знак + соединяет их: получается строка "32". print выводит 32, затем перевод строки.'},
 'L1.types.2':{lesson:'L1',topic:'types',analogy:'В другом примере int("6") + int("1") даёт 7: сначала строки превращаются в числа.',solution:'int("3") даёт число 3, int("2") — число 2. Их сумма равна 5. print выводит 5, затем перевод строки.'},
 'L1.condition.1':{lesson:'L1',topic:'условия',analogy:'В другом примере x = 8 и if x == 8 условие истинно, поэтому выполняется его блок, а else пропускается.',solution:'x равно 2. Проверка x == 2 истинна. Выполняется print("да"), ветка else пропускается. Вывод: да.'},
 'L2.range.1':{lesson:'L2',topic:'range',analogy:'Например, range(10, 13) даёт 10, 11, 12: конечная граница не входит. Сравни со своим диапазоном.',solution:'range(2, 5) начинается с 2, шаг равен 1, граница 5 не входит. Получаются 2, 3, 4. print выводит каждое число на отдельной строке.'},
 'L2.range.2':{lesson:'L2',topic:'range',analogy:'Например, range(10, 4, -3) даёт 10, 7. Следующее число 4 уже равно исключённой границе.',solution:'range(5, 1, -2) начинается с 5. После шага -2 получаем 3. Следующее число 1 равно исключённой границе. Вывод: 5 и 3 на отдельных строках.'},
 'L2.accumulator.1':{lesson:'L2',topic:'накопитель',analogy:'В другом примере s = 0 перед циклом, затем s = s + 4 два раза: сначала 4, затем 8. Значение сохраняется между шагами.',solution:'Сначала s = 0. range(1, 4) даёт 1, 2, 3. После прибавлений s становится 1, затем 3, затем 6. print находится после цикла и один раз выводит 6.'},
 'practice.age':{lesson:'L1',topic:'условия',first:'Какое сравнение подходит словам «не меньше»? Проверь, что будет ровно на границе.',second:'Сравнение должно включать граничный возраст. Проверь двоеточие после if и отступ перед print.'}
};
export function hintTask(taskId){const t=Object.hasOwn(tasks,taskId)?tasks[taskId]:null;return t?{task_id:taskId,lesson:t.lesson,topic:t.topic,has_analogy:!!t.analogy,has_solution:!!t.solution}:null;}
function validState(s){
 check(s&&typeof s.task_id==='string'&&s.task_id.length>0&&s.task_id.length<=100,'hint state task');
 check(['attempts_count','hints_used','max_level_used'].every(k=>integer(s[k]))&&s.max_level_used<=4,'hint state counters');
 check(s.max_level_used<=s.hints_used&&(s.hints_used===0)===(s.max_level_used===0),'hint state sequence');return s;
}
export function hintProgress(taskId,events=[]){
 check(typeof taskId==='string'&&taskId.length>0&&taskId.length<=100,'task ID');
 check(Array.isArray(events)&&events.length<=1000,'hint event count');const seen=new Map();
 for(const e of events){
  check(e&&typeof e==='object'&&['id','task_id'].every(k=>typeof e[k]==='string'&&e[k].length>0&&e[k].length<=100),'hint event identity');
  check(['attempt','hint'].includes(e.kind)&&['verified','pending','client_claim'].includes(e.status),'hint event type');
  check(e.kind==='attempt'?typeof e.passed==='boolean':Number.isInteger(e.level)&&e.level>=1&&e.level<=4,'hint event result');
  const n={id:e.id,task_id:e.task_id,kind:e.kind,status:e.status,...e.kind==='attempt'?{passed:e.passed}:{level:e.level}};
  check(!seen.has(n.id)||JSON.stringify(seen.get(n.id))===JSON.stringify(n),'hint event ID conflict');seen.set(n.id,n);
 }
 const es=[...seen.values()].filter(e=>e.task_id===taskId&&e.status==='verified');
 const hs=[...new Map(es.filter(e=>e.kind==='hint').map(e=>[e.level,e])).values()];
 const state={task_id:taskId,attempts_count:es.filter(e=>e.kind==='attempt').length,hints_used:hs.length,max_level_used:Math.max(0,...hs.map(e=>e.level))};
 for(let n=1;n<=state.max_level_used;n++)check(hs.some(e=>e.level===n),'hint state missing earlier level');
 return validState(state);
}
export function hint(req,ctx={}){
 const task=Object.hasOwn(tasks,req.task_id)?tasks[req.task_id]:null;
 if(task)check((!req.lesson||req.lesson===task.lesson)&&(!req.topic||req.topic===task.topic),'task context mismatch');
 const topic=task?.topic??req.topic,texts=Object.hasOwn(generic,topic)?generic[topic]:['Покажи конкретную строку, ожидаемый результат и фактический результат. Пока причина ошибки неизвестна.'];
 const s=ctx.hintState===undefined?null:validState(ctx.hintState),bound=!!s&&typeof req.task_id==='string'&&req.task_id===s.task_id;
 let level=1,reason=bound?'first_hint':'no_trusted_task_state';
 if(bound&&s.hints_used>=1){level=2;reason='direction';}
 if(bound&&s.hints_used>=2&&s.attempts_count>=1&&task?.analogy){level=3;reason='distinct_example';}
 if(bound&&s.hints_used>=3&&s.attempts_count>=2&&ctx.allowSolution===true&&task?.solution){level=4;reason='authorized_task_breakdown';}
 if(bound)level=Math.min(level,s.max_level_used+1); // Many attempts cannot skip a rung.
 const text=level===4?task.solution:level===3?task.analogy:level===2?(task?.second??texts[1]??texts[0]):task?.first??texts[0];
 reason=!bound?'no_trusted_task_state':level===4?'authorized_task_breakdown':level===3?'distinct_example':level===1?'first_hint':s.hints_used>=2&&s.attempts_count<1?'needs_verified_attempt':s.hints_used>=2&&!task?.analogy?'no_prepared_analogy':'direction';
 return {level,text,source:'catalogue',target_solution:level===4,task_id:req.task_id??null,level_source:'trusted_task_state',reason,...bound?{state_before:{...s}}:{}};
}
