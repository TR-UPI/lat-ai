import test from 'node:test';
import assert from 'node:assert/strict';
import vm from 'node:vm';
import {readFileSync} from 'node:fs';
test('disabled local documents do not hide automatic lesson progress',async()=>{
 const source=readFileSync(new URL('../../../assets/app.js',import.meta.url),'utf8');
 const fn=source.split('\n').find(line=>line.includes('async function dashboard('));
 const context={user:{display_name:'Tester'},api:()=>({dashboard:async()=>({courses:[],total_courses:0}),attempts:async()=>[],documents:async()=>{throw Object.assign(Error('Documents disabled'),{status:503});}}),pageHead:()=>'',button:()=>'',icon:()=>'',escape:x=>x,format:x=>x,progressTable:()=>'<p>progress-ok</p>',attemptRows:()=>''};
 const html=await vm.runInNewContext(fn+'; dashboard()',context);
 assert.match(html,/progress-ok/);assert.match(html,/Материалы сейчас недоступны/);
});
