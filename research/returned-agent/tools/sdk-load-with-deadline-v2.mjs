// Future diagnostic runs only. V1 and its completed live protocol remain immutable.
export const MAX_LOAD_DEADLINE_MS=2147483647;
export async function loadWithDeadline(client,key,options={},timeoutMs=120000){
 if(!Number.isInteger(timeoutMs)||timeoutMs<1||timeoutMs>MAX_LOAD_DEADLINE_MS)throw RangeError('Load deadline must be an integer from 1 to 2147483647 ms');
 if(Object.hasOwn(options,'signal'))throw Error('Wrapper owns the load abort signal');
 const controller=new AbortController();
 const timer=setTimeout(()=>controller.abort(new Error('SDK load deadline exceeded')),timeoutMs);
 try{return await client.llm.load(key,{...options,signal:controller.signal});}
 finally{clearTimeout(timer);}
}
