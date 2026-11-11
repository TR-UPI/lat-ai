import {rangeFacts} from './range-facts.mjs';

// A deliberately closed integer language. No eval, Python execution, calls,
// attribute access, implicit initial values, or partial-program execution.
const ID='[A-Za-z_][A-Za-z_0-9]{0,23}';
const NUM='[+-]?(?:0|[1-9][0-9]{0,6})';
const ATOM=`(?:${NUM}|${ID})`;
const ASSIGN=new RegExp(`^(${ID})[ ]*=[ ]*(${ATOM})(?:[ ]*([+-])[ ]*(${ATOM}))?$`);
const reserved=new Set('False None True __debug__ and as assert async await break class continue def del elif else except finally for from global if import in is lambda nonlocal not or pass raise return try while with yield range print'.split(' '));
const validName=x=>new RegExp(`^${ID}$`).test(x)&&!reserved.has(x);
function atom(x){if(new RegExp(`^${NUM}$`).test(x)&&Math.abs(Number(x))<=1e6)return Number(x);if(validName(x))return x;throw Error('atom');}
function assignment(s){const m=ASSIGN.exec(s);if(!m||!validName(m[1]))throw Error('assignment');return {target:m[1],left:atom(m[2]),op:m[3],right:m[4]===undefined?undefined:atom(m[4]),expression:s};}
function value(x,env){if(typeof x==='number')return x;if(!Object.hasOwn(env,x))throw Error('unknown variable');return env[x];}
function compute(a,env){const l=value(a.left,env),r=a.op?value(a.right,env):0;const n=a.op==='+'?l+r:a.op==='-'?l-r:l;if(!Number.isSafeInteger(n)||Math.abs(n)>1e9)throw Error('number bound');return n;}
function fact(a){return {expression:a.expression,target:a.target,effect:!a.op?(typeof a.left==='number'?'replace_with_constant':'replace_with_current_value'):a.left===a.target?(a.op==='+'?'add_to_previous':'subtract_from_previous'):'replace_with_expression',rhs_uses_previous_target:a.left===a.target||a.right===a.target,scope:'one_assignment_only',assumption:'defined_integer_operands'};}

export function traceProgram(code,{includeStructure=false}={}){try{
 if(typeof code!=='string'||code.length>3000||/[^\x20-\x7e\n]/.test(code))return null;
 const lines=code.split('\n').filter(x=>x.trim());if(!lines.length||lines.length>30)return null;
 const nodes=[];let loops=0;
 function simple(s){const p=new RegExp(`^print[ ]*\\([ ]*(${ATOM})[ ]*\\)$`).exec(s);return p?{print:atom(p[1])}:{assign:assignment(s)};}
 for(let i=0;i<lines.length;i++){
  const line=lines[i];if(line.startsWith(' '))return null;
  const loop=new RegExp(`^for[ ]+(${ID})[ ]+in[ ]+(range[ ]*\\([^()]*\\))[ ]*:$`).exec(line);
  if(!loop){nodes.push(simple(line.trimEnd()));continue;}
  if(++loops>1||!validName(loop[1]))return null;
  const ranges=rangeFacts(loop[2]);if(ranges.length!==1||!Array.isArray(ranges[0].values))return null;
  const body=[];let indent=null;
  while(i+1<lines.length&&lines[i+1].startsWith(' ')){
   const raw=lines[++i],n=raw.length-raw.trimStart().length;
   if(indent===null)indent=n;if(n!==indent)return null;
   body.push(simple(raw.trim()));
  }
  if(!body.length)return null;nodes.push({loop:loop[1],values:ranges[0].values,body});
 }
 const env=Object.create(null),steps=[],output=[];let count=0;
 function run(node){if(++count>100)throw Error('step bound');if(node.assign){const a=node.assign;env[a.target]=compute(a,env);steps.push({expression:a.expression,after:{...env}});}else{output.push(value(node.print,env));}}
 for(const n of nodes){if(n.loop){for(const v of n.values){env[n.loop]=v;for(const b of n.body)run(b);}}else run(n);}
 const command=n=>n.assign?{code:n.assign.expression,effect:fact(n.assign).effect}:{print:n.print};
 const structure=includeStructure?nodes.map(n=>n.loop?{variable:n.loop,values:n.values,body:n.body.map(command)}:command(n)):undefined;
 return {scope:'provided_code_only',assumption:'fresh_integer_environment_standard_range_print',steps,final:{...env},output,...(structure?{structure}:{})};
 }catch{return null;}}

