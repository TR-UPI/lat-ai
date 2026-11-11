import {readFileSync,writeFileSync} from 'node:fs';
import {createHash} from 'node:crypto';
import {pathToFileURL} from 'node:url';
import {resolve} from 'node:path';
import {reviewSignals} from './review-signals.mjs';
export function reviewBatch(rows){
 if(!Array.isArray(rows)||!rows.length)throw Error('Non-empty review rows required');
 const seen=new Set();
 return rows.map(row=>{
  if(!row||Object.keys(row).sort().join(',')!=='id,series,student_answer,task_key,verification')throw Error('Only explicitly allowed model-input fields may enter the signal detector; no labels');
  if(typeof row.id!=='string'||!/^[-a-zA-Z0-9.]+$/.test(row.id)||![1,2,3].includes(row.series))throw Error('Invalid row identity');
  const key=row.series+':'+row.id;if(seen.has(key))throw Error('Duplicate row');seen.add(key);
  return {id:row.id,series:row.series,task_key:row.task_key,...reviewSignals(row)};
 });
}
if(process.argv[1]&&pathToFileURL(resolve(process.argv[1])).href===import.meta.url){
 const [input,output]=process.argv.slice(2);if(!output)throw Error('Usage: node review-signals-batch.mjs INPUT_JSON NEW_OUTPUT_JSON');
 const bytes=readFileSync(input),rows=reviewBatch(JSON.parse(bytes.toString('utf8').replace(/^\uFEFF/,'')));
 writeFileSync(output,JSON.stringify({input_sha256:createHash('sha256').update(bytes).digest('hex'),advisory_only:true,rows},null,2)+'\n',{flag:'wx'});
 console.log(JSON.stringify({rows:rows.length,signals:rows.filter(r=>r.status==='signals_found').length,technical_errors:rows.filter(r=>r.status==='technical_error').length,unsupported:rows.filter(r=>r.status==='unsupported_task').length}));
}
