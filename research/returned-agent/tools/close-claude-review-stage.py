"""Package reviewed AI-only continuation without modifying frozen experiment evidence."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,subprocess,zipfile,shutil
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/claude-reviewed-ai-continuation-2026-11-11'
OLD=ROOT/'outputs/sdk-fix-and-history-scan-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def put(p,s):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:f.write(s)
def archive(path,files):
    manifest={n:sha(p) for n,p in sorted(files.items())}
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
        for name,p in sorted(files.items()):z.write(p,name)
        z.writestr('ARCHIVE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(manifest)|{'ARCHIVE_MANIFEST.json'}
        for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    return {'name':path.name,'sha256':sha(path),'verified_entries':len(manifest)+1}

stamp=datetime.now(timezone.utc).isoformat()
previous=read(OLD/'backup/source-and-evidence-manifest.json')
source=ROOT/'lat-ai';git=['git','-c','safe.directory='+source.as_posix(),'-C',str(source)]
names=subprocess.check_output(git+['ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
current={n:sha(source/n) for n in sorted(set(filter(None,names))) if (source/n).is_file()}
assert current==read(OLD/'source-audit.json')['after_sha256']
protected=[n for n in current if n.startswith(('backend/','assets/')) or n=='index.html']
frozen_evidence={n:h for n,h in previous.items() if n.startswith(('outputs/u02-runtime-controls-2026-11-11/','outputs/sdk-fix-and-history-scan-2026-11-11/','outputs/review-signals-prototype-2026-11-11/'))}
for name,digest in frozen_evidence.items():assert sha(ROOT/name)==digest,name
rules=read(ROOT/'outputs/review-signals-prototype-2026-11-11/signal-protocol.json')
for name,digest in rules['files_sha256'].items():assert sha(ROOT/name)==digest,name
for name in ['tools/sdk-load-with-deadline.mjs','tools/verify-sdk-deadline-live.mjs','work/local-pc/profile.json']:
    assert sha(ROOT/name)==previous[name],name
plan=read(ROOT/'outputs/u02-runtime-controls-2026-11-11/known128-plan.json')
for name,digest in plan['tool_sha256'].items():assert sha(ROOT/'tools'/name)==digest,name
policy=read(OUT/'audit-protocol.json')
assert sha(OUT/'audit-protocol.json')==(OUT/'audit-protocol.json.sha256').read_text().strip()
for name,digest in policy['files_sha256'].items():assert sha(ROOT/name)==digest,name
imports=[]
for p in (source/'integration/ai/core/src').rglob('*'):
    if p.is_file() and any(t in p.read_text(encoding='utf-8',errors='replace') for t in ['review-signals','prepare-signal-review-audit','sdk-load-with-deadline-v2']):imports.append(p.as_posix())
assert not imports
save(OUT/'source-audit.json',{'utc':stamp,'project_files_unchanged':len(current),'protected_files_unchanged':len(protected),'frozen_evidence_files_unchanged':len(frozen_evidence),'signal_dependencies_unchanged':len(rules['files_sha256']),'old_sdk_helper_and_live_runner_unchanged':True,'scan_tools_unchanged':True,'new_audit_protocol_verified':True,'local_profile_unchanged':True,'prototype_imports_in_core':imports,'after_sha256':current})

delivery={'recorded_utc':stamp,'chat':'https://claude.ai/chat/bf69c588-0773-495f-8cbe-6167148049f6','actual_sent_messages':4,'completed_responses_read':4,'verification':'Native Claude accessibility tree shows four sent stage messages and four completed responses. Not merely draft/send key. Document text truncated on long chat; full final response read in AX elements. Screenshots unavailable, not claimed.','scope':'Review of supplied descriptions/snippet, not repository audit','prepared_previous_reports_sha256':{p.name:sha(p) for p in (ROOT/'outputs/claude-review-2026-11-11').glob('*TO-SEND.txt')},'notes':{p.name:sha(p) for p in OUT.glob('CLAUDE-*-NOTES.txt')},'notes_are':'Codex summaries, not verbatim transcript; messages1/3 included later clarifications, message4 summarized completed changes.'}
save(OUT/'delivery-record.json',delivery)
status=ROOT/'outputs/claude-review-2026-11-11/DELIVERY-STATUS.txt'
old_status=status.read_text(encoding='utf-8-sig')
status.write_text('АКТУАЛИЗАЦИЯ '+stamp+': отправлены4 отчёта, прочитаны4 рецензии Claude.\nЧат: '+delivery['chat']+'\nПодтверждения/конспекты/решения: outputs/claude-reviewed-ai-continuation-2026-11-11.\nНиже неизменный текст прежнего неуспешного этапа (история, не текущий статус).\n\n'+old_status,encoding='utf-8')

duplicate='В третьей серии — **107 верных, 2 неверных, 19 отказов**: U02 занижен, U46 получил\nневерный полный балл после пропуска противоречия. Автоматически выпускать полный\nбалл по согласию двух проходов нельзя считать безопасным. U02 также показал\nизменение verifier при checkpoints32; прежнее постоянство было ограничено серией.\n'
nav='''## Рецензии Claude и подготовка ручного аудита · 11.11.2026

**Отправлены четыре отчёта и прочитаны четыре рецензии.** Замечания сверены с
артефактами; это рецензия описаний, не независимый аудит репозитория.
SDK helper v2: проверка диапазона таймера,6tests; старый live helper сохранён,
новая livev2/abort проверка не проводилась. Новый offline sampler:8tests,
замороженная выборка до20 no-signal плюс все отмеченные случаи после слепых меток.
Оценщик, промпты,209исходников,бэк/фронт и профиль60/70/80 не менялись.

Скан известного128: ошибки0/109,0/109,2/109 среди выданных;19отказов в каждой
серии имеют разный состав. U02 занижен, U46 завышен в третьей;7/128 меняли итог.
Таблица7×3/задачи/ограничения добавлены без пересчёта первичных результатов.
Реальные данные и люди отсутствуют; координатор разраб 1 П, сбор12.11.2026.
Пилот только теневой, решения после показа модели не заменяют слепой reference.
T01/S02/D01/D02 открыты. Перед выдачей карточек нужна ручная проверка raw fragment IDs.

[Отчёт](<E:/Startup Tau/outputs/claude-reviewed-ai-continuation-2026-11-11/REPORT.txt>) ·
[Пакет координатору ZIP](<E:/Startup Tau/outputs/claude-reviewed-ai-continuation-2026-11-11/LAT-AI-PILOT-AND-CLAUDE-REVIEW-2026-11-11.zip>).

Далее история этапов; прежний статус «не отправлено» заменён записью доставки выше.

'''
for name in ['START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md']:
    p=ROOT/name;old=p.read_text(encoding='utf-8-sig');assert nav.split('\n')[0] not in old
    assert duplicate+duplicate in old
    old=old.replace(duplicate+duplicate,duplicate,1)
    if old.startswith('# LAT AI'):
        title,rest=old.split('\n',1);new=title+'\n\n'+nav+rest.lstrip('\n')
    else:new=nav+old
    p.write_text(new,encoding='utf-8')
p=ROOT/'tools/update-sdk-history-docs.py';text=p.read_text(encoding='utf-8-sig');assert duplicate+duplicate in text;p.write_text(text.replace(duplicate+duplicate,duplicate,1),encoding='utf-8')
p=ROOT/'AGENTS.md'
with p.open('a',encoding='utf-8') as f:f.write('\n- Claude-reviewed continuation11.11:4reports actually sent/4responses read in desktop; descriptions review, not repo audit. SDKhelperv2+6tests separate from unchanged frozenv1/live; realabort nottested/quarantine runbook. New frozen post-label signal audit sampler+8tests,allflags+20controls,not initialblind,gold unchanged; no realpilot run. Public seed not manipulation-proof; manual fragment-ID interpretation check before exposure. Source209/101 and oldfrozen evidence unchanged, no modelPOST/commit/push. Current report/manualZIP/backup:outputs/claude-reviewed-ai-continuation-2026-11-11. PriorNOTSENT history superseded by delivery-record. Scan has7/128varied,errors0/109,0/109,2/109; U is datasetnot task; V32 outside selected128. Continue realdata/people gates,T01/S02/D01/D02 open, no prompt/backend/frontend edits.\n')
put(OUT/'WORKLOG.txt',f'''LAT AI worklog, recorded {stamp}
1. Restored Claude desktop after user focused composer. Four reports sent once;
   actual message/finished response verified in AX, notes saved. Earlier failure retained.
2. Reviewed local SDK ownership/error paths and Node timers docs. RED overflow test
   preserved; separate v2 range guard passed6tests. No live retry/abort/model load.
3. Added standalone post-label audit sampler.8tests passed, fixture only;
   audit-protocol frozen before realdata. Original9 signal dependencies unchanged.
4. Read frozen scan raw U46 and sampling code; generated post-hoc descriptive
   addendum with original result SHA verification, no rerun/no label changes.
5. Reconciled Claude4: anchoring/reference,20controls,privacy/exposure,unsupported,
   known-data origin vs text overlap,public seed limitation. Remaining human gates explicit.
6. Source audit209/protected101/frozen evidence+protocols passed. New core imports none.
7. Current navigation/delivery updated, duplicate paragraph removed in navigation
   and unfrozen old doc generator. Historical scan reports unchanged.
8. Build coordinatorZIP plus bundle/ZIP backup; CRC and each entry SHA checked.
No prompts/backend/frontend/production gate edits, commit/push or inference this continuation.
Tests: node --test tools/test-sdk-load-with-deadline-v2.mjs (6 passed; earlier RED retained).
Python tools/test-signal-review-audit.py (8passed; final log retained, rerun after provenance guard).
Python tools/report-claude-history-addendum.py (read-only input; new output only).
Python tools/prepare-signal-review-audit.py freeze ... (new protocol, no model).
Console Cyrillic on one report command was encoding-limited; output file written UTF-8.
Routine failed rg wildcard paths corrected with supported -g/file enumeration; no source mutation.
''')

human=OUT/'LAT-AI-PILOT-AND-CLAUDE-REVIEW';human.mkdir(exist_ok=False)
put(human/'00_START.txt','''LAT AI — пакет координатору, 11.11.2026
Координатор разраб 1 П; план сбора12.11.2026. Сначала CURRENT_REPORT.txt и
PILOT_AUDIT_RULES.txt, затем PILOT/01_ПЛАН_И_РЕШЕНИЕ.txt. Реальных данных пока нет.
PILOT — сбор/согласия/обезличивание/люди. HISTORY —8известных случаев с метками,
не выдавать слепым разметчикам. CLAUDE — конспекты4реальных рецензий описаний.
Техническому специалисту SDK-FAILURE-RUNBOOK.txt и SCAN_REVIEW_ADDENDUM.txt.
Полный ZIP только координатору. Первичным разметчикам отдельная проверенная blind
выгрузка; post-label reviewer только после freezeметок. Private map отдельным доступом.
Назначить2независимых разметчиков и третьего для споров; подтвердить доступ/хранение,
обезличивание и reference. Проверить понятность fragment IDs до аудита цитат.
Все результаты экспериментальные, автоматической выдачи оценок ученикам не разрешают.
''')
for p in (ROOT/'outputs/ai-pilot-integrity-2026-11-11/LAT-AI-PILOT-START-2026-11-12').glob('*.txt'):
    target=human/'PILOT'/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
for name in ['HISTORY_CASES.txt','HISTORY_CASES.json']:
    shutil.copy2(OLD/'LAT-AI-PILOT-AND-HISTORY-REVIEW'/name,human/name)
for p in OUT.glob('*.txt'):
    if p.name=='WORKLOG.txt':continue
    target=human/('CURRENT_REPORT.txt' if p.name=='REPORT.txt' else p.name);shutil.copy2(p,target)
shutil.copy2(OUT/'delivery-record.json',human/'delivery-record.json')
manual=archive(OUT/'LAT-AI-PILOT-AND-CLAUDE-REVIEW-2026-11-11.zip',{p.relative_to(human).as_posix():p for p in human.rglob('*') if p.is_file()})
backup=OUT/'backup';backup.mkdir(exist_ok=False)
bundle=backup/'LAT-AI-GIT.bundle';subprocess.run(git+['bundle','create',str(bundle),'--all'],check=True,capture_output=True)
result=subprocess.run(git+['bundle','verify',str(bundle)],check=True,capture_output=True)
(backup/'bundle-verify.log').write_bytes(result.stdout+result.stderr)
(backup/'dirty.patch').write_bytes(subprocess.check_output(git+['diff','--binary','HEAD']))
(backup/'git-status.txt').write_bytes(subprocess.check_output(git+['status','--short']))
files={name:ROOT/name for name in previous if (ROOT/name).is_file()}
for p in (ROOT/'tools').iterdir():
    if p.is_file():files[p.relative_to(ROOT).as_posix()]=p
for p in OUT.rglob('*'):
    if p.is_file() and 'backup' not in p.relative_to(OUT).parts and p.suffix not in {'.zip','.pyc'} and p.name!='package-build.log':files[p.relative_to(ROOT).as_posix()]=p
assert not any(n.endswith(('.gguf','.sqlite3','.db','ipc-secret.txt')) for n in files)
save(backup/'source-and-evidence-manifest.json',{n:sha(p) for n,p in files.items()})
back=archive(backup/'LAT-AI-CLAUDE-REVIEW-SOURCE-AND-EVIDENCE.zip',files)
put(backup/'RESTORE.txt','Clone bundle into a NEW directory, overlay lat-ai/ from ZIP. Do not apply dirty.patch over overlay. Do not reset current dirty tree. ZIP contains current source/tools and preserved previous evidence. No weights,DB,secrets. Check SHA manifest. No commit/push.\n')
save(OUT/'package-audit.json',{'utc':datetime.now(timezone.utc).isoformat(),'manual':manual,'backup':back,'bundle_sha256':sha(bundle),'bundle_verified':True})
print(json.dumps({'source_unchanged':len(current),'protected_unchanged':len(protected),'frozen_evidence_unchanged':len(frozen_evidence),'manual':manual,'backup':back},ensure_ascii=False))
