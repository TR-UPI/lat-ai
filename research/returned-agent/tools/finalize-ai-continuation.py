from pathlib import Path
import json,hashlib,zipfile,subprocess
root=Path(__file__).resolve().parent.parent;base=root/'outputs/ai-continuation-2026-11-11'
package=json.loads((base/'human-package-verification.json').read_text())
report=f'''LAT AI — продолжение ИИ-части и отдельный пакет ручной проверки, 11.11.2026

Результат
1. evidence-v3e-context: распознаётся явная запись x := 2; значения 2.5 не принимаются за 2.
   Меняется только дополнение исходной цитаты. Промпты, критерии и grade gate прежние.
2. Слепая выгрузка для двух проверяющих исключает expected/actual/category/group metadata.
   Пометка ambiguous_rubric=true требует ручного решения даже при одинаковых checks.
   Freeze сохраняет четыре исходных разметки/ответа, primary и три серии с SHA256 восьми файлов.
3. Пилот, T01, S02, D01/D02 и инженерный handoff собраны в отдельный ZIP для людей.

Архив для ручной работы
{package['zip']}
43 файла, {package['bytes']} байт.
SHA256: {package['sha256']}
CRC и побайтовая проверка всех файлов прошли. Проверено 42 записи MANIFEST и сам MANIFEST.
После извлечения все7 тестов утилит прошли; слепые формы пустые, контексты T01 на месте.
Реальных данных, приглашений, заполненных подписей, секретов и модели в пакете нет.
Полный ZIP предназначен координатору; разметчикам передавать ТОЛЬКО их отдельные слепые папки.

Доказательства AI-правки
- Синтаксические development-фикстуры зафиксированы с SHA до изменения; это не модельный holdout.
- Replay160 сохранённых ранее модельных ответов:136 совпадений с авторской разметкой,
  1 ошибка,23 отказа. Изменений checks/отказов0; изменена ровно1 цитата V11.
- До: «проверка x==2 := True;». После: «x := 2; проверка x==2 := True;».
- Предыдущий новый32 остаётся историческим:25 верных,1 неверная оценка,6 отказов,24 joint.
  После правки теперь известного V11 нельзя объявлять первичный результат25 joint или unseen.
- Live через приватный AI worker: V11/N05 2/2, полные цитаты, точные квитанции.
  Время14.43/10.13с; это2 известных синтетических smoke-случая, не статистика качества/нагрузки.
- 80 Node integration,19 Django,335 archived core,3 схемы/20 pins,7 pilot tool tests прошли.
  Проверки Django read/test-only; исходники backend/frontend не правились.

Сбой первого запуска и восстановление
Первый запуск из sandbox не увидел занятые порты: Get-NetTCPConnection подавлял ошибку.
Он создал нерабочие дубли; новый worker получил database is locked. Read-only smoke заметил
старую ревизию v3d ДО dispatch, поэтому модельный запрос из этой попытки не был отправлен.
Сохранены failed-launch-process-record.json, process-ownership-proof.json, restart/HTTP логи.
Проверены реальные PID, executable, command line и creation time трёх наших процессов;
восстановлена запись владельцев. Завершён только подтверждённый зависший дочерний Django
неудачного запуска. Штатный launcher затем проверил ownership/idle/retirement и перезапустил
наш стенд. Общий LM Studio и чужие процессы не останавливались, БД/аккаунты сохранены.
В локальном launcher ErrorAction заменён на Stop: ошибка чтения портов больше не маскируется.
Итог ready/idle, без quarantine; локальные60/70/80с сохранены, общие8/9/10с не изменены.
Начальная ошибка и её лог не заменены удачным повтором. Повторного unknown POST не было.

Область изменений и сохранение
В проекте209 файлов до/после; изменены4 файла: AI helper,revision,тесты и AI-документация.
Все остальные исходники побайтово прежние, включая101 backend/assets/index файл.
Изменения вспомогательных tools ограничены пилотом, отчётами и локальным запуском AI-стенда.
Git bundle проверен; текущий dirty tree сохранён отдельно в backup/LAT-AI-AI-CONTINUATION-SOURCE.zip.
Commit/push/reset не делались. Предыдущие полные резервные копии и архивы сохранены.

Что не решено
V05 — недооценка, U02/U26/H18 — отказы на правильных ответах. Общий риск не подтверждён.
Два прохода одной модели не независимые судьи. Цитатный regex не проверяет смысл/истинность.
Новый модельный holdout в этом этапе НЕ запускался: промпты/решения не менялись, и главный
пробел теперь реальные независимые работы и люди, а не повторное тестирование авторских фраз.
Теневой пилот не проведён. Цели2%/20% — предложения; T01/S02/D01/D02 остаются открытыми.
Большая очередь класса, async UI и backend recovery не реализованы (другие разработчики).

Следующее ручное действие
Координатор открывает ZIP/00_START_HERE.txt, назначает двух людей, утверждает рубрику/план,
собирает реальные обезличенные ответы и возвращает независимые листы плюс adjudication.
Без этих данных невозможно честно измерить качество на учениках; формы не считаются результатом.
'''
(base/'REPORT.txt').write_text(report,encoding='utf-8')
log='''
Stage 1: Snapshot209 source files; syntax development fixtures+SHA frozen before edit.
Stage 2: v3e citation completion and numeric-boundary tests;6 context tests passed.
Stage 3: Pilot ambiguity gate + canonical input freeze hashes; initial6, then7 tests passed after blind export.
Stage 4: Replay160:0 decision changes,1 citation change V11;136 correct,1 wrong,23 abstain on known synthetic labels.
Stage 5: tools/test-lat-ai.ps1 checks:80 integration,19 Django,335 core,contracts3/20 passed.
Stage 6: First sandbox restart failed to discover existing listeners; duplicate worker database locked.
Initial HTTP assertion detected old v3d at read-only receipt BEFORE inference. Failure preserved.
Escalated read verified live ownership: worker28456/Django4820/site22728 at06:26:23.
Recovered process record, stopped only failed owned Django17220 (06:39:09), normal verified restart succeeded.
Local launcher now fails on Get-NetTCPConnection error (no silent failure).
Stage 7: Live v3e V11/N05 both passed,14.43/10.13s,exact receipts; new unique request IDs, no inference retries.
Stage 8: Human package43files allowlist; CRC+byte verification,42 manifest entries; extracted7 tests passed.
Stage 9: Source audit209->209;4 AI/doc changes;101 protected backend/assets/index files identical.
Stage 10: Final runtime ready/idle,local60/70/80. Git bundle created/verified; dirty source backup prepared.
Read-only discovery errors: guessed f01-review/frozen-inputs path absent (canonical f01 context found);
checks/summary.json absent (actual checks/results.json used). No data or source losses.
No real works/human labels received, no new neural holdout, no external messages, no commit/push.
'''
with (base/'WORKLOG.txt').open('a',encoding='utf-8') as f:f.write(log)
prefix='''## ИИ-продолжение и отдельный ZIP ручной проверки · 11.11.2026

Принята evidence-v3e-context: запись x := 2 дополняет известную цитату V11;
промпты/checks/gate прежние. Replay160:0 изменений решений,1 исправленная цитата;
136 верных,1 ошибка,23 отказа на известных синтетических данных. Это НЕ новый holdout.
Живые V11/N05:2/2 с полными цитатами и точными квитанциями. V05/U02/U26/H18 остаются открытыми.

Пилот усилен слепым экспортом A/B, обязательным разбором ambiguous_rubric даже при
совпавших checks и SHA исходных разметок. Отдельный ZIP содержит43 файла для координатора,
преподавателей, S02 и D01/D02. Реальных работ/решений нет; T01/S02/D01 открыты,2%/20% не утверждены.
80 Node+19 Django+335 baseline+contracts+7 pilot tests прошли;101 backend/assets/index неизменны.
Ошибка первого sandbox-перезапуска сохранена и исправлена; новый стенд ready/idle с60/70/80с.
Полный отчёт содержит восстановление процессов; общие лимиты и backend/frontend не менялись.

[Отдельный ZIP](<E:/Startup Tau/outputs/ai-continuation-2026-11-11/LAT-AI-PILOT-AND-HUMAN-REVIEW-2026-11-11.zip>) ·
[Отчёт и ограничения](<E:/Startup Tau/outputs/ai-continuation-2026-11-11/REPORT.txt>).

'''
for name in ['outputs/AI_ROADMAP.md','outputs/STATUS.md']:
 p=root/name;p.write_text(prefix+p.read_text(encoding='utf-8-sig'),encoding='utf-8')
