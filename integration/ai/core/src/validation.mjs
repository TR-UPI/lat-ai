export function validateAnswer(raw,lesson,limit=192){
 const fail=m=>{throw Error(m);};
 if(!raw||typeof raw.answer!=='string'||raw.answer.length>5000)fail('answer length');
 if(raw.finish_reason!=='stop')fail('finish reason');
 if(!Number.isInteger(raw.stats?.total_output_tokens)||raw.stats.total_output_tokens>=limit||raw.stats.total_output_tokens<=0)fail('cap or unknown completion');
 if(raw.stats.reasoning_output_tokens!==0)fail('reasoning not off');
 const a=JSON.parse(raw.answer); // Deliberately no repair or markdown stripping.
 // Fixed, shallow schema: count parsed property tokens, including escaped key names.
 const propertyNames=[...raw.answer.matchAll(/"(?:[^"\\]|\\.)*"\s*:/g)].map(m=>JSON.parse(m[0].slice(0,m[0].lastIndexOf(':')).trim()));
 if(propertyNames.length!==2||new Set(propertyNames).size!==2)fail('duplicate or nested keys');
 if(!a||Array.isArray(a)||Object.keys(a).sort().join(',')!=='source_ids,text')fail('schema keys');
 if(typeof a.text!=='string'||a.text.trim().length<10||a.text.length>900)fail('text length');
 if(/[\p{Cf}\p{Cc}]/u.test(a.text.replace(/[\n\r\t]/g,''))||a.text.replace(/\s/gu,'').length<5)fail('invisible content');
 if(!Array.isArray(a.source_ids)||a.source_ids.length!==1||a.source_ids[0]!==lesson)fail('source ids');
 const words=a.text.toLowerCase().split(/\s+/),grams=new Map();
 for(let i=0;i+5<=words.length;i++){const g=words.slice(i,i+5).join(' ');grams.set(g,(grams.get(g)||0)+1);if(grams.get(g)>=3)fail('repetition');}
 if(/<think>|system_prompt|CANARY_|https?:\/\/|[\w.+-]+@[\w.-]+|парол|сексуаль|бомб|взлом/i.test(a.text))fail('unsafe output');
 return {text:a.text.trim(),source_ids:[...a.source_ids]};
}
