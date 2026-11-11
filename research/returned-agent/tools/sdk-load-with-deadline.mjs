// Diagnostic tooling only. Do not use an uncancellable AbortSignal.timeout for
// SDK 2.1.0 load(): its retained abort listener may send cancel after load/dispose.
export async function loadWithDeadline(client,key,options={},timeoutMs=120000){
 if(!Number.isFinite(timeoutMs)||timeoutMs<=0)throw Error('Positive load deadline required');
 if(Object.hasOwn(options,'signal'))throw Error('Wrapper owns the load abort signal');
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(new Error('SDK load deadline exceeded')),timeoutMs);
 try{return await client.llm.load(key,{...options,signal:controller.signal});}
 finally{clearTimeout(timer);}
}
