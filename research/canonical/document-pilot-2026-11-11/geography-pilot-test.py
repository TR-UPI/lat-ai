import json,pathlib,sqlite3,time,uuid
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path(r'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-08/shag-model-selection/outputs/document-pilot-2026-11-11')
API='http://127.0.0.1:8001/api/v1/'
opener=build_opener(ProxyHandler({}))
def call(path,data=None,token=None,mime='application/json'):
    headers={'Content-Type':mime}
    if token:headers['Authorization']='Bearer '+token
    if isinstance(data,dict):data=json.dumps(data).encode()
    try:r=opener.open(Request(API+path,data=data,headers=headers),timeout=30)
    except HTTPError as error:r=error
    with r:return r.status,json.load(r)
_,login=call('auth/token/',{'email':'review@lad-ai.local','password':'LadAI-Review-2026!'})
token=login['access'];source=(ROOT/'tools/demo-materials/pilot-geography.txt').read_text(encoding='utf-8')
boundary='lad'+uuid.uuid4().hex
raw=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="geography.txt"\r\nContent-Type: text/plain\r\n\r\n'+source+f'\r\n--{boundary}--\r\n').encode()
status,doc=call('documents/',raw,token,'multipart/form-data; boundary='+boundary);assert status==201 and doc['status']=='ready'
_,pack=call(f"documents/{doc['id']}/generate/",{'request_id':str(uuid.uuid4()),'mode':'course','source_start':0,'source_end':len(source)},token)
pid=pack['id'];began=time.monotonic()
while time.monotonic()-began<240:
    _,pack=call(f'documents/packs/{pid}/',token=token)
    if pack['status'] not in ('running','queued'):break
    time.sleep(2)
report={'document_id':doc['id'],'pack_id':pid,'status':pack['status'],'seconds':round(time.monotonic()-began,3),'public_pack':pack,'attempts':[]}
(OUT/'live-geography.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
assert pack['status']=='ready',pack
# Private test-only key lookup proves scoring, not learner ability; GET above excludes keys.
with sqlite3.connect(str(ROOT/'.runtime/pilot-check/django.sqlite3')) as db:
    result=json.loads(db.execute('SELECT result FROM documents_studypack WHERE id=?',(pid,)).fetchone()[0])
assert all('correct_index' not in q for q in pack['questions'])
for index,question in enumerate(result['questions'],1):
    _,hint=call(f'documents/packs/{pid}/hints/',{'question_id':f'q{index}'},token)
    status,answer=call(f'documents/packs/{pid}/attempts/',{'request_id':str(uuid.uuid4()),'question_id':f'q{index}','choice':question['correct_index']},token)
    assert status==201 and answer['score']==1
    report['attempts'].append({'question':question,'hint':hint,'answer':answer})
_,finished=call(f'documents/packs/{pid}/',token=token)
assert finished['progress']=={'answered':3,'total':3,'score':3,'max_score':3,'percent':100.0,'completed':True}
# Latest answer replaces, rather than adds to, the same question's credit.
_,wrong=call(f'documents/packs/{pid}/attempts/',{'request_id':str(uuid.uuid4()),'question_id':'q1','choice':(result['questions'][0]['correct_index']+1)%4},token)
assert wrong['progress']['answered']==3 and wrong['progress']['score']==2
_,corrected=call(f'documents/packs/{pid}/attempts/',{'request_id':str(uuid.uuid4()),'question_id':'q1','choice':result['questions'][0]['correct_index']},token)
assert corrected['progress']['score']==3 and corrected['progress']['completed']
report['completed_progress']=corrected['progress'];report['latest_answer_replaces_score']=True
(OUT/'live-geography.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ('public_pack','attempts')},indent=2),flush=True)
