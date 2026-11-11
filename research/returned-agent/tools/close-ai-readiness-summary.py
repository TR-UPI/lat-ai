"""Preserve this offline AI stage without modifying frozen predecessors or Git history."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,zipfile,importlib.util,os,re
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/ai-readiness-and-audit-summary-2026-11-11'
PREV=ROOT/'outputs/audit-recovery-2026-11-11'
NAV={'AGENTS.md','START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md'}
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
encoded=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def put(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(data,str):data=data.encode()
    if p.exists():assert p.read_bytes()==data,('existing_artifact_changed',str(p));return
    with p.open('xb') as f:f.write(data)
def save(p,v):put(p,encoded(v))
def load(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
def archive(path,files):
    manifest={n:sha(p) for n,p in sorted(files.items())}
    if not path.exists():
        with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
            for n,p in sorted(files.items()):z.write(p,n)
            z.writestr('ARCHIVE_MANIFEST.json',encoded(manifest))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None and set(z.namelist())==set(manifest)|{'ARCHIVE_MANIFEST.json'}
        assert json.loads(z.read('ARCHIVE_MANIFEST.json'))==manifest
        for n,h in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    return {'path':path.relative_to(OUT).as_posix(),'sha256':sha(path),'verified_entries':len(manifest)+1,'bytes':path.stat().st_size}

if not (OUT/'closure.json').exists():save(OUT/'closure.json',{'started_utc':datetime.now(timezone.utc).isoformat(),'scope':'Offline AI audit summary/readiness; real human returns0; model mutations0'})
stamp=read(OUT/'closure.json')['started_utc'];previous=read(PREV/'backup/source-and-evidence-manifest.json')
retained={n:h for n,h in previous.items() if n not in NAV}
for n,h in retained.items():assert sha(ROOT/n)==h,n
source=ROOT/'lat-ai';git=['git','-c','safe.directory='+source.as_posix(),'-C',str(source)]
names=subprocess.check_output(git+['ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
current={n:sha(source/n) for n in sorted(set(filter(None,names))) if (source/n).is_file()}
assert current==read(PREV/'source-audit.json')['after_sha256']
assert sha(ROOT/'work/local-pc/profile.json')==previous['work/local-pc/profile.json']
summary=load('summary_closure',ROOT/'tools/summarize-audit-returns.py');summary.verify(OUT/'summary-protocol.json')
doctor=load('readiness_closure',ROOT/'tools/check-ai-readiness.py');assert doctor.run(OUT/'readiness-protocol.json')['technical_integrity_passed']
assert 'Ran 24 tests' in (OUT/'tests-summary-final-24.log').read_text(encoding='utf-8-sig')
assert 'Ran 5 tests' in (OUT/'tests-readiness-final-5.log').read_text(encoding='utf-8-sig')
demo=read(OUT/'TECHNICAL_FIXTURE/DEMO_RESULT.json')
assert demo['actual_human_returns']==0 and demo['model_calls']==0 and len(demo['commands'])==6
assert all(x['returncode']==x['expected'] for x in demo['commands'])
assert demo['index_permutation_summary_byte_identical'] and demo['later_amendment_detected_as_stale'] and demo['old_export_preserved']
anchors={n:sha(OUT/n) for n in ['summary-protocol.json','readiness-protocol.json','TECHNICAL_FIXTURE/SUMMARY_AFTER/MANIFEST.json','READINESS.json']}
save(OUT/'ANCHORS.json',{'sha256':anchors,'note':'Keep independently from the ZIP. Hashes detect drift, not authenticity.'})
put(OUT/'REPORT_ANCHORS.txt','LAT AI · корневые SHA256\n'+''.join(n+'  '+h+'\n' for n,h in anchors.items())+'Хранить отдельно от ZIP; SHA не доказывают подлинность.\n')

nav='''## Сводка ручного аудита и offline preflight · 11.11.2026

Новые standalone summarize-audit-returns.py и check-ai-readiness.py заморожены.
Сводка сохраняет пропуски/исключения/решения, сверяет текущую историю доставки,
не объединяет кейсы по тексту, не создаёт gold или балл. verify-export: 0 current,
3 stale,4 corrupt,2 invalid/unavailable; 0 не означает правильность оценок.
24+5 тестов и6 CLI-команд TECHNICAL_FIXTURE прошли; реальных возвратов0.
Целостность:209 исходников/2090 прежних файлов/6 протоколов пройдена. Runtime:
только read-only наблюдение, текущие ready/idle/ownership не заявляются; inference0.
Промпты/backend/frontend/локальный профиль и старые frozen-файлы сохранены.
Три отчёта/ответа Claude сверены; это review описания, код/ZIP ему не передавались.

[Отчёт](<E:/Startup Tau/outputs/ai-readiness-and-audit-summary-2026-11-11/REPORT.txt>) ·
[Оператору](<E:/Startup Tau/outputs/ai-readiness-and-audit-summary-2026-11-11/OPERATOR_GUIDE.txt>) ·
[Открытые задачи](<E:/Startup Tau/outputs/ai-readiness-and-audit-summary-2026-11-11/ROADMAP_COVERAGE.txt>) ·
[Пакет человеку](<E:/Startup Tau/outputs/ai-readiness-and-audit-summary-2026-11-11/LAT-AI-HUMAN-AUDIT-READINESS-2026-11-11.zip>).

Сводку не выдавать разметчикам до/во время слепой разметки; human_reason проверить
на персональные данные. Пилот/люди/T01/S02/D01/D02 открыты, координатор разраб 1 П,
план12.11.2026. SDK v2 isolated live/abort terminal proof остаётся отдельной задачей.
Ниже — история предыдущих этапов, не утверждение текущего состояния стенда.

'''
for name in NAV:
    p=ROOT/name;snap=OUT/'navigation-before'/name
    if not snap.exists():assert sha(p)==previous[name],name;put(snap,p.read_bytes())
    else:assert sha(snap)==previous[name],name
for name in ['START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md']:
    p=ROOT/name;old=p.read_text(encoding='utf-8-sig')
    if nav.split('\n')[0] in old:assert nav in old;continue
    if old.startswith('# LAT AI'):title,rest=old.split('\n',1);new=title+'\n\n'+nav+rest.lstrip('\n')
    else:new=nav+old
    p.write_text(new,encoding='utf-8')
entry='\n- Audit summary/readiness11.11: frozen standalone summarize-audit-returns.py + check-ai-readiness.py; explicit index, exact render-manifest+audit_id identity, uncertainty/forced fields not agreement, missing/excluded returns retained, exposure history/current status, no gold/score/adjudication. 24+5tests and6CLI TECHNICAL_FIXTURE passed; actual human returns0. verify-export0current/3stale/4corrupt/2invalid; never overwrite prior export.209source/101protected/2090previousimmutablefiles/profile unchanged.6protocols offline integrity passed, no model inference/load/unload.3read-only model GETs: ID matched historical stand restoration record, current origin/ready/idle/ownership NOT established. SDKv2 isolated live/abort terminal proof still open; no unknown POST retry/lock age deletion. Claude3actual reports/replies26/28/30, description review only, code/ZIP not shared. Reports/humanZIP/backup:outputs/ai-readiness-and-audit-summary-2026-11-11. Summary is private coordinator post-label material; never share with blind reviewers before/during labels; check human_reason for personal data. Humanpilot/T01/S02/D01/D02 open, coordinator разраб 1 П,start12.11.2026. No commit/push.\n'
p=ROOT/'AGENTS.md'
if 'Audit summary/readiness11.11:' not in p.read_text(encoding='utf-8-sig'):
    with p.open('a',encoding='utf-8') as f:f.write(entry)
else:assert entry in p.read_text(encoding='utf-8-sig')
protected=[n for n in current if n.startswith(('backend/','assets/')) or n=='index.html']
for n,h in retained.items():assert sha(ROOT/n)==h,n
save(OUT/'source-audit.json',{'utc':stamp,'project_files_unchanged':len(current),'protected_backend_frontend_files':len(protected),'prior_immutable_files_unchanged':len(retained),'mutable_navigation_updated':sorted(NAV),'navigation_before_sha256':{n:previous[n] for n in NAV},'navigation_after_sha256':{n:sha(ROOT/n) for n in NAV},'local_profile_unchanged':True,'frozen_protocols_verified':True,'new_model_calls':0,'read_only_runtime_gets':3,'after_sha256':current})
save(OUT/'delivery-record.json',{'utc':stamp,'chat':'https://claude.ai/chat/bf69c588-0773-495f-8cbe-6167148049f6','messages_sent':3,'completed_replies_read':3,'response_numbers':[26,28,30],'evidence':'Native AX observed delivered messages/completed replies; no screenshot/code/ZIP audit claimed','notes_sha256':sha(OUT/'CLAUDE_REVIEW.txt')})

human=OUT/'LAT-AI-HUMAN-AUDIT-READINESS'
for name,target in [('ONE_PAGE.txt','00_START.txt'),('HUMAN_RULES.txt','01_HUMAN_RULES.txt'),('ROADMAP_COVERAGE.txt','02_ROADMAP_COVERAGE.txt')]:put(human/target,(OUT/name).read_bytes())
# Context-bearing copy; original raw demo evidence remains unchanged.
annotated={**demo,'scope':'TECHNICAL_FIXTURE_ONLY_NO_REAL_HUMANS_OR_PILOT','commands':[{'mode':'TECHNICAL_FIXTURE',**v} for v in demo['commands']]}
save(human/'03_TECHNICAL_FIXTURE_SUMMARY.json',annotated)
save(human/'PACKAGE_INFO.json',{'recipient':'Coordinator only; not blind-reviewer material','file_integrity':'passed:209 project files,6 protocols','runtime':'observation without conclusion; current state not claimed','sha256_anchors':anchors,'authenticity_note':'SHA in same ZIP detects drift only; keep external report anchors separately.','actual_human_returns':0,'actual_pilot':False,'tests':29,'fixture_cli_commands':6,'no_store_locks_runtime_ids_or_human_reason_values':True})
humanfiles={p.relative_to(human).as_posix():p for p in human.rglob('*') if p.is_file()}
patterns=[r'(?i)[A-Z]:[\\/]',r'(?i)/(?:Users|home)/',r'(?i)"(?:pid|creation_filetime|machine_id_sha256|MachineGuid|files_seen_sha256|seed|stratum|private_map|human_reason)"\s*:',r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b']
for n,p in humanfiles.items():
    text=p.read_text(encoding='utf-8-sig');assert not any(re.search(pattern,text) for pattern in patterns),n
    for value in [os.environ.get('USERNAME'),os.environ.get('COMPUTERNAME')]:
        assert not value or len(value)<=3 or value.casefold() not in text.casefold(),n
    assert Path(n).name not in ['STORE.json','intake.lock','BARRIER.json','HOST.json','PRIVATE_DELIVERY.json','PRIVATE_COORDINATOR.json'],n
save(OUT/'human-package-screening.json',{'files_checked':len(humanfiles),'prohibited_local_paths_host_user_guids_pid_fields_found':False,'raw_logs_store_locks_or_human_reason_values_included':False,'redactions':[],'transformation':'Technical demo copy adds context labels to every command; original unchanged.'})
manual=archive(OUT/'LAT-AI-HUMAN-AUDIT-READINESS-2026-11-11.zip',humanfiles)

backup=OUT/'backup';backup.mkdir(exist_ok=True);bundle=backup/'LAT-AI-GIT.bundle'
if not bundle.exists():subprocess.run(git+['bundle','create',str(bundle),'--all'],check=True,capture_output=True)
verified=subprocess.run(git+['bundle','verify',str(bundle)],check=True,capture_output=True);put(backup/'bundle-verify.log',verified.stdout+verified.stderr)
put(backup/'dirty.patch',subprocess.check_output(git+['diff','--binary','HEAD']))
put(backup/'git-status.txt',subprocess.check_output(git+['status','--short']))
put(backup/'RESTORE.txt','Clone bundle into a NEW directory; overlay lat-ai source/evidence ZIP; verify SHA. Do not apply dirty.patch on top or reset current work. No weights/databases/secrets. Included historical stores/locks are inert evidence, NOT live clones; host/path bindings prevent migration. Previous recovery archive included only to reproduce offline integrity preflight. Do not execute copied store or old launcher. No commit/push.\n')
mf=backup/'source-and-evidence-manifest.json'
if mf.exists():files={n:ROOT/n for n in read(mf)}
else:
    files={n:ROOT/n for n in previous}
    for n in doctor.FILES:
        files[n]=ROOT/n
        side=Path(str(ROOT/n)+'.sha256')
        if side.is_file():files[side.relative_to(ROOT).as_posix()]=side
    previouszip=PREV/read(PREV/'package-audit.json')['backup']['path'];files[previouszip.relative_to(ROOT).as_posix()]=previouszip
    for p in (ROOT/'tools').iterdir():
        if p.is_file():files[p.relative_to(ROOT).as_posix()]=p
    for p in OUT.rglob('*'):
        if p.is_file() and 'backup' not in p.relative_to(OUT).parts and p.suffix not in {'.zip','.pyc'} and p.name not in {'stage-close.log','package-audit.json','postpackage-verification.json','restore-check.log'}:files[p.relative_to(ROOT).as_posix()]=p
    assert not any(n.endswith(('.gguf','.sqlite3','.db','ipc-secret.txt')) for n in files)
    save(mf,{n:sha(p) for n,p in files.items()})
for n,h in read(mf).items():assert sha(ROOT/n)==h,n
back=archive(backup/'LAT-AI-READINESS-SOURCE-AND-EVIDENCE.zip',files)
save(OUT/'package-audit.json',{'utc':stamp,'manual':manual,'backup':back,'bundle_sha256':sha(bundle),'bundle_verified':True,'anchors':anchors,'tests':29,'fixture_cli_commands':6,'no_commit_or_push':True})
print(json.dumps({'project_unchanged':len(current),'protected_unchanged':len(protected),'prior_immutable_files_unchanged':len(retained),'manual':manual,'backup':back},ensure_ascii=False))
