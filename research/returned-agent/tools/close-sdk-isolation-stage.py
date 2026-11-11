"""Preserve a blocked isolated-load investigation; never label read-only as load validation."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,zipfile
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/sdk-isolation-live-2026-11-11';PREV=ROOT/'outputs/ai-readiness-and-audit-summary-2026-11-11'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
enc=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()
def put(p,data):
    p=Path(p);p.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(data,str):data=data.encode()
    if p.exists():assert p.read_bytes()==data,str(p);return
    with p.open('xb') as f:f.write(data)
def save(p,v):put(p,enc(v))
def archive(p,files):
    mf={n:sha(f) for n,f in sorted(files.items())}
    if not p.exists():
        with zipfile.ZipFile(p,'x',zipfile.ZIP_DEFLATED) as z:
            for n,f in sorted(files.items()):z.write(f,n)
            z.writestr('ARCHIVE_MANIFEST.json',enc(mf))
    with zipfile.ZipFile(p) as z:
        assert set(z.namelist())==set(mf)|{'ARCHIVE_MANIFEST.json'} and z.testzip() is None
        assert json.loads(z.read('ARCHIVE_MANIFEST.json'))==mf
        for n,h in mf.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    return {'path':p.relative_to(OUT).as_posix(),'sha256':sha(p),'entries':len(mf)+1,'bytes':p.stat().st_size}
if not (OUT/'closure.json').exists():save(OUT/'closure.json',{'utc':datetime.now(timezone.utc).isoformat(),'requested_isolated_live':'BLOCKED_NOT_RUN','completed':'read-only SDK connection/disposal only'})
stamp=read(OUT/'closure.json')['utc'];previous=read(PREV/'backup/source-and-evidence-manifest.json');nav={'AGENTS.md','START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md'}
for n,h in previous.items():
    if n not in nav:assert sha(ROOT/n)==h,n
source=ROOT/'lat-ai';git=['git','-c','safe.directory='+source.as_posix(),'-C',str(source)]
names=subprocess.check_output(git+['ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
current={n:sha(source/n) for n in sorted(set(filter(None,names))) if (source/n).is_file()};assert current==read(PREV/'source-audit.json')['after_sha256']
before=read(OUT/'inventory-before.json');after=read(OUT/'inventory-after.json');summary=read(OUT/'readonly-live/summary.json')
assert summary['read_only_sdk_completed'] and summary['load_unload_inference_calls']==0 and summary['helper_load_exercised'] is False
assert summary['isolated_normal_load_status']=='NOT_RUN' and summary['forced_abort_status']=='NOT_RUN'
assert 'pass 14' in (OUT/'tests.log').read_text(encoding='utf-8-sig')
protocol=OUT/'readonly-protocol.json';assert sha(protocol)==Path(str(protocol)+'.sha256').read_text().strip()
for n,h in read(protocol)['files_sha256'].items():assert sha(ROOT/n)==h,n
comparison={key:before[key]==after[key] for key in ['runtime_processes','runtime_listeners','shared_settings_sha256','shared_models']};assert all(comparison.values())
save(OUT/'preservation-audit.json',{'utc':stamp,'read_only_snapshot_equal':comparison,'point_observations_not_continuous_proof':True,'project_files_unchanged':len(current),'protected_files_unchanged':sum(n.startswith(('backend/','assets/')) or n=='index.html' for n in current),'previous_immutable_files_unchanged':len(previous)-len(nav),'local_profile_unchanged':sha(ROOT/'work/local-pc/profile.json')==previous['work/local-pc/profile.json'],'after_sha256':current,'frozen_protocol_sha256':sha(protocol),'model_mutations':0})
note='''## SDK: изолированный load не выполнен · 11.11.2026

Подготовлен инженерный план, но отдельный runtime/profile/process containment
не подтверждён; свободной памяти также недостаточно для предварительного бюджета.
Полный normal-load/forced-abort = NOT_RUN/BLOCKED. Не запускать общий daemon up/down
под видом изоляции. Новые веса/пользователи/VM не устанавливались.
Выполнены только4 read-only SDK вызова к ОБЩЕМУ серверу, dispose,5s,exit0.
loadWithDeadline не вызывался; это не проверка прежнего load-deadline сбоя.
14tests=8декларативных правил+6helper mocks; они не доказывают изоляцию.
Общая модель не вызывалась/загружалась/выгружалась; PID/config/settings совпали
в точечных снимках. Source209/101 и прежние evidence неизменны.
Два отчёта/ответа Claude32/34 сверены, review описания, не кода.

[Отчёт](<E:/Startup Tau/outputs/sdk-isolation-live-2026-11-11/REPORT.txt>) ·
[План полной проверки](<E:/Startup Tau/outputs/sdk-isolation-live-2026-11-11/ISOLATED_LIVE_PLAN.txt>) ·
[Пакет человеку](<E:/Startup Tau/outputs/sdk-isolation-live-2026-11-11/LAT-AI-SDK-ISOLATION-HANDOFF-2026-11-11.zip>).

Для продолжения нужен подтверждённый независимый runtime и ресурсный бюджет.
Не повторять unknown load/POST, не удалять старые locks. Пилот/quality gates прежние.
Ниже исторические этапы; они не подтверждают текущую изоляцию SDK.

'''
for name in nav:
    p=ROOT/name;snap=OUT/'navigation-before'/name
    if not snap.exists():assert sha(p)==previous[name];put(snap,p.read_bytes())
    else:assert sha(snap)==previous[name]
for name in ['START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md']:
    p=ROOT/name;old=p.read_text(encoding='utf-8-sig')
    if note.split('\n')[0] in old:assert note in old;continue
    if old.startswith('# LAT AI'):title,rest=old.split('\n',1);text=title+'\n\n'+note+rest.lstrip('\n')
    else:text=note+old
    p.write_text(text,encoding='utf-8')
entry='\n- SDK isolation11.11: requested isolated normal load/forced abort BLOCKED_NOT_RUN; no verified separate runtime/profile/job containment, preliminary memory budget also unmet. Only explicit read-only SDK2.1.0 connection to SHARED server:4metadata calls/dispose/5s/exit0. Helper loadWithDeadline NOT exercised, no load/unload/inference.14tests=8declarative checklist+6existing helper mocks, not isolation proof; checklist never dispatches even all flags true. Five process identities/listeners/two settings hashes/model metadata equal at two observations, not continuous noninterference. New plan not operational launcher. No common model/process/profile changes,source209/101/previous evidence preserved. Claude2reports/replies32/34 description review. Reports/logs/handoffZIP/backup outputs/sdk-isolation-live-2026-11-11. Need independent runtime/resource budget to resume; no unknown retry/age-lock deletion; no new weights/VM/user installation; no commit/push.\n'
p=ROOT/'AGENTS.md'
if 'SDK isolation11.11:' not in p.read_text(encoding='utf-8-sig'):
    with p.open('a',encoding='utf-8') as f:f.write(entry)
else:assert entry in p.read_text(encoding='utf-8-sig')
save(OUT/'delivery-record.json',{'messages_sent':2,'completed_replies_read':2,'response_numbers':[32,34],'scope':'Description review, not code/ZIP audit','notes_sha256':sha(OUT/'CLAUDE_REVIEW.txt')})
anchors={'readonly_protocol':sha(protocol),'plan':sha(OUT/'ISOLATED_LIVE_PLAN.txt'),'helper_v2':sha(ROOT/'tools/sdk-load-with-deadline-v2.mjs')}
save(OUT/'ANCHORS.json',anchors)
human=OUT/'HUMAN_HANDOFF';put(human/'00_START.txt',(OUT/'HUMAN_NEXT_STEP.txt').read_bytes());put(human/'01_ISOLATED_LIVE_PLAN.txt',(OUT/'ISOLATED_LIVE_PLAN.txt').read_bytes())
save(human/'PACKAGE_INFO.json',{'requested_isolated_live':'NOT_RUN_BLOCKED','completed':'4 read-only SDK calls on SHARED runtime,dispose,5s,exit0','model_load_unload_inference':0,'anchors':anchors,'note':'Plan only, no launcher; SHA detects drift, not authenticity. No real human/student data.'})
manual=archive(OUT/'LAT-AI-SDK-ISOLATION-HANDOFF-2026-11-11.zip',{p.relative_to(human).as_posix():p for p in human.iterdir() if p.is_file()})
backup=OUT/'backup';backup.mkdir(exist_ok=True);bundle=backup/'LAT-AI-GIT.bundle'
if not bundle.exists():subprocess.run(git+['bundle','create',str(bundle),'--all'],check=True,capture_output=True)
v=subprocess.run(git+['bundle','verify',str(bundle)],check=True,capture_output=True);put(backup/'bundle-verify.log',v.stdout+v.stderr)
put(backup/'dirty.patch',subprocess.check_output(git+['diff','--binary','HEAD']));put(backup/'git-status.txt',subprocess.check_output(git+['status','--short']))
put(backup/'RESTORE.txt','Preservation only: clone bundle into NEW folder, overlay source ZIP, verify SHA. Do not apply dirty.patch over overlay or reset current work. Stores/locks in old evidence are inert, not live clones. No weights/databases/secrets. Archive CRC/per-entry SHA checked; no new full restore execution claimed. No commit/push.\n')
files={n:ROOT/n for n in previous}
for p in (ROOT/'tools').iterdir():
    if p.is_file():files[p.relative_to(ROOT).as_posix()]=p
for n in ['package-audit.json','postpackage-verification.json']:
    p=PREV/n;files[p.relative_to(ROOT).as_posix()]=p
for p in OUT.rglob('*'):
    if p.is_file() and 'backup' not in p.relative_to(OUT).parts and p.suffix not in {'.zip','.pyc'} and p.name not in ['stage-close.log','package-audit.json']:files[p.relative_to(ROOT).as_posix()]=p
assert not any(n.endswith(('.gguf','.db','.sqlite3','ipc-secret.txt')) for n in files)
save(backup/'source-and-evidence-manifest.json',{n:sha(p) for n,p in files.items()})
back=archive(backup/'LAT-AI-SDK-ISOLATION-SOURCE-EVIDENCE.zip',files)
save(OUT/'package-audit.json',{'manual':manual,'backup':back,'bundle_sha256':sha(bundle),'bundle_verified':True,'full_restore_executed_this_stage':False,'archive_crc_and_entry_sha_verified':True,'tests':14,'isolated_live':'NOT_RUN_BLOCKED','read_only_connection':'completed','no_commit_or_push':True})
print(json.dumps({'project_unchanged':len(current),'old_files_unchanged':len(previous)-len(nav),'isolated_live':'NOT_RUN_BLOCKED','manual':manual,'backup':back},ensure_ascii=False))
