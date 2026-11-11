from pathlib import Path
import json,hashlib,zipfile,shutil
root=Path(__file__).resolve().parent.parent
out=root/'outputs/u02-runtime-controls-2026-11-11'
if (out/'HUMAN-REVIEW').exists():raise SystemExit('One-time finalizer already ran; do not rewrite reports or navigation')
if (out/'HUMAN-REVIEW').exists():raise SystemExit('One-time finalizer already ran; do not rewrite reports or navigation')
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    with p.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)

header='''## U02: checkpoints меняют ошибки, исправление не принято · 11.11.2026

На8 новых загрузках при32: послеN05→U15 отказ2/2, послеV11 занижение2/2.
При0: отказ4/4, но оба прохода ошибаются в разных критериях; правильной оценки нет.
Медиана U02 выросла с10,38 до12,75с. Штатная настройка32 сохранена.
Все20 ответов/40POST и8 выгрузок сохранены, но процесс завершился exit1 при закрытии SDK.
Отдельный аудит подтвердил terminal ответы, отсутствие8 ID и прежний SHA весов.
Сбой не скрыт повтором; последняя диагностическая блокировка сохранена как доказательство.

17 тестов нового runner v2 и4 теста отменяемого load-таймера прошли. Живое подтверждение
нового helper отсутствует. V2 фиксирует3 разных порядка, окружение, instance ID и историю.
Скан128×3 заморожен, **не запущен** после непредвиденного завершения; доля чувствительных
случаев неизвестна. Предыдущие8 загрузок:3 с занижением/5 с отказом, а по запросам5/12 и7/12.
Старые H32/V32 цифры не пересчитаны; добавлено ограничение истории/порядка.

Все209 файлов проекта, промпты, бэк и фронт неизменны. Стенд ready/idle,60/70/80с прежние.
Реальных работ и независимых разметчиков ещё нет. Координатор «разраб 1 П», старт12.11.2026.
Следующий ручной шаг: разбор SDK/runtime и U02, утверждение/сбор реального теневого пилота.

[Отчёт](<E:/Startup Tau/outputs/u02-runtime-controls-2026-11-11/REPORT.txt>) ·
[Уточнение метрик](<E:/Startup Tau/outputs/u02-runtime-controls-2026-11-11/ERRATA_HISTORY_AND_UNITS.txt>) ·
[Пилот и ручной разбор ZIP](<E:/Startup Tau/outputs/u02-runtime-controls-2026-11-11/LAT-AI-PILOT-AND-RUNTIME-REVIEW-2026-11-11.zip>).

'''
for name in ['outputs/AI_ROADMAP.md','outputs/STATUS.md']:
    p=root/name;p.write_text(header+p.read_text(encoding='utf-8'),encoding='utf-8')
p=root/'START_HERE.md';text=p.read_text(encoding='utf-8');title,rest=text.split('\n',1);p.write_text(title+'\n\n'+header+rest.lstrip('\n'),encoding='utf-8')
with (root/'AGENTS.md').open('a',encoding='utf-8') as f:f.write('\n- 11.11 runtime controls: user still forbids prompt/backend/frontend changes. New8 loads20assessments40POST; checkpoint32 A-refusal2/2,B-undergrade2/2; checkpoint0 A/B-refusal4/4 with different errors in BOTH passes (proposal FTT,verifier TTF), not a grading fix. Global process exit1 after all8 retirement proofs due SDK late abort after dispose; separate read-only audit confirms40 terminal bodies and absence8 IDs. Last diagnostic lock preserved; no retries. Stand ready/idle default32,source209 unchanged. SDK safe-deadline helper4 unit tests only; v2 pilot runner17 tests,3 frozen orders+automatic environment/history. Known128x3 plan frozen NOT RUN due unexpected event; v2 uses CLI, not SDK. Older8-load investigation is3/8undergrade5/8refusal,5/12undergrade7/12refusal by observations. Persistence claim limited to2instances; oldmetrics conditioned on order/history. Report/errata/manualZIP:outputs/u02-runtime-controls-2026-11-11. Manual runtime review and real pilot remain open; coordinator разраб 1 П,start12.11.2026. No commit/push/messages.\n')

manual=out/'HUMAN-REVIEW';manual.mkdir();pilot=manual/'PILOT';pilot.mkdir()
old=root/'outputs/ai-pilot-integrity-2026-11-11/LAT-AI-PILOT-START-2026-11-12'
for p in old.glob('*.txt'):shutil.copy2(p,pilot/p.name)
for name in ['ERRATA_HISTORY_AND_UNITS.txt','PILOT_EXECUTION_ADDENDUM.txt']:
    shutil.copy2(out/name,manual/name)
