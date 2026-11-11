"""Preserve the frozen offline recovery stage. No commit, push or model activity."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,zipfile,importlib.util,os,re

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/audit-recovery-2026-11-11'
PREV=ROOT/'outputs/manual-audit-intake-2026-11-11'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
encoded=lambda v:(json.dumps(v,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode()

def put(path,data):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    if isinstance(data,str):data=data.encode()
    if path.exists():
        assert path.read_bytes()==data,('existing_artifact_changed',str(path));return
    with path.open('xb') as f:f.write(data)
def save(path,value):put(path,encoded(value))
def archive(path,files):
    manifest={n:sha(p) for n,p in sorted(files.items())}
    if not path.exists():
        with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
            for n,p in sorted(files.items()):z.write(p,n)
            z.writestr('ARCHIVE_MANIFEST.json',encoded(manifest))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(manifest)|{'ARCHIVE_MANIFEST.json'}
        assert json.loads(z.read('ARCHIVE_MANIFEST.json'))==manifest
        for n,h in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
    return {'path':path.relative_to(OUT).as_posix(),'sha256':sha(path),'verified_entries':len(manifest)+1,'bytes':path.stat().st_size}

closure=OUT/'closure.json'
if not closure.exists():save(closure,{'started_utc':datetime.now(timezone.utc).isoformat(),'scope':'AI offline recovery only; no actual human returns or inference'})
stamp=read(closure)['started_utc']
previous=read(PREV/'backup/source-and-evidence-manifest.json')
mutable={'AGENTS.md','START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md'}
retained={n:h for n,h in previous.items() if n.startswith(('tools/','outputs/')) and n not in mutable}
for n,h in retained.items():assert sha(ROOT/n)==h,n
source=ROOT/'lat-ai';git=['git','-c','safe.directory='+source.as_posix(),'-C',str(source)]
names=subprocess.check_output(git+['ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
current={n:sha(source/n) for n in sorted(set(filter(None,names))) if (source/n).is_file()}
assert current==read(PREV/'source-audit.json')['after_sha256']
assert sha(ROOT/'work/local-pc/profile.json')==previous['work/local-pc/profile.json']
spec=importlib.util.spec_from_file_location('recovery_close',ROOT/'tools/recover-audit-store.py');r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)
protocol=OUT/'recovery-protocol.json';r.verify(protocol)
assert 'Ran 49 tests' in (OUT/'tests-core-final-49.log').read_text(encoding='utf-8-sig')
assert 'Ran 12 tests' in (OUT/'tests-triage-final-12.log').read_text(encoding='utf-8-sig')
summary=read(OUT/'TECHNICAL_FIXTURE/SUMMARY.json')
assert summary['actual_human_reviews']==0 and summary['model_calls']==0 and len(summary['commands'])==19
assert all(x['returncode']==x['expected'] for x in summary['commands'])
assert summary['original_partial_attempt_unchanged'] and summary['baseline_marker_and_files_unchanged']

# Keep raw logs intact. Context-bearing copies are for viewing and quotation.
for p in sorted((OUT/'TECHNICAL_FIXTURE').glob('*.log')):
    raw=p.read_text(encoding='utf-8-sig')
    try:value=json.loads(raw)
    except ValueError:value=raw
    save(OUT/'TECHNICAL_FIXTURE/ANNOTATED_OUTPUTS'/(p.stem+'.json'),{'scope':'TECHNICAL_FIXTURE_ONLY_NOT_REAL_HUMAN_DATA','actual_human_reviews':0,'model_calls':0,'raw_log':p.name,'raw_sha256':sha(p),'output':value})

nav='''## Восстановление приёма и история доставки · 11.11.2026

Готовы отдельные offline recovery/amendment, защищённый приём и read-only диагностика.
Исходные попытки/квитанции сохраняются; поправки добавляются цепочкой, effective_status
учитывает всю историю. Постоянный idle-barrier блокирует старые prepare/receive на
переведённом store. Не удалять intake.lock: owned_idle_barrier — штатное состояние.
Неизвестный старый lock, пропавший барьер, неполная выдача/входы — ручные инциденты.
61test (49+12), differential24 внутри49 и19 CLI-команд на TECHNICAL_FIXTURE прошли.
Четыре отчёта/четыре ответа Claude прочитаны, условия сверены; это review описания.
Промпты,209исходников/101backend+frontend,старые tools/evidence и профиль прежние.
Модель не вызывалась; реальных решений людей0. Формальная проверка не допуск качества.

[Кратко](<E:/Startup Tau/outputs/audit-recovery-2026-11-11/ONE_PAGE.txt>) ·
[Оператору](<E:/Startup Tau/outputs/audit-recovery-2026-11-11/OPERATOR_GUIDE.txt>) ·
[Отчёт](<E:/Startup Tau/outputs/audit-recovery-2026-11-11/REPORT.txt>) ·
[ZIP для ручной работы](<E:/Startup Tau/outputs/audit-recovery-2026-11-11/LAT-AI-HUMAN-RECOVERY-AND-PILOT-2026-11-11.zip>).

Следующий значимый шаг: реальные обезличенные ответы/люди/согласия и смысловая проверка.
Координатор разраб 1 П, план12.11.2026. T01/S02/D01/D02 открыты. Ниже история этапов;
прежнее «нет repair/amendment» относится к frozen v1, который не изменялся.

'''
for name in sorted(mutable):
    p=ROOT/name;snapshot=OUT/'navigation-before'/name
    if not snapshot.exists():
        assert sha(p)==previous[name],name
        put(snapshot,p.read_bytes())
    else:assert sha(snapshot)==previous[name]
for name in ['START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md']:
    p=ROOT/name;old=p.read_text(encoding='utf-8-sig')
    if nav.split('\n')[0] in old:assert nav in old;continue
    if old.startswith('# LAT AI'):
        title,rest=old.split('\n',1);new=title+'\n\n'+nav+rest.lstrip('\n')
    else:new=nav+old
    p.write_text(new,encoding='utf-8')
entry='\n- Audit recovery11.11: frozen standalone recover-audit-store.py + Windows audit-store-lease.py + read-only triage-audit-recovery.py. Explicit finalize_issue/recover_attempt/recover_execution/amend_delivery, append-only plans/receipts/events, conservative exposure/current reader; no gold/score changes.61tests(49+12),differential24inside49,19CLI TECHNICAL_FIXTURE commands passed; originals unchanged. Persistent owned_idle_barrier intentionally remains; NEVER delete intake.lock. Old prepare/receive blocked on adopted store; missing initialized barrier/legacy unknown lock/incomplete assignment/different inputs stay manual. Same-host fixed local NTFS process-crash only; no power-loss/clone/host-move/authentication guarantee. Four actual Claude reports/replies read (18/20/22/24), description review not code audit. Source209/protected101/old immutable tools+evidence/profile unchanged,no modelPOST/commit/push/stand restart. Human ZIP has no store/locks/maps; backup stores are inert evidence, not live clones. Current reports/protocol/human ZIP/backup:outputs/audit-recovery-2026-11-11. Realpilot/people/T01/S02/D01/D02 remain open; coordinator разраб 1 П,start12.11.2026.\n'
agents=ROOT/'AGENTS.md'
if 'Audit recovery11.11:' not in agents.read_text(encoding='utf-8-sig'):
    with agents.open('a',encoding='utf-8') as f:f.write(entry)
else:assert entry in agents.read_text(encoding='utf-8-sig')

protected=[n for n in current if n.startswith(('backend/','assets/')) or n=='index.html']
for n,h in retained.items():assert sha(ROOT/n)==h,n
save(OUT/'source-audit.json',{'utc':stamp,'project_files_unchanged':len(current),'protected_backend_frontend_files':len(protected),'old_immutable_tool_and_evidence_files_unchanged':len(retained),'mutable_navigation_updated':sorted(mutable),'navigation_before_sha256':{n:previous[n] for n in mutable},'navigation_after_sha256':{n:sha(ROOT/n) for n in mutable},'local_profile_unchanged':True,'frozen_recovery_protocol_verified':True,'new_model_calls':0,'after_sha256':current})
save(OUT/'delivery-record.json',{'recorded_utc':stamp,'chat':'https://claude.ai/chat/bf69c588-0773-495f-8cbe-6167148049f6','messages_sent':4,'completed_replies_read':4,'response_numbers':[18,20,22,24],'evidence':'Native Claude AX user messages and completed responses, no screenshot proof claimed.','scope':'Description review only; not source-code/ZIP audit','notes_sha256':sha(OUT/'CLAUDE_REVIEW.txt')})
save(OUT/'operating-addendum.json',{'created_utc':stamp,'recovery_protocol_sha256':sha(protocol),'documents_sha256':{n:sha(OUT/n) for n in ['REPORT.txt','ONE_PAGE.txt','OPERATOR_GUIDE.txt','MANUAL_INCIDENT.txt','HUMAN_RULES.txt','CLAUDE_REVIEW.txt','WORKLOG.txt']},'demo_script_sha256':sha(ROOT/'tools/demo-audit-recovery.py'),'status':'Pre-data; human returns0, no model quality claims. Persistent idle barrier, source snapshots and current status required.'})
put(OUT/'operating-addendum.json.sha256',sha(OUT/'operating-addendum.json')+'\n')

human=OUT/'LAT-AI-HUMAN-RECOVERY-AND-PILOT';human.mkdir(exist_ok=True)
for name,target in [('ONE_PAGE.txt','00_START.txt'),('MANUAL_INCIDENT.txt','01_MANUAL_INCIDENT.txt'),('HUMAN_RULES.txt','02_RETURN_AND_DELIVERY_RULES.txt')]:put(human/target,(OUT/name).read_bytes())
put(human/'03_TECHNICAL_FIXTURE_SUMMARY.json',(OUT/'TECHNICAL_FIXTURE/SUMMARY.json').read_bytes())
for p in sorted((ROOT/'outputs/ai-pilot-integrity-2026-11-11/LAT-AI-PILOT-START-2026-11-12').glob('*.txt')):put(human/'PILOT'/p.name,p.read_bytes())
save(human/'PACKAGE_INFO.json',{'protocol_revision':read(protocol)['revision'],'protocol_sha256':sha(protocol),'applies_to':'Every file in ARCHIVE_MANIFEST.json','recipient':'Coordinator only; do not forward to blind reviewers or use their distribution channel.','not_for_execution':True,'store_clone_supported':False,'contains_store_or_locks':False,'actual_human_returns':0})
humanfiles={p.relative_to(human).as_posix():p for p in human.rglob('*') if p.is_file()}
prohibited=[]
guid=re.compile(r'\b[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}\b')
for name,p in humanfiles.items():
    text=p.read_text(encoding='utf-8-sig')
    patterns=[r'(?i)[A-Z]:[\\/]',r'(?i)/(?:Users|home)/',r'(?i)"(?:pid|creation_filetime|machine_id_sha256|files_seen_sha256|seed|stratum|private_map)"\s*:',guid]
    if any(re.search(pattern,text) for pattern in patterns):prohibited.append(name)
    for value in [os.environ.get('USERNAME'),os.environ.get('COMPUTERNAME')]:
        if value and len(value)>3 and value.casefold() in text.casefold():prohibited.append(name)
    assert Path(name).name not in ['STORE.json','intake.lock','BARRIER.json','HOST.json','PRIVATE_DELIVERY.json','PRIVATE_COORDINATOR.json']
assert not prohibited,prohibited
save(OUT/'human-package-screening.json',{'files_checked':len(humanfiles),'actual_local_user_host_paths_or_GUIDs_found':False,'prohibited_structured_seed_map_exposure_fields_found':False,'raw_logs_store_locks_included':False,'source_documents_not_redacted':True,'rules_and_historical_dataset_hashes_are_not_seed_or_exposure_material':'Six coordinator pilot documents inspected; no actual assignment/private map included.','protocol_sha256':sha(protocol)})
manual=archive(OUT/'LAT-AI-HUMAN-RECOVERY-AND-PILOT-2026-11-11.zip',humanfiles)

backup=OUT/'backup';backup.mkdir(exist_ok=True);bundle=backup/'LAT-AI-GIT.bundle'
if not bundle.exists():subprocess.run(git+['bundle','create',str(bundle),'--all'],check=True,capture_output=True)
verified=subprocess.run(git+['bundle','verify',str(bundle)],check=True,capture_output=True)
put(backup/'bundle-verify.log',verified.stdout+verified.stderr)
put(backup/'dirty.patch',subprocess.check_output(git+['diff','--binary','HEAD']))
put(backup/'git-status.txt',subprocess.check_output(git+['status','--short']))
put(backup/'RESTORE.txt','Source preservation: clone Git bundle into a NEW directory, overlay lat-ai/ from source/evidence ZIP, verify SHA. Do not apply dirty.patch on top of overlay or reset the present tree. No weights, databases or secrets. Historical/TECHNICAL_FIXTURE stores are inert evidence only, NOT live store clones; their absolute-path/host bindings intentionally prevent resuming at another location. Live-store disaster/host migration is a separate manual procedure. No commit/push.\n')
manifestfile=backup/'source-and-evidence-manifest.json'
if manifestfile.exists():files={n:ROOT/n for n in read(manifestfile)}
else:
    files={n:ROOT/n for n in previous if (ROOT/n).is_file()}
    for p in (ROOT/'tools').iterdir():
        if p.is_file():files[p.relative_to(ROOT).as_posix()]=p
    for p in OUT.rglob('*'):
        if p.is_file() and 'backup' not in p.relative_to(OUT).parts and p.suffix not in {'.zip','.pyc'} and p.name not in {'stage-close.log','package-audit.json','postpackage-verification.json'}:files[p.relative_to(ROOT).as_posix()]=p
    assert not any(n.endswith(('.gguf','.sqlite3','.db','ipc-secret.txt')) for n in files)
    save(manifestfile,{n:sha(p) for n,p in files.items()})
for n,h in read(manifestfile).items():assert sha(ROOT/n)==h,n
back=archive(backup/'LAT-AI-RECOVERY-SOURCE-AND-EVIDENCE.zip',files)
save(OUT/'package-audit.json',{'utc':stamp,'manual':manual,'backup':back,'bundle_sha256':sha(bundle),'bundle_verified':True,'frozen_protocol_sha256':sha(protocol),'tests':{'core':49,'triage':12,'differential_variants_within_core':24,'cli_commands':19},'no_commit_or_push':True})
print(json.dumps({'project_unchanged':len(current),'protected_unchanged':len(protected),'old_immutable_files_unchanged':len(retained),'manual':manual,'backup':back},ensure_ascii=False))
