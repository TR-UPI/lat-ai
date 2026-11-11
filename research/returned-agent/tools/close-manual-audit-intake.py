"""Audit and preserve completed offline intake stage, without changing frozen sources."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,zipfile,shutil,importlib.util
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/manual-audit-intake-2026-11-11'
PREV=ROOT/'outputs/review-card-fragments-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def put(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:f.write(v)
def archive(path,files):
    manifest={n:sha(p) for n,p in sorted(files.items())}
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
        z.writestr('ARCHIVE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None and set(z.namelist())==set(manifest)|{'ARCHIVE_MANIFEST.json'}
        for n,h in manifest.items():assert hashlib.sha256(z.read(n)).hexdigest()==h
    return {'path':path.relative_to(OUT).as_posix(),'sha256':sha(path),'verified_entries':len(manifest)+1}
stamp=datetime.now(timezone.utc).isoformat()
previous=read(PREV/'backup/source-and-evidence-manifest.json')
source=ROOT/'lat-ai';git=['git','-c','safe.directory='+source.as_posix(),'-C',str(source)]
names=subprocess.check_output(git+['ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
current={n:sha(source/n) for n in sorted(set(filter(None,names))) if (source/n).is_file()}
assert current==read(PREV/'source-audit.json')['after_sha256']
retained={n:h for n,h in previous.items() if n.startswith(('tools/','outputs/'))}
for n,h in retained.items():assert sha(ROOT/n)==h,n
assert sha(ROOT/'work/local-pc/profile.json')==previous['work/local-pc/profile.json']
spec=importlib.util.spec_from_file_location('intake',ROOT/'tools/receive-review-cards.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
module.verify_protocol(OUT/'intake-protocol.json')
put(OUT/'FILLING_GUIDE.txt',module.GUIDE)
save(OUT/'operating-addendum.json',{'created_utc':stamp,'intake_protocol_sha256':sha(OUT/'intake-protocol.json'),'documents_sha256':{n:sha(OUT/n) for n in ['COORDINATOR_GUIDE.txt','FILLING_GUIDE.txt','RECOVERY_RUNBOOK.txt','CLAUDE_REVIEW.txt']},'status':'Pre-data operating record. No repair/amendment in v1; receipt validation is not registration without accepted marker. No real human returns.'})
put(OUT/'operating-addendum.json.sha256',sha(OUT/'operating-addendum.json')+'\n')
protected=[n for n in current if n.startswith(('backend/','assets/')) or n=='index.html']
save(OUT/'source-audit.json',{'utc':stamp,'project_files_unchanged':len(current),'protected_backend_frontend_files':len(protected),'old_tool_and_evidence_files_unchanged':len(retained),'intake_protocol_verified':True,'old_presentation_dependencies_verified':True,'local_profile_unchanged':True,'new_model_calls':0,'after_sha256':current})
save(OUT/'delivery-record.json',{'recorded_utc':stamp,'chat':'https://claude.ai/chat/bf69c588-0773-495f-8cbe-6167148049f6','messages_sent':2,'completed_replies_read':2,'verification':'Native Claude AX user messages and completed responses Message14/16. No screenshot proof claimed.','review_scope':'Descriptions only, not repository/code audit','notes_sha256':sha(OUT/'CLAUDE_REVIEW.txt')})
summary=read(OUT/'TECHNICAL_FIXTURE/SUMMARY.json')
assert summary['actual_human_reviews']==0 and summary['incomplete_rejected'] and summary['complete_fixture_validated'] and summary['identical_repeat_deduplicated']
nav='''## Приём заполненных карточек аудита · 11.11.2026

Готов отдельный offline prepare/receive: назначение и SHA выдачи, обязательные
человеческие поля, неизменность ответов/цитат, UUID/UTC/exposure, квитанции и
реестр выдачи/принятия. Uncertain допустим; расхождения идут на ручной разбор.
16 тестов и сквозной искусственный пример прошли, CLI exit2/0 проверены.
Две рецензии Claude прочитаны, замечания сверены и учтены; это рецензия описания.
209 исходников/101 защищённый файл, прежние инструменты и frozen evidence
сохранены, новых modelPOST нет. Первичные слепые метки/баллы не меняются.
Реальных человеческих возвратов:0. Validation_passed не gold; принятие требует
marker accepted. Автоматического repair/amendment нет, один store на кампанию.

[Приём и инструкции](<E:/Startup Tau/outputs/manual-audit-intake-2026-11-11/COORDINATOR_GUIDE.txt>) ·
[Отчёт](<E:/Startup Tau/outputs/manual-audit-intake-2026-11-11/REPORT.txt>) ·
[ZIP координатору](<E:/Startup Tau/outputs/manual-audit-intake-2026-11-11/LAT-AI-MANUAL-AUDIT-INTAKE-2026-11-11.zip>).

Далее история этапов. Реальные люди/данные/согласия и разбор смысла остаются
следующим шагом; T01/S02/D01/D02 открыты. Промпты, бэк и фронт не менять.

'''
for name in ['START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md']:
    p=ROOT/name;old=p.read_text(encoding='utf-8-sig');assert nav.split('\n')[0] not in old
    if old.startswith('# LAT AI'):
        title,rest=old.split('\n',1);new=title+'\n\n'+nav+rest.lstrip('\n')
    else:new=nav+old
    p.write_text(new,encoding='utf-8')
with (ROOT/'AGENTS.md').open('a',encoding='utf-8') as f:f.write('\n- Manual audit intake11.11: separate tools/receive-review-cards.py prepare/receive, strict full package/types/immutable fields/UUID/UTC/exposure; uncertain and human-verifier disagreements go to followup, no gold/score mutation.16tests plus end-to-end TECHNICAL_FIXTURE and CLIexit2/0 passed. New intake-protocol+operating-addendum frozen. Single storeUUID issued registry blocks same content/reviewer reissue (ignores opaque IDs/order), accepted marker binds receipt; repeated bytes idempotent, no automatic replacement/repair/amendment. Pending reservations require coordinator+AI-maintainer manual incident, no age steal/newstore bypass; partial overlaps/crossstore not globally deduped. Actual human returns0. Two actual Claude reviews read, descriptions not code audit. Source209/101 and old tools/evidence unchanged,no modelPOST/commit/push. Current report/guides/manualZIP/backup outputs/manual-audit-intake-2026-11-11. Realpilot/people and T01/S02/D01/D02 open; no prompts/backend/frontend changes.\n')
put(OUT/'WORKLOG.txt',f'''LAT AI offline intake stage; recorded {stamp}
Read current roadmap/navigation/AGENTS, frozen presentation/sampler contracts.
Added standalone intake with strict duplicate-key/nonfinite/type-aware parsing,
five editable fields, full assignment/immutable content, identity/time/exposure.
Initial11tests passed. Added accepted marker integrity;12tests passed.
Sent actual stage report to authorized Claude desktop, read response14.
Added explicit human/verifier matrix+followup, finite numeric/unpaired surrogate
checks, content/reviewer issuance registry, store binding.16tests passed.
One test bytes literal emitted SyntaxWarning; changed to raw bytes literal,
retained warning log; final16tests passed without warning. No production change.
Frozen intake protocol. Generated technical fixture through actual old renderer
then new prepare/receive: reject incomplete, validate uncertain complete, dedup repeat.
CLI repeated rejection returned2, repeated valid receipt0; logs preserved.
Sent final description, read completed response16; no blocking remarks subject
to documented limits. Added coordinator/runbook, ops addendum and report.
Report-only patch with delete/add same target was rejected before write; report
written via UTF-8 PowerShell here-string. No evidence/production files deleted.
Audited all209project/protected101 and old tools/evidence; no model calls.
Current navigation updated; manualsZIP and bundle/source-evidenceZIP CRC+SHA checked.
Commands: python tools/test-receive-review-cards.py; python ... freeze newprotocol;
python tools/demo-manual-audit-intake.py; python ... receive (fixture only);
python tools/close-manual-audit-intake.py. No commit/push/stand restart/old lock changes.
''')
human=OUT/'LAT-AI-MANUAL-AUDIT-INTAKE';human.mkdir()
put(human/'00_START.txt','''LAT AI — приём ручного аудита, пакет координатору
Начать с CURRENT_REPORT.txt и COORDINATOR_GUIDE.txt. FILLING_GUIDE.txt предназначен
рецензенту после первичной слепой разметки; RECOVERY_RUNBOOK.txt — для остановок.
PILOT — прежние правила сбора/согласий/обезличивания/людей. Разраб 1 П, план12.11.2026.
TECHNICAL_EXAMPLES — только искусственные примеры, не настоящие решения людей.
UUID111.../222... вымышлены; исходные карточки из примеров не выдавать как реальные.
Реальную выдачу создаёт prepare из готового rendered package в новом каталоге.
Человеку передать только reviewer/, координаторские receipt/assignment/store отдельно.
ПолныйZIP не предназначен для первоначальной слепой разметки.
Реальных возвратов пока нет; formal validation не подтверждает правильность/допуск.
''')
for name in ['REPORT.txt','COORDINATOR_GUIDE.txt','FILLING_GUIDE.txt','RECOVERY_RUNBOOK.txt','CLAUDE_REVIEW.txt']:
    shutil.copy2(OUT/name,human/('CURRENT_REPORT.txt' if name=='REPORT.txt' else name))
examples={'RETURN_UNFILLED_FIXTURE.json':'assignment/reviewer/cards.json','DELIVERY_TEMPLATE_FIXTURE.json':'assignment/DELIVERY_TEMPLATE.json','RETURN_FILLED_FIXTURE.json':'RETURN_FILLED_FIXTURE.json','DELIVERY_FILLED_FIXTURE.json':'DELIVERY_FILLED_FIXTURE.json','SUMMARY.json':'SUMMARY.json'}
for name,relative in examples.items():
    target=human/'TECHNICAL_EXAMPLES'/name;target.parent.mkdir(exist_ok=True);shutil.copy2(OUT/'TECHNICAL_FIXTURE'/relative,target)
for p in (ROOT/'outputs/ai-pilot-integrity-2026-11-11/LAT-AI-PILOT-START-2026-11-12').glob('*.txt'):
    target=human/'PILOT'/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
manual=archive(OUT/'LAT-AI-MANUAL-AUDIT-INTAKE-2026-11-11.zip',{p.relative_to(human).as_posix():p for p in human.rglob('*') if p.is_file()})
backup=OUT/'backup';backup.mkdir();bundle=backup/'LAT-AI-GIT.bundle'
subprocess.run(git+['bundle','create',str(bundle),'--all'],check=True,capture_output=True)
verified=subprocess.run(git+['bundle','verify',str(bundle)],check=True,capture_output=True);(backup/'bundle-verify.log').write_bytes(verified.stdout+verified.stderr)
(backup/'dirty.patch').write_bytes(subprocess.check_output(git+['diff','--binary','HEAD']))
(backup/'git-status.txt').write_bytes(subprocess.check_output(git+['status','--short']))
files={n:ROOT/n for n in previous if (ROOT/n).is_file()}
for p in (ROOT/'tools').iterdir():
    if p.is_file():files[p.relative_to(ROOT).as_posix()]=p
for p in OUT.rglob('*'):
    if p.is_file() and 'backup' not in p.relative_to(OUT).parts and p.suffix not in {'.zip','.pyc','.lock'} and p.name!='package-build.log':files[p.relative_to(ROOT).as_posix()]=p
assert not any(n.endswith(('.gguf','.sqlite3','.db','ipc-secret.txt')) for n in files)
save(backup/'source-and-evidence-manifest.json',{n:sha(p) for n,p in files.items()})
back=archive(backup/'LAT-AI-INTAKE-SOURCE-AND-EVIDENCE.zip',files)
put(backup/'RESTORE.txt','Clone bundle into a NEW directory; overlay lat-ai/ from ZIP. Do not apply dirty.patch over overlay/reset present tree. Check SHA. Includes old/new tools and evidence; no weights,DB,secrets. TECHNICAL_FIXTURE store is not real human data. No commit/push.\n')
save(OUT/'package-audit.json',{'utc':datetime.now(timezone.utc).isoformat(),'manual':manual,'backup':back,'bundle_sha256':sha(bundle),'bundle_verified':True})
print(json.dumps({'source_unchanged':len(current),'protected_unchanged':len(protected),'old_tools_evidence_unchanged':len(retained),'manual':manual,'backup':back}))
