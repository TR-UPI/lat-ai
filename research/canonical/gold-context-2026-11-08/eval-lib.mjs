export function makeInput(s,c){return 'ROLE: '+c.role+'\nMATERIALS:\n'+c.docs.map(id=>'['+id+']\n'+s.documents[id]).join('\n\n')+'\nTASK:\n'+c.input;}
export function parseAnswer(data,limit){
 const answer=(data.output||[]).filter(x=>x.type==='message').map(x=>x.content).join('\n');
 let parsed=null,jsonError=null;try{parsed=JSON.parse(answer)}catch(e){jsonError=e.message}
 return {answer,parsed,jsonValid:jsonError===null,jsonError,complete:!!answer && (data.stats?.total_output_tokens??0)<limit,stats:data.stats??null};
}
export function quizCheck(q,expected){
 const ok=Array.isArray(q?.options)&&q.options.length===4&&new Set(q.options).size===4&&Number.isInteger(q.correct_index)&&q.correct_index>=0&&q.correct_index<4&&q.options[q.correct_index]===expected&&q.options.filter(x=>x===expected).length===1;
 return {ok,expected,chosen:q?.options?.[q?.correct_index]??null};
}
export function tally(rows,planned){const passed=rows.filter(r=>r.pass===true&&!r.error).length;return {passed,total:planned,missing:planned-rows.length,rate:passed/planned};}
export function technicalCheck(c,a){
 const p=a.parsed, schema=[],objective=[];
 const str=x=>typeof x==='string'&&x.length>0;
 const arr=x=>Array.isArray(x)&&x.every(y=>typeof y==='string');
 const obj=x=>x!==null&&typeof x==='object'&&!Array.isArray(x);
 const need=(b,msg)=>{if(!b)schema.push(msg)};
 const validIds=new Set((c.events||[]).filter(e=>e.status==='verified').map(e=>e.id));
 const evidence=x=>{if(arr(x)&&x.some(id=>!validIds.has(id)))objective.push('unsupported evidence ID: '+x.filter(id=>!validIds.has(id)).join(','));};
 const sources=x=>{if(arr(x)&&x.some(id=>!c.docs.includes(id)))objective.push('unknown source ID');};
 if(!obj(p))return {schemaValid:false,objectiveValid:false,schemaErrors:['not an object'],objectiveErrors:[]};
 if(['explain','hint'].includes(c.role)){
  need(str(p.text),'text required');need(arr(p.sources),'sources required');sources(p.sources);
  if(c.role==='hint'){need(Number.isInteger(p.level),'level required');if(p.level!==c.hint_level)objective.push('wrong level');}
 }
 if(c.role==='quiz'){
  need(Array.isArray(p.questions),'questions required');
  if(Array.isArray(p.questions)){
   if(p.questions.length!==c.checks.length)objective.push('wrong question count');
   p.questions.forEach((q,i)=>{
    if(!obj(q)){schema.push('question not object');return;}
    need(str(q.prompt)&&str(q.explanation)&&str(q.source),'question fields required');
    need(arr(q.options)&&q.options.length===4,'four string options required');
    need(Number.isInteger(q.correct_index)&&q.correct_index>=0&&q.correct_index<4,'index must be 0..3');sources([q.source]);
    if(c.checks[i]){
     if(!q.prompt?.includes(c.checks[i].code))objective.push('source code changed/missing q'+i);
     const norm=x=>typeof x==='string'?x.replace(/\r?\n$/,''):x;
     if(!quizCheck({...q,options:q.options?.map(norm)},norm(c.checks[i].stdout)).ok)objective.push('wrong/nonunique answer q'+i);
    }
   });
  }
 }
 if(c.role==='profile'){
  need(Array.isArray(p.observations)&&arr(p.unknown)&&str(p.next_step),'profile fields required');
  for(const o of p.observations||[]){need(obj(o)&&str(o.concept)&&arr(o.evidence_ids)&&str(o.conclusion),'observation fields');evidence(o.evidence_ids);}
 }
 if(c.role==='plan'){
  need(Array.isArray(p.steps)&&str(p.reason),'plan fields required');
  if(Array.isArray(p.steps)){
   if(p.steps.length!==c.steps)objective.push('wrong step count');
   if(p.steps.reduce((s,x)=>s+(typeof x.minutes==='number'?x.minutes:0),0)!==c.minutes)objective.push('wrong total minutes');
   for(const x of p.steps){need(obj(x)&&str(x.topic)&&Number.isInteger(x.minutes)&&x.minutes>0&&str(x.activity)&&str(x.check)&&arr(x.evidence_ids),'step fields required');evidence(x.evidence_ids);}
  }
 }
 return {schemaValid:schema.length===0,objectiveValid:objective.length===0,schemaErrors:schema,objectiveErrors:objective};
}
