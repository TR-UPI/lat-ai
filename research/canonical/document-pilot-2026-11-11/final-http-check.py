import json,pathlib,re
from urllib.request import Request,build_opener,ProxyHandler
from urllib.error import HTTPError
ROOT=pathlib.Path(__file__).resolve().parents[1]
OUT=pathlib.Path(r'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-08/shag-model-selection/outputs/document-pilot-2026-11-11')
opener=build_opener(ProxyHandler({}))
def get(url,headers=None,data=None):
    try:r=opener.open(Request(url,headers=headers or {},data=data),timeout=5)
    except HTTPError as e:r=e
    with r:return r.status,r.read(),r.geturl()
_,raw,_=get('http://127.0.0.1:8001/api/v1/auth/token/',{'Content-Type':'application/json'},json.dumps({'email':'review@lad-ai.local','password':'LadAI-Review-2026!'}).encode())
token=json.loads(raw)['access'];headers={'Authorization':'Bearer '+token}
_,raw,_=get('http://127.0.0.1:8001/api/v1/documents/packs/8/',headers)
pack=json.loads(raw)
assert pack['source_excerpt']==(ROOT/'tools/demo-materials/pilot-geography.txt').read_text(encoding='utf-8')
assert pack['progress']['completed'] and pack['progress']['score']==3
assert all('correct_index' not in question for question in pack['questions'])
admin_status,admin,url=get('http://127.0.0.1:8001/admin/')
assert admin_status==200 and '/admin/login/' in url
css=re.search(rb'href="(/static/admin/css/[^\"]+)"',admin).group(1).decode()
assert get('http://127.0.0.1:8001'+css)[0]==200
private_statuses={path:get('http://127.0.0.1:5174/'+path)[0] for path in ['integration/ai/worker.mjs','.runtime/pilot-check/django.sqlite3','backend/manage.py']}
assert all(status in (403,404) for status in private_statuses.values())
assert get('http://127.0.0.1:8373/health')[0]==401
health={}
for label,port,runtime in [('new',8373,ROOT/'.runtime/pilot-check'),('original',8372,pathlib.Path(r'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-08/shag-model-selection/work/tf11kit/app/.runtime/i02'))]:
    secret=(runtime/'ipc-secret.txt').read_text(encoding='utf-8').strip()
    status,raw,_=get(f'http://127.0.0.1:{port}/health',{'X-LAD-IPC':secret})
    health[label]=json.loads(raw);assert status==200 and not health[label]['tutor']['quarantined']
assert health['new']['model']['id']==health['original']['model']['id']
report={'source_excerpt_preserved':True,'progress_after_restart':pack['progress'],'admin_login_and_css':True,
        'static_private_paths_denied':private_statuses,'worker_unauthenticated_denied':True,
        'original_and_new_health':health,'test_only_raw_model_capture_disabled':True}
(OUT/'final-http.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Final API, progress, admin/CSS, static privacy and original model health PASS')