p=root/'START_HERE.md';text=p.read_text(encoding='utf-8-sig');title='# LAT AI — начало работы\n'
assert text.startswith(title)
p.write_text(title+'\n'+prefix+text[len(title):],encoding='utf-8')
with (root/'AGENTS.md').open('a',encoding='utf-8') as f:f.write('''
- Актуальное продолжение11.11: evidence-v3e-context исправляет известную цитату V11 (x := 2), не checks/prompts. Replay160:136correct/1wrong/23refusal,0decision changes,1quote change; это не unseen. LiveV11/N05 2/2. V05/U02/U26/H18 открыты. Отдельный ZIP пилота/ручной проверки:outputs/ai-continuation-2026-11-11/LAT-AI-PILOT-AND-HUMAN-REVIEW-2026-11-11.zip (43files). Полный ZIP только координатору; слепым разметчикам только их папки без model/author labels. ambiguous_rubric=true требует adjudication даже при равныхchecks. Freeze сохраняет SHA8 файлов.80Node+19Django+335core+contracts+7pilot passed;101backend/assets/index unchanged. Реальных работ пока нет,T01/S02/D01 открыты.
- Локальный перезапуск из sandbox однажды не увидел порты и создал нерабочие дубли; восстановление ownership задокументировано в outputs/ai-continuation-2026-11-11/REPORT.txt. Launcher теперь ErrorAction Stop при проверке портов. Для чтения WMI/владельцев и штатного Restart использовать разрешённую эскалацию, не обходить проверки и не восстанавливать старые PID автоматически. Одноразовый recover-local-record-v3e.ps1 повторно НЕ запускать. Текущий runtime ready/idle,v3e,60/70/80; не останавливать чужие процессы.
''')
# Source backup is separate from the human package; include only allowlisted project files and support evidence.
audit=json.loads((base/'source-audit.json').read_text())
files={}
for name in audit['after_sha256']:files['lat-ai/'+name]=root/'lat-ai'/name
for p in (root/'tools').glob('*'):
 if p.is_file() and p.suffix in ['.py','.mjs','.ps1']:files['tools/'+p.name]=p
for name in ['AGENTS.md','START_HERE.md','outputs/STATUS.md','outputs/AI_ROADMAP.md']:files[name]=root/name
for p in base.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(base)
 if rel.parts[0] in ['backup','source-before','package-extracted-verification','LAT-AI-HUMAN-REVIEW']:continue
 if 'test-runtime' in rel.parts:continue
 if p.suffix.lower() not in ['.txt','.json','.jsonl','.log','.patch','.sha256','.zip']:continue
 files['evidence/'+rel.as_posix()]=p
files['history.bundle']=base/'backup/history.bundle'
manifest={name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for name,p in files.items()}
destination=base/'backup/LAT-AI-AI-CONTINUATION-SOURCE.zip'
with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as z:
 for name,p in sorted(files.items()):z.write(p,name)
 z.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(destination) as z:
 assert z.testzip() is None
 for name,entry in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==entry['sha256']
result={'path':str(destination),'project_files':len(audit['after_sha256']),'entries':len(files)+1,'bytes':destination.stat().st_size,'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'verified':True,'git_bundle_verified':True,'note':'Dirty working tree snapshot, not a commit. Does not contain runtime/databases/model/secrets. Earlier original archives remain separate.'}
(base/'backup/verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
