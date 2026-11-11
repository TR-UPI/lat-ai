from pathlib import Path
import json,hashlib,re
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1];MAIN=ROOT/'work/lat-ai';RUNTIME=ROOT/'work/tf11kit/app/.runtime/i02'
opener=build_opener(ProxyHandler({}))
def get(url,headers=None):
    try:r=opener.open(Request(url,headers=headers or {}),timeout=10)
    except HTTPError as e:r=e
    with r:return r.status,r.read()
checks=[]
for rel in ['assets/app.js','assets/styles.css']:
    status,data=get('http://127.0.0.1:5173/'+rel)
    assert status==200 and data==(MAIN/rel).read_bytes(),rel
    checks.append(rel+' served exact updated bytes')
for rel in ['.runtime/main-local.json','integration/ai/study-schema.mjs']:
    status,_=get('http://127.0.0.1:5173/'+rel)
    assert status in (403,404),rel
    checks.append(rel+' private')
status,html=get('http://127.0.0.1:8000/admin/login/')
assert status==200 and b'csrfmiddlewaretoken' in html
assert get('http://127.0.0.1:8000/static/admin/css/base.css')[0]==200
assert get('http://127.0.0.1:8000/api/v1/documents/')[0]==401
checks+=['Django admin login and CSS available','documents require auth']
status,raw=get('http://127.0.0.1:8372/health',{'X-LAD-IPC':(RUNTIME/'ipc-secret.txt').read_text().strip()})
health=json.loads(raw)
assert status==200 and health['tutor']['ready'] and not health['model']['quarantined']
for item in json.loads((OUT/'promotion-applied.json').read_text()):
    assert hashlib.sha256((MAIN/item['path']).read_bytes()).hexdigest()==item['after_sha256']
checks.append('all promoted hashes match')
result={'checks':checks,'health':health,'processes':json.loads((RUNTIME/'pilot-processes.json').read_text())}
(OUT/'main-smoke.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({'checks':len(checks),'ready':True}))
