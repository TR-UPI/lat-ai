"""Synthetic end-to-end checks only, isolated runtime. Never emits auth tokens."""
import hashlib,json,pathlib,time,uuid
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path(r'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-08/shag-model-selection/outputs/document-pilot-2026-11-11')
OUT.mkdir(exist_ok=True)
API='http://127.0.0.1:8001/api/v1/'
opener=build_opener(ProxyHandler({}))
checks=[]
def call(path,body=None,token=None,method=None,binary=None,content_type=None):
    headers={}
    if token:headers['Authorization']='Bearer '+token
    data=None
    if body is not None:data=json.dumps(body,ensure_ascii=True).encode();headers['Content-Type']='application/json'
    if binary is not None:data=binary;headers['Content-Type']=content_type
    req=Request(API+path,data=data,headers=headers,method=method or ('POST' if data is not None else 'GET'))
    try:r=opener.open(req,timeout=30)
    except HTTPError as e:r=e
    with r:
        raw=r.read()
        try:result=json.loads(raw)
        except ValueError:result={'text':raw.decode(errors='replace')[:100]}
        return r.status,result
def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    (OUT/'live-checks.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
    if not condition:raise AssertionError(name)
    print(name, 'PASS',flush=True)
def upload(text,token,name):
    boundary='lad'+uuid.uuid4().hex
    data=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{name}.txt"\r\nContent-Type: text/plain\r\n\r\n'+text+f'\r\n--{boundary}--\r\n').encode()
    return call('documents/',token=token,binary=data,content_type='multipart/form-data; boundary='+boundary)

status,login=call('auth/token/',{'email':'review@lad-ai.local','password':'LadAI-Review-2026!'})
check('login',status==200);token=login['access']
email='privacy-'+uuid.uuid4().hex[:8]+'@lad-ai.local'
status,_=call('auth/register/',{'email':email,'password':'Synthetic-Pilot-2026!','display_name':'Privacy test'})
check('second_user',status==201)
_,second=call('auth/token/',{'email':email,'password':'Synthetic-Pilot-2026!'});other=second['access']
fixtures={name:(ROOT/f'tools/demo-materials/pilot-{name}.txt').read_text(encoding='utf-8') for name in ('history','biology','math')}
(OUT/'fixture-freeze.json').write_text(json.dumps({name:{'sha256':hashlib.sha256(text.encode()).hexdigest(),'characters':len(text),'mode':'test' if name=='math' else 'course'} for name,text in fixtures.items()},indent=2),encoding='utf-8')
records=[]
for name,source in fixtures.items():
    status,doc=upload(source,token,name);check(name+'_upload',status==201 and doc['status']=='ready')
    did=doc['id'];status,detail=call(f'documents/{did}/',token=token);check(name+'_text',detail['extracted_text']==source)
    check(name+'_private',call(f'documents/{did}/',token=other)[0]==404)
    body={'request_id':str(uuid.uuid4()),'mode':'test' if name=='math' else 'course','source_start':0,'source_end':len(source)}
    status,pack=call(f'documents/{did}/generate/',body,token);check(name+'_queued',status==202)
    pid=pack['id'];began=time.monotonic()
    check(name+'_pack_private',call(f'documents/packs/{pid}/',token=other)[0]==404)
    replay_status,replay=call(f'documents/{did}/generate/',body,token);check(name+'_replay',replay_status in (200,202) and replay['id']==pid)
    check(name+'_conflict',call(f'documents/{did}/generate/',{**body,'mode':'test' if body['mode']=='course' else 'course'},token)[0]==409)
    check(name+'_active_delete',call(f'documents/{did}/',token=token,method='DELETE')[0]==409)
    while time.monotonic()-began<240:
        status,pack=call(f'documents/packs/{pid}/',token=token)
        if pack['status'] not in ('queued','running'):break
        time.sleep(2)
    duration=time.monotonic()-began
    (OUT/f'live-{name}-public.json').write_text(json.dumps(pack,ensure_ascii=False,indent=2),encoding='utf-8')
    records.append({'topic':name,'document_id':did,'pack_id':pid,'status':pack['status'],'seconds':round(duration,3)})
    (OUT/'live-generations.json').write_text(json.dumps(records,indent=2),encoding='utf-8')
    check(name+'_ready',pack['status']=='ready')
    check(name+'_keys_hidden',all('correct_index' not in q and 'source_quote' not in q for q in pack['questions']))
    question=pack['questions'][0]
    status,hint=call(f'documents/packs/{pid}/hints/',{'question_id':question['id']},token)
    check(name+'_hint',status==200 and bool(hint.get('hint')))
    attempt={'request_id':str(uuid.uuid4()),'question_id':question['id'],'choice':0}
    status,answer=call(f'documents/packs/{pid}/attempts/',attempt,token)
    check(name+'_auto_points',status in (200,201) and answer['score'] in (0,1) and answer['progress']['answered']==1)
    _,duplicate=call(f'documents/packs/{pid}/attempts/',attempt,token)
    check(name+'_no_double_points',answer==duplicate)
    check(name+'_forged_points',call(f'documents/packs/{pid}/attempts/',{**attempt,'request_id':str(uuid.uuid4()),'score':100},token)[0]==400)
    check(name+'_attempt_private',call(f'documents/packs/{pid}/attempts/',{**attempt,'request_id':str(uuid.uuid4())},other)[0]==404)
print('LIVE COMPLETE',flush=True)
