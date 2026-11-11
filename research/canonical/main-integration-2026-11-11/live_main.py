from pathlib import Path
import json, sqlite3, uuid, time, re
from urllib.request import Request, build_opener, ProxyHandler
from urllib.error import HTTPError
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
MAIN=ROOT/'work/lat-ai'
RUNTIME=ROOT/'work/tf11kit/app/.runtime/i02'
API='http://127.0.0.1:8000/api/v1/'
opener=build_opener(ProxyHandler({}))
checks=[]
def save(name,data): (OUT/name).write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8')
def request(url,body=None,token=None,raw=None,content_type=None):
    headers={}
    if token: headers['Authorization']='Bearer '+token
    if body is not None: raw=json.dumps(body).encode();headers['Content-Type']='application/json'
    if content_type: headers['Content-Type']=content_type
    try: response=opener.open(Request(url,headers=headers,data=raw),timeout=25)
    except HTTPError as error: response=error
    with response:
        data=response.read()
        try: decoded=json.loads(data)
        except ValueError: decoded=data.decode(errors='replace')
        return response.status,decoded,response.geturl()
def api(path,*args,**kwargs): return request(API+path,*args,**kwargs)[:2]
def check(name,condition):
    checks.append({'name':name,'passed':bool(condition)})
    save('live-checks.json',checks)
    print(name+': '+('PASS' if condition else 'FAIL'),flush=True)
    if not condition: raise AssertionError(name)

# Compare all existing user/learning rows against the migration baseline before synthetic writes.
backup=ROOT/'work/main-integration-private-backup-final/active-tf11kit/django.sqlite3'
with sqlite3.connect(backup.as_uri()+'?mode=ro',uri=True) as old, sqlite3.connect((RUNTIME/'django.sqlite3').as_uri()+'?mode=ro',uri=True) as current:
    preserved={}
    for (table,) in old.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('django_migrations','django_content_type','auth_permission')").fetchall():
        cols=[r[1] for r in old.execute('PRAGMA table_info("'+table+'")')]
        sql='SELECT '+','.join('"'+x+'"' for x in cols)+' FROM "'+table+'"'
        before=sorted(old.execute(sql).fetchall(),key=repr)
        after=sorted(current.execute(sql).fetchall(),key=repr)
        check('preserved_'+table,before==after)
        preserved[table]=len(before)
    check('live_database_integrity',current.execute('PRAGMA integrity_check').fetchall()==[('ok',)] and not current.execute('PRAGMA foreign_key_check').fetchall())
save('live-preserved-tables.json',preserved)
check('main_site_source',request('http://127.0.0.1:5173/assets/app.js')[1]==(MAIN/'assets/app.js').read_bytes().decode('utf-8'))
for path in ['.runtime/main-local.json','integration/ai/core/data/assessment-rubrics.json','backend/manage.py','media/private.txt']:
    check('private_'+path,request('http://127.0.0.1:5173/'+path)[0] in (403,404))
check('worker_requires_secret',request('http://127.0.0.1:8372/health')[0]==401)
status,html,url=request('http://127.0.0.1:8000/admin/')
check('admin_login',status==200 and '/admin/login/' in url)
css=re.search(r'href="(/static/admin/css/[^\"]+)"',html).group(1)
check('admin_css',request('http://127.0.0.1:8000'+css)[0]==200)
status,login=api('auth/token/',{'email':'review@lad-ai.local','password':'LadAI-Review-2026!'})
check('previous_account_login',status==200)
old_token=login['access']
check('previous_courses',api('courses/',token=old_token)[0]==200)
check('previous_attempts',api('progress/attempts/',token=old_token)[0]==200)
email='main-smoke-'+uuid.uuid4().hex[:8]+'@lad-ai.local'
password='Main-integration-2026!'
check('synthetic_user_created',api('auth/register/',{'email':email,'password':password,'display_name':'MAIN integration synthetic'})[0]==201)
status,login=api('auth/token/',{'email':email,'password':password})
check('synthetic_login',status==200)
token=login['access']
contexts=json.loads((RUNTIME/'seed.json').read_text())['contexts']
answers={
 'L1.types.1':'Оба значения "3" и "2" являются строками str. Знак + соединяет эти строки, а не складывает числа. Программа выводит 32.',
 'L1.condition.1':'x равно 2, поэтому условие x == 2 истинно. Выполняется ветка if, ветка else пропускается. Программа выводит да.',
 'L2.range.1':'range(2, 5) задаёт значения 2, 3, 4. Правая граница 5 не входит. Цикл печатает 2, 3, 4, каждое число на своей отдельной строке.',
 'L2.accumulator.1':'s создаётся равной 0 один раз до цикла и не сбрасывается внутри. При i=1 сумма становится 1, при i=2 — 3, при i=3 — 6. Итог 6. print без отступа находится после цикла и печатает итог один раз.'}
