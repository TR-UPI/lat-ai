from pathlib import Path
import hashlib, json, subprocess, shutil
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
MAIN=ROOT/'work/lat-ai'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
readme=MAIN/'README.md'
body=readme.read_text(encoding='utf-8')
header='> **Основная интегрированная версия MAIN01:** запуск `START_MAIN.cmd`, инструкция [README-MAIN.txt](README-MAIN.txt). Принятые наработки агента и DOC01 объединены; прежняя БД выбирается явно. Прежние инструкции отдельных запусков ниже — история.\n\n'
if not body.startswith(header): readme.write_text(header+body,encoding='utf-8')
promoted=json.loads((OUT/'promoted-source.json').read_text())
for entry in promoted['files']: entry['sha256']=sha(MAIN/entry['path'])
(OUT/'promoted-source.json').write_text(json.dumps(promoted,indent=2),encoding='utf-8')
for suffix,args in [('status',['status','--short']),('diff',['diff','--binary'])]:
    (OUT/('git-'+suffix+'-after.txt')).write_bytes(subprocess.check_output(['git','-C',str(MAIN),*args]))

report='''MAIN01 — РЕЗУЛЬТАТ ИНТЕГРАЦИИ, 11.11.2026

Основная инженерная копия: canonical work/lat-ai (ветка codex/i02-api-contract, dirty сохранён, commit/push не выполнялись).
Встроен принятый source209 другого агента и последующий DOC01244. Итог248 исходных файлов:35 прежних изменены,57 добавлены, удалённых0. Перед переносом191source совпал с прежним handoff, пилот244 совпал с проверенным ZIP. Никаких новых конфликтующих локальных правок не обнаружено. Бэкап191source, git patch/index/status сохранены в этом каталоге. Дополнения MAIN: START_MAIN.cmd, tools/start-main.ps1, README-MAIN.txt, docs/ai/INTEGRATED_WORK.txt; README дополнен актуальной точкой входа.

Полный исследовательский контекст не потерян: lat-return-1111/workspace сохранён, индекс всех12132 файлов и21 раздела результатов связан из INTEGRATED_WORK. Offline-инструменты, raw/frozen, отрицательные результаты и открытые находки остаются доступны. Экспериментальные промпты, SDK-кандидаты и чужой профиль60/70/80 не активированы. Это включение результатов в рабочий контекст, а не обещание запустить каждый исторический script.

Запуск и данные:
- START_MAIN.cmd выбирает существующую tf11kit/app/.runtime/i02 через приватный .runtime/main-local.json; тип/обязательные поля проверяются, отсутствующая настроеннаяБД блокирует запуск. Никаких секретов в source.
- Старые стенды5173 и5174 остановлены после проверки idle. Borrower5174 освобождён через известный supervisor; старый tf11kit остановлен штатным run.ps1 Stop, с проверкой PID/start ticks и retirement только своего modelinstance. LM Studio server не останавливался. Новый worker владеет своим загруженным экземпляром из тех же существующих весов.
- Сайт5173, API8000, admin8000/admin/, worker8372 теперь работают из work/lat-ai. Djangojobs запущен. Старый отдельный5174 остановлен; его данные сохранены в прежнем pilot-check и не смешаны с основнойБД.
- Согласованные backup Django/replay обоихruntime находятся в work/main-integration-private-backup-final. Секреты и mapping сохранены там локально, не предназначены для пересылки.
- До миграции проверены копии обеихБД,13/14 прежних таблиц неизменны. На живойБД перед тестовыми записями все14 таблиц побайтово по значениям строк совпали с backup. integrity/FK passed. Исторические названия курсов и текст старых оценок не переписывались, поэтому могут содержать прежнюю формулировку о ручной проверке. Новые оценки автоматические.

Доказательства:
-91/91 Node integration,37/37 Django,335/335 core на текущемsrc/data,4/4 frontend; provenance20 pinned files.
-6/6 launcher guard tests; до исправления malformed-config тесты дали4ошибки, после исправления0.
-43/43 HTTP/DBchecks: существующийаккаунт, курсы/попытки, adminlogin/CSS, приватныепути, новыйsyntheticuser,4автооценки, hint, личныйдокумент, jobs, ключискрыты, повторбезнакрутки, owner404.
-4/4 synthetic Python: auto_checked100/100,2.187–3.547с; обаурокаcompleted100. Это smoke интеграции, не доказательство100%точности на новыхработах.
-Документhistory: ready14.156с; автооценка/прогресс/защитаотповтораpassed. Учебные61файл не импортированы.
-В браузере: входстарымаккаунтом, курс, обаурока и историческиебаллысохранены, новыйразделдокументов. Полный uploadчерезfilechooserнеповторялся, HTTPсценарийвыполнен.
-Повторный MAINзапуск отказал на занятом8000 до созданияпроцессов/миграции; активныйстендсохранён.

Условия и неуспешные попытки не скрыты:
Node sandboxloopbackEACCES устранён scopedразрешением. Coreharness сначала не содержал schema/ajv/eval — добавлены только тестовыезависимости, затем335passed. Первый liveharness сравнивал CRLF cнормализованнымread_text, исправленнаbytesdecode до любогоmodelcall. Активныйreplay имеет EXCLUSIVElocking, livebackupожидаемо не завершился; после штатнойостановки backuppassed. Первое продвижение остановилось на различии npminstallationmetadata .package-lock.json после копированияsource; всеdependency payloadпроверены, metadataнеперезаписана. В bundledPython нетpip: parsersперенесены из ужеустановленныхпроверенныхпакетов,6imports passed; защитаWindowsнеизменна.

Открыто: U02/V05/U46/отказыcorrectanswers, Djangoassessment receipt reconciliation, полныйUI/чистыйПК, SDKisolatedabort, качество подсказок/цитат DOC01. Преподаватель не обязательный gate по указанию владельца. Архивныеотчёты не переписывались; новыеоценкинеисправляют прежние заднимчислом.

Откат: ROLLBACK.txt. Исходники main-source-before.zip; promotion-manifest.json/promoted-source.json; миграции и данные migration-verification.json/live-preserved-tables.json. После новыхответов запрещено молча накладывать старуюБД — откатsource и откатданных разныеоперации.
'''
(OUT/'REPORT.txt').write_text(report,encoding='utf-8')
(OUT/'ROLLBACK.txt').write_text('''MAIN01 — возврат к предыдущему стенду
1. Остановить MAIN через Ctrl+C в окне запуска. Если запуск выполнен агентом скрыто, использовать его сохранённый процессный контекст: runtime/pilot-processes.json, проверить PID, путь исполняемого файла и родителя; сначала дождаться idle, затем штатно retire только принадлежащий MAIN экземпляр. Не убивать процесс только по номеру из старого файла и не удалять model-inflight.lock.
2. Предыдущая рабочая копия tf11kit/app целиком сохранена. Её run.ps1 Start/START.cmd возвращает прежний код на тех же портах с той жеБД; перед этим подтвердить отсутствие MAINпроцессов и unresolvedlocks. Общий LMStudio не останавливать. Новыеstudyтаблицы не нужно удалять ради старого кода.
3. main-source-before.zip содержит все191 прежнихtracked/untracked source. Если требуется вернуть именно work/lat-ai, сначала проверить CRC/SHA по backup-verification.json и сравнить текущиеfiles с promoted-source.json. Сохранить текущие изменяемые файлы отдельно; любые новые изменения послеMAIN01 — ручное слияние. Новые57files переместить в отдельный карантин только после проверки принадлежности; git reset/clean не применять.
4. БД/секреты/mapping/replay не заменять source-архивом. Согласованные локальные backup — work/main-integration-private-backup-final; восстановлениеданных может потерять новыеответы, поэтому только отдельнымявнымрешением. Копии locks/PID не использовать.
''',encoding='utf-8')
summary='**MAIN01 — интеграция в основную работу, 11.11.2026:** текущие исходники теперь `work/lat-ai` (248 файлов), включают принятые209 и DOC01. Запуск `START_MAIN.cmd`; сайт5173/API8000/admin8000/admin/ используют прежнюю tf11kit SQLite, аккаунты/оценки/прогресс сохранены. Старый отдельный5174 остановлен, его данные сохранены.91Node/37Django/335core/4frontend/6launcher и43HTTP/DBchecks passed;4 живые автооценки2,19–3,55с, оба урока100%; документready14,16с. Это интеграционный smoke, не оценка качества. Бэкапы и [отчёт](<'+str(OUT/'REPORT.txt').replace('\\','/')+'>); исследовательский контекст связан из docs/ai/INTEGRATED_WORK.txt. Учебный пакет61 отложен. Без новых весов/API/RAG и без commit/push. Следующий шаг: качество оценки/подсказок и recovery, не повторная интеграция.**'
roadmap=ROOT/'outputs/AI_ROADMAP.md'
status=Path('C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-05/new-chat/outputs/shag-platform/STATUS.md')
for path in [roadmap,status]:
    shutil.copy2(path,OUT/(path.name+'.before-main01'))
    text=path.read_text(encoding='utf-8')
    if path==roadmap:
        text=text.replace('## Где мы сейчас\n','## Где мы сейчас\n\n'+summary+'\n',1)
        text+='\n\n### MAIN01 — основная интеграция\n\n| R-120 | Владелец: встроить работу прошлого агента, ничего не сломать; материалы отложить | Выполнено в work/lat-ai с source/SQLitebackup, явнымruntime, сохранениемdirty и тестами; исследовательские результаты проиндексированы, экспериментальные настройки не включены. | MAIN01 |\n| R-121 | Независимая проверка launcher/runtime | Старыйlauncher не запускаетjobs; новыйMAIN использует прежнююБД. Malformedconfig failclosed,6/6tests. | MAIN01 |\n\nСледующий входящий ID: R-122. Ближайшая очередь: качество автооценки/подсказок и восстановление Pythonоценок по receipt; материалы61 пока отложены. Старые блоки текущихстендов ниже MAIN01 — исторические снимки.\n'
    else:
        first=text.index('\n',text.index('Обновлено:'))
        text=text[:first]+'\n\n'+summary+'\n\n### LOG-0046 · 11.11.2026 · Основная интеграция MAIN01\n\n-248source перенесены вwork/lat-ai;35changed/57added/0removed,191backupverified. Existing runtime tf11kit сохранён,14таблицunchanged доsyntheticwrites. Старые191/209/244snapshot и отдельныйpilotSQLite сохранены.\n-91/37/335/4/6tests;43HTTP/DBpassed,4modelauto_checked,docready. Браузервход/уроки/старыеоценки/новыедокументыverified. Повторныйстартblockedнаoccupiedport.\n-Source/DBrollbackописан; studyUI/quality и SDK/recoverylimitsнеобъявленыготовыми. Отчёт outputs/main-integration-2026-11-11. Не коммитили, не пушили, ПКневыключали.\n\nНиже — исторические записи прошлых срезов; адреса и активная копия определяются MAIN01.\n'+text[first:]
    path.write_text(text,encoding='utf-8')
print('MAIN01 README, source manifest, report, rollback, canonical roadmap and sole STATUS updated.')

if __name__=='__main__': pass
