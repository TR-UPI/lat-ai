"""Archive presentation-only work; retain source and frozen evidence byte-for-byte."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,zipfile,shutil
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/review-card-fragments-2026-11-11'
PREV=ROOT/'outputs/claude-reviewed-ai-continuation-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def put(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:f.write(v)
def zip_checked(path,files):
    manifest={n:sha(p) for n,p in sorted(files.items())}
    with zipfile.ZipFile(path,'x',zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):z.write(p,n)
        z.writestr('ARCHIVE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
        assert set(z.namelist())==set(manifest)|{'ARCHIVE_MANIFEST.json'}
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
policy=read(OUT/'presentation-protocol.json')
assert sha(OUT/'presentation-protocol.json')==(OUT/'presentation-protocol.json.sha256').read_text().strip()
for n,h in policy['files_sha256'].items():assert sha(ROOT/n)==h,n
protected=[n for n in current if n.startswith(('backend/','assets/')) or n=='index.html']
save(OUT/'source-audit.json',{'utc':stamp,'project_files_unchanged':len(current),'protected_backend_frontend_files':len(protected),'previous_tool_and_evidence_files_unchanged':len(retained),'presentation_dependencies_verified':len(policy['files_sha256']),'local_profile_unchanged':True,'model_calls':0,'after_sha256':current})
save(OUT/'delivery-record.json',{'recorded_utc':stamp,'chat':'https://claude.ai/chat/bf69c588-0773-495f-8cbe-6167148049f6','stage_messages_sent':2,'completed_responses_read':2,'verification':'Claude native AX user messages + Message10 and12 completed responses. Actual response text read; no screenshot proof claimed.','notes_sha256':sha(OUT/'CLAUDE_REVIEW.txt'),'scope':'Review of descriptions/text examples, not code audit. No blocking comments on second review; style suggestions retained.'})
nav='''## Карточки с расшифровкой цитат · 11.11.2026

Добавлен отдельный offline formatter: полный ответ, все фрагменты verifier[0]…,
выбранный индекс и подставленный текст по каждому критерию. -1,недопустимый
индекс и непрочитанный вывод различаются; единственный фрагмент помечен как весь
ответ, а не узкая цитата. Это отображение, не новая оценка/семантическая проверка.
Готовы24карточки прежних8известных текстов×3серии.9tests и проверка24ссылочных
расшифровок прошли. Две рецензии Claude прочитаны; замечания сверены/учтены.
Source209/101,старые frozen evidence/tools и60/70/80 неизменны. Модель не вызывалась.
Техническое восстановление номеров вручную больше не требуется; смысл цитат,
понятность человеку и реальный пилот остаются ручными этапами. Промпты не менять.

[Карточки](<E:/Startup Tau/outputs/review-card-fragments-2026-11-11/history-cards/CARDS.txt>) ·
[Отчёт](<E:/Startup Tau/outputs/review-card-fragments-2026-11-11/REPORT.txt>) ·
[ZIP координатору](<E:/Startup Tau/outputs/review-card-fragments-2026-11-11/LAT-AI-HUMAN-CARDS-WITH-CITATIONS-2026-11-11.zip>).

Ниже история: прежний пробел fragment IDs закрыт новым formatter, файлы прошлых
протоколов не изменены. T01/S02/D01/D02 открыты, реальные люди/данные ещё нужны.

'''
for name in ['START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md']:
    p=ROOT/name;old=p.read_text(encoding='utf-8-sig');assert nav.split('\n')[0] not in old
    if old.startswith('# LAT AI'):
        title,rest=old.split('\n',1);new=title+'\n\n'+nav+rest.lstrip('\n')
    else:new=nav+old
    p.write_text(new,encoding='utf-8')
with (ROOT/'AGENTS.md').open('a',encoding='utf-8') as f:f.write('\n- Citation cards11.11: new separate render-signal-review-cards.mjs imports unchanged verifier segments; fullanswer/allfragments/zero-based[index]/insertedtext, -1vsinvalidvsunreadable,wholeanswer notice. Old sampler/protocols intact, new presentation-protocol pins6dependencies.9tests+24historicalcards check passed;8knowntexts×3 not24independent. Two actual Claude reviews read; no blocking comments on description, not code audit. Source209/101+prior evidence unchanged,no inference/commit/push. Manual fragment-number reconstruction gap closed; semantic review/realpilot remain. Current cards/report/manualZIP/backup outputs/review-card-fragments-2026-11-11. Future pipeline old sampler -> new renderer -> only reviewer/ after blindlabels; PRIVATE_DELIVERY hashes actual new exposure, separate coordinator access.\n')
put(OUT/'WORKLOG.txt',f'''LAT AI presentation stage, recorded {stamp}
Read active instructions, frozen sampler/test and production verifier segments/validation.
Added standalone renderer and tests; original sampler/prompts/backend/frontend never edited.
First8tests passed; firstdemo saved. Read3card UTF-8 TXT, checked U02/U46 and invalid999.
Sent stage description/examples to authorized Claude desktop; read completed response10.
Clarified -1 using actual checks=ids.map(i=>i>=0), inserted-text attribution,neutral
all-fragment labels,whole-answer notice,repeated references and valid range.
9tests passed after review; froze new presentation protocol; finaldemo saved separately.
Sent revised descriptions; read response12, no blocking comments. Style suggestions
remain for real-reader feedback, not silently modifying the frozen version again.
Built all8old diagnostic cases×3verifier series as24readablecards, no resampling/inference.
Read finalTXT and checked24 reference/quote matches; unreadable labels separately checked.
Source audit209/protected101, prior tools/evidence and local profile unchanged.
Updated current navigation, saved report/review/usage/delivery, coordinatorZIP and backup.
Commands: node --test tools/test-render-signal-review-cards.mjs (logs initial/refinement/final);
node tools/demo-review-card-fragments.mjs [demo-final];
node tools/render-signal-review-cards.mjs freeze .../presentation-protocol.json;
node tools/build-history-fragment-cards.mjs; read-only Node assertions ->readout-audit.json;
python tools/close-review-card-fragments.py (CRC+per-entrySHA checked).
No new modelrequests,stand restarts,lock changes,commit or push.
''')
human=OUT/'LAT-AI-HUMAN-CARDS-WITH-CITATIONS';human.mkdir()
put(human/'00_START.txt','''LAT AI — карточки с расшифровкой, пакет координатору
Начать сCURRENT_REPORT.txt иUSAGE.txt. Для чтения: HISTORY/CARDS.txt; соответствия
прежнимID/сериям — HISTORY/COORDINATOR_INDEX.txt.8известных ответов×3серии, не
реальные работы учеников. DEMO — короткие3примера, один ответ искусственно повреждён.
PILOT — прежние правила сбора/обезличивания/слепой разметки. Координатор разраб1П,
план начала12.11.2026. Реальных данных/независимых людей пока нет.
ПолныйZIP содержит открытые диагностические материалы: НЕ выдавать первоначальным
слепым разметчикам. Для будущей post-label выдачи следоватьUSAGE, только reviewer/
после frozenметок; private map/receipt отдельным доступом. Новых оценок здесь нет.
CLAUDE_REVIEW — две фактические рецензии описаний и решения по замечаниям.
''')
for name in ['REPORT.txt','USAGE.txt','CLAUDE_REVIEW.txt']:
    shutil.copy2(OUT/name,human/('CURRENT_REPORT.txt' if name=='REPORT.txt' else name))
for dirname,dest in [('history-cards','HISTORY'),('demo-final','DEMO')]:
    for p in (OUT/dirname).iterdir():
        if not p.is_file() or p.name.startswith('PRIVATE'):continue
        target=human/dest/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
for p in (ROOT/'outputs/ai-pilot-integrity-2026-11-11/LAT-AI-PILOT-START-2026-11-12').glob('*.txt'):
    target=human/'PILOT'/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
manual=zip_checked(OUT/'LAT-AI-HUMAN-CARDS-WITH-CITATIONS-2026-11-11.zip',{p.relative_to(human).as_posix():p for p in human.rglob('*') if p.is_file()})
backup=OUT/'backup';backup.mkdir();bundle=backup/'LAT-AI-GIT.bundle'
subprocess.run(git+['bundle','create',str(bundle),'--all'],check=True,capture_output=True)
res=subprocess.run(git+['bundle','verify',str(bundle)],check=True,capture_output=True);(backup/'bundle-verify.log').write_bytes(res.stdout+res.stderr)
(backup/'dirty.patch').write_bytes(subprocess.check_output(git+['diff','--binary','HEAD']))
(backup/'git-status.txt').write_bytes(subprocess.check_output(git+['status','--short']))
files={n:ROOT/n for n in previous if (ROOT/n).is_file()}
for p in (ROOT/'tools').iterdir():
    if p.is_file():files[p.relative_to(ROOT).as_posix()]=p
for p in OUT.rglob('*'):
    if p.is_file() and 'backup' not in p.relative_to(OUT).parts and p.suffix not in {'.zip','.pyc'} and p.name!='package-build.log':files[p.relative_to(ROOT).as_posix()]=p
assert not any(n.endswith(('.gguf','.sqlite3','.db','ipc-secret.txt')) for n in files)
save(backup/'source-and-evidence-manifest.json',{n:sha(p) for n,p in files.items()})
back=zip_checked(backup/'LAT-AI-CITATION-CARDS-SOURCE-AND-EVIDENCE.zip',files)
put(backup/'RESTORE.txt','Clone bundle into NEW directory and overlay lat-ai/ from ZIP. Do not apply dirty.patch over overlay or reset current workspace. Verify SHA. Old and new source/evidence included; weights,DB,secrets excluded. No commit/push.\n')
save(OUT/'package-audit.json',{'utc':datetime.now(timezone.utc).isoformat(),'manual':manual,'backup':back,'bundle_sha256':sha(bundle),'bundle_verified':True})
print(json.dumps({'source_unchanged':len(current),'protected_unchanged':len(protected),'old_tools_evidence_unchanged':len(retained),'manual':manual,'backup':back}))