grades=[]
for context in contexts:
    start=time.monotonic()
    status,result=api('progress/attempts/',{'exercise':context['exercise_id'],'answer':answers[context['task_key']]},token)
    grades.append({'task':context['task_key'],'http_status':status,'seconds':round(time.monotonic()-start,3),'result':result})
    save('live-assessments.json',grades)
    check('assessment_record_'+context['task_key'],status==201 and result.get('status') in ('auto_checked','auto_unavailable','auto_pending'))
    print('ASSESS '+context['task_key']+' '+str(result.get('status'))+' score='+str(result.get('score')),flush=True)
status,progress=api('progress/',token=token)
check('progress_api',status==200)
save('live-python-progress.json',progress)
c=contexts[0]
status,hint=api('tutor/ask/',{'contract_version':'1.0','request_id':str(uuid.uuid4()),'action':'hint','question':'Подскажи следующий шаг','course_id':c['course_id'],'lesson_id':c['lesson_id'],'exercise_id':c['exercise_id']},token)
save('live-python-hint.json',{'http':status,'body':hint})
check('hint_after_attempt',status==200 and hint.get('outcome')=='answer')

# One synthetic document verifies the newly integrated background worker and scoring.
source=(MAIN/'tools/demo-materials/pilot-history.txt').read_text(encoding='utf-8')
boundary='main'+uuid.uuid4().hex
raw=(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="main-smoke-history.txt"\r\nContent-Type: text/plain\r\n\r\n'+source+f'\r\n--{boundary}--\r\n').encode()
status,doc=api('documents/',token=token,raw=raw,content_type='multipart/form-data; boundary='+boundary)
check('document_upload',status==201 and doc['status']=='ready')
check('document_private',api(f'documents/{doc["id"]}/',token=old_token)[0]==404)
generation={'request_id':str(uuid.uuid4()),'mode':'test','source_start':0,'source_end':len(source)}
status,pack=api(f'documents/{doc["id"]}/generate/',generation,token)
check('document_queued',status==202)
pid=pack['id']; start=time.monotonic()
while time.monotonic()-start<195:
    _,pack=api(f'documents/packs/{pid}/',token=token)
    if pack['status'] not in ('queued','running'): break
    time.sleep(2)
save('live-document.json',{'seconds':round(time.monotonic()-start,3),'pack':pack})
check('document_processed_by_jobs',pack['status']=='ready')
check('keys_hidden',all('correct_index' not in q for q in pack['questions']))
check('source_excerpt',pack['source_excerpt']==source)
attempt={'request_id':str(uuid.uuid4()),'question_id':pack['questions'][0]['id'],'choice':0}
status,result=api(f'documents/packs/{pid}/attempts/',attempt,token)
check('document_auto_points',status in (200,201) and result['score'] in (0,1) and result['progress']['answered']==1)
check('document_replay_no_double_score',api(f'documents/packs/{pid}/attempts/',attempt,token)[1]==result)
check('document_other_owner_denied',api(f'documents/packs/{pid}/',token=old_token)[0]==404)
save('live-summary.json',{'checks':len(checks),'all_passed':all(x['passed'] for x in checks),'auto_checked':sum(g['result'].get('status')=='auto_checked' for g in grades),'assessment_count':len(grades),'synthetic_user':email,'document_pack':pid,'note':'Synthetic integration checks, not accuracy evaluation; no hidden failed repetitions'})
print('MAIN LIVE SMOKE COMPLETE',flush=True)