// Symbolic composition is restricted to two explicit adjacent assignments to
// the SAME target. It states a conditional local result, never a loop result.
function compose(a,b){
 if(a.target!==b.target||a.op||typeof a.left!=='number')return null;
 const val=x=>x===a.target?a.left:x;
 const l=val(b.left),r=val(b.right);
 let result;
 if(!b.op)result=String(l);
 else if(typeof l==='number'&&typeof r==='number')result=String(b.op==='+'?l+r:l-r);
 else if(b.op==='+'&&l===0)result=String(r);
 else if(r===0)result=String(l);
 else result=`${l}${b.op}${r}`;
 return {scope:'conditional_sequence_only',condition:'these_two_assignments_run_consecutively_with_defined_integer_operands',target:a.target,final_expression:result,depends_on_previous_target:false,program_result:'unknown'};
}
export function stateFacts(text,{includeStructure=false}={}){
 const empty={program_result:'unknown',assignments:[]};
 if(typeof text!=='string'||text.length>4000)return empty;
 if(text.includes('```')){
  const blocks=[...text.matchAll(/```(?:python)?\n([^`]+)\n```/g)];
  if(blocks.length!==1||text.split('```').length!==3)return empty;
  const trace=traceProgram(blocks[0][1],{includeStructure});return trace?{...empty,trace}:empty;
 }
 const re=new RegExp(`(${ID})[ ]*=[ ]*(${ATOM})(?:[ ]*[+-][ ]*${ATOM})?`,'g'),found=[];
 for(const m of text.matchAll(re)){
  const before=text.slice(0,m.index),after=text.slice(m.index+m[0].length);
  // Reject matching a suffix/prefix of a larger Python expression.
  if(/[\p{ID_Continue}.]$/u.test(before)||/[.=+*/%<>!:\-][ ]*$/.test(before)||/^\p{ID_Continue}/u.test(after)||/^[ ]*(?:[=+*/%<>!()\[\]:&|^@\\-]|\.[ ]*[A-Za-z_0-9]|[A-Za-z_0-9])/.test(after))continue;
  // A comma can continue a Python tuple; accept it as prose punctuation only
  // when followed by a Russian word (e.g. explicit «, затем»).
  if(/^[ ]*,/.test(after)&&!/^,[ ]+[А-Яа-яЁё]/u.test(after.trimStart()))continue;
  try{found.push({a:assignment(m[0]),start:m.index,end:m.index+m[0].length});}catch{}
  if(found.length>4)return empty;
 }
 const out={...empty,assignments:found.map(x=>fact(x.a))};
 if(found.length===2){const [a,b]=found,between=text.slice(a.end,b.start);if(/^[ ]*(?:,[ ]*(?:а[ ]+)?(?:затем|потом)[ ]+|;[ ]*(?:(?:затем|потом)[ ]+)?)[ ]*$/iu.test(between)){
  out.sequence=compose(a.a,b.a);
  // A final constant assignment is independent of any preceding value.
  if(!out.sequence&&!b.a.op&&typeof b.a.left==='number'&&a.a.target===b.a.target)out.sequence={scope:'conditional_sequence_only',condition:'these_two_assignments_run_consecutively_with_defined_integer_operands',target:b.a.target,final_expression:String(b.a.left),depends_on_previous_target:false,program_result:'unknown'};
  if(!out.sequence)delete out.sequence;
 }}
 return out;
}