(manual/'00_READ_ME.txt').write_text('''LAT AI — координатору и специалисту ручной проверки, 11.11.2026
Координатор: разраб 1 П. Начало сбора: 12.11.2026.

1. Координатор: прочитать PILOT_EXECUTION_ADDENDUM.txt, затем короткие6 файлов PILOT.
   Исходный краткий пакет сохранён; дополнение уточняет историю/порядки модели.
2. Специалист по оцениванию/runtime: U02_REVIEW.txt и U02_EVIDENCE.json.
   Это открытый разбор с метками модели/автора, НЕ слепая разметка.
3. ERRATA_HISTORY_AND_UNITS.txt объясняет ограничения прежних цифр.
4. Реальным слепым разметчикам передавать только отдельные очищенные выгрузки,
   созданные export-blind-review.py и проверенные verify-blind-review.py.
   Не отправлять им этот полный ZIP с результатами модели.

Реальный пилот не проведён; людские решения и согласия не заполнены автоматически.
Никаких материалов никому не отправляли. ZIP — для локальной передачи владельцем.
Полные технические raw/протокол/логи: outputs/u02-runtime-controls-2026-11-11.
''',encoding='utf-8')
(manual/'U02_REVIEW.txt').write_text('''LAT AI — открытая карточка U02 для преподавателя и runtime-специалиста
Это НЕ слепая разметка и НЕ результат независимого второго человека.

Задание: print("3" + "2").
Ответ: Результат на экране — 32. Он получается склейкой: оператор + соединяет
строку «3» со строкой «2», а не складывает числа.
Критерии: типы операндов; операция склейки; результат32.
Авторское предложение: все3 выполнены. Преподаватель должен подтвердить/оспорить.

Сегмент0: первое предложение о результате.
Сегмент1: второе предложение, строки и склейка.
Предлагаемые смысловые ссылки verifier:[1,1,0].
Фактические32 checkpoints:[-1,0,0];0 checkpoints:[0,1,-1].
Нумерация запроса и validator одинаковая (с0): это не ошибка смещения индексов кода.

Заполнить преподавателю:
- Требует ли критерий типов отдельной фразы, или достаточно «строку...со строкой»?
- Корректные checks и достаточные цитаты по всем3 критериям:
- Есть ли в ответе противоречие? Конкретный фрагмент:
- Имя/роль проверившего и дата:

Runtime-специалисту:
- Восемь загрузок дали0A/0B отказ4/4 вместо32B занижение2/2, но verifier сменил ошибку.
- После40 terminal model responses и8 retirement proofs SDK2.1.0 упал на позднем
  AbortSignal.timeout cancel после dispose. Последующий GET подтвердил отсутствие ID.
- Проверить SDK load listener lifecycle и предложенный helper с clearTimeout.
  Helper имеет4 unit tests, живого подтверждения нет; не принимать0 как готовый fix.
- Подтвердить порядок следующего ограниченного запуска/разбор сохранённого lock;
  не удалять блокировки по возрасту, не повторять неизвестные POST.
- Решение, ответственный и дата:

Скан128 на3 разных порядках заморожен, не выполнен. Правила выдачи полного/неполного
балла не менялись; вариант «полный балл автоматически безопасен» не подтверждён.
''',encoding='utf-8')
save(manual/'U02_EVIDENCE.json',{'mapping':read(out/'u02-index-mapping-audit.json'),'checkpoint_result':read(out/'checkpoint-analysis.json'),'abnormal_exit_audit':read(out/'checkpoint-recovery-audit.json')})
files={p.relative_to(manual).as_posix():sha(p) for p in sorted(manual.rglob('*')) if p.is_file()}
save(manual/'MANIFEST.json',{'audience':'coordinator and non-blind technical/teacher review; not a blind rater handout','files_sha256':files})
archive=out/'LAT-AI-PILOT-AND-RUNTIME-REVIEW-2026-11-11.zip'
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
    for p in sorted(manual.rglob('*')):
        if p.is_file():z.write(p,p.relative_to(manual).as_posix())
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None
    assert set(z.namelist())==set(files)|{'MANIFEST.json'}
    for name,digest in files.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
save(out/'manual-package-audit.json',{'zip':archive.name,'files':len(files)+1,'sha256':sha(archive),'all_entries_verified':True,'not_blind_handout':True})
print(json.dumps({'manual_zip':archive.name,'files':len(files)+1,'verified':True}))
