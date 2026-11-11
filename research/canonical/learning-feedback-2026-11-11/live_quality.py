from pathlib import Path
import json,uuid,time,sys,sqlite3
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
STAGE=ROOT/'work/learning-feedback-stage/LAD-AI-Document-Pilot'
run=OUT/(sys.argv[1] if len(sys.argv)>1 else 'live-round1')
run.mkdir(exist_ok=False)
api='http://127.0.0.1:8002/api/v1/'
opener=build_opener(ProxyHandler({}))
def save(name,value): (run/name).write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
def call(path,body=None,token=None,raw=None,ctype=None):
    headers={}
    if token:headers['Authorization']='Bearer '+token
    if body is not None:raw=json.dumps(body).encode();headers['Content-Type']='application/json'
    if ctype:headers['Content-Type']=ctype
    try:r=opener.open(Request(api+path,data=raw,headers=headers),timeout=25)
    except HTTPError as e:r=e
    with r:return r.status,json.load(r)
status,login=call('auth/token/',{'email':'review@lad-ai.local','password':'LadAI-Review-2026!'})
assert status==200
token=login['access']
source=(OUT/(sys.argv[2] if len(sys.argv)>2 else 'sql-fixture.txt')).read_text(encoding='utf-8')
boundary='review'+uuid.uuid4().hex
filename='water-feedback.txt' if len(sys.argv)>2 else 'SQL-transactions-feedback.txt'
raw=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{filename}"\r\nContent-Type: text/plain\r\n\r\n'+source+f'\r\n--{boundary}--\r\n').encode()
status,doc=call('documents/',token=token,raw=raw,ctype='multipart/form-data; boundary='+boundary)
assert status==201
body={'request_id':str(uuid.uuid4()),'mode':'test','source_start':0,'source_end':len(source)}
save('request.json',{'document':doc['id'],'generation':body})
status,pack=call(f'documents/{doc["id"]}/generate/',body,token)
assert status==202
pid=pack['id'];start=time.monotonic()
while time.monotonic()-start<195:
    _,pack=call(f'documents/packs/{pid}/',token=token)
    if pack['status'] not in ('queued','running'):break
    time.sleep(2)
save('pack.json',{'seconds':round(time.monotonic()-start,3),'pack':pack})
print('Pack '+str(pid)+' '+pack['status']+' '+str(round(time.monotonic()-start,2))+'s',flush=True)
if pack['status']!='ready':raise SystemExit(2)
with sqlite3.connect((STAGE/'.runtime/test-feedback/django.sqlite3').as_uri()+'?mode=ro',uri=True) as db:
    private=json.loads(db.execute('SELECT result FROM documents_studypack WHERE id=?',(pid,)).fetchone()[0])
save('synthetic-private-result.json',private)
results=[]
for index,q in enumerate(pack['questions']):
    assert 'correct_index' not in q and 'option_explanations' not in q
    _,hint=call(f'documents/packs/{pid}/hints/',{'question_id':q['id']},token)
    correct=private['questions'][index]['correct_index'];wrong=(correct+1)%4
    request={'request_id':str(uuid.uuid4()),'question_id':q['id'],'choice':wrong}
    status,answer=call(f'documents/packs/{pid}/attempts/',request,token)
    assert status==201 and answer['score']==0
    assert answer['feedback']==private['questions'][index]['option_explanations'][wrong]
    assert answer['correct_option']==q['options'][correct]
    assert call(f'documents/packs/{pid}/attempts/',request,token)[1]==answer
    results.append({'question':q,'hint':hint,'wrong_feedback':answer})
    print('Q'+str(index+1)+' hint: '+hint['hint'],flush=True)
save('feedback.json',results)
q=pack['questions'][0]
choice=private['questions'][0]['correct_index']
request={'request_id':str(uuid.uuid4()),'question_id':q['id'],'choice':choice}
status,correct=call(f'documents/packs/{pid}/attempts/',request,token)
assert status==201 and correct['score']==1
assert correct['feedback']==private['questions'][0]['option_explanations'][choice]
assert call(f'documents/packs/{pid}/attempts/',request,token)[1]==correct
save('correct-feedback.json',correct)
context=json.loads((STAGE/'.runtime/test-feedback/seed.json').read_text())['contexts'][0]
status,partial=call('progress/attempts/',{'exercise':context['exercise_id'],'answer':'Оба значения являются строками. Программа выводит 32.'},token)
save('python-partial.json',{'http_status':status,'attempt':partial})
print('Python report status '+str(partial.get('status'))+' score '+str(partial.get('score')),flush=True)
