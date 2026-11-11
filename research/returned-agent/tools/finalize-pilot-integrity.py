from pathlib import Path
import json,hashlib,zipfile,shutil
root=Path(__file__).resolve().parent.parent;out=root/'outputs/ai-pilot-integrity-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
live=read(out/'live-three-series-analysis.json');audit=read(out/'source-and-package-audit.json');packages=read(out/'packages-verification.json')
report='''LAT AI — надёжность пилота, разбор независимого ревью, локальный запуск
11 ноября2026. Только AI-инструменты, AI-документация и запуск локального стенда.

Главный новый результат
При проверке нового инструмента U02 получил заниженную оценку во всех3 сериях:
checks=[false,true,true] вместо авторского[true,true,true]. Ранее в stability48 U02
получал отказ. Это не исправлено; оба прохода одной модели согласились в ошибке.
V11 верен3/3. Всего2 известных текста×3 серии=6 вызовов:3 верных,3 неверных,0 отказов.
Первичная серия:1 верный,1 неверный из2;0/2 нестабильных исходов внутри новых3 серий.
Между историческими и текущими запусками исход U02 изменился; нельзя обещать постоянную
воспроизводимость. Причина смены вывода не установлена. Промпты/checks/gate не правились.
Техническое завершение3/3 серий НЕ означает прохождение качества. Это не новый holdout.

Разбор замечания о «пересчёте32»
Проверены JSON,freeze SHA и первичные метрики. H01–H32 и V01–V32 — разные наборы:
H:26 верных,0 неверных,6 отказов,joint26; V:25 верных,1 неверная,6 отказов,joint24.
Общих ID/точных task+answer нет; обаSHA совпали с исходной заморозкой. Пересчёта не было.
Ошибкой документации было повторение названия «новый32». Создан ERRATA_DATASETS.txt,
в актуальных точках входа указаны H32/V32. Исторические первичные метрики не переписаны.
Условные односторонние95% верхние границы0/26=10,883%,1/26=16,983%; это не реальный
риск на учениках. Цель2% не установлена этими авторскими наборами.
Replay160 содержит160 уникальных текстов L24+N24+U48+H32+V32, все известные разработке.
Отдельная историческая стабильность48 —8 текстов×6:0/8 нестабильных внутри той серии.

Что реализовано для roadmap L01 и подготовки T01
1. Замороженный run plan: SHA25 файлов AI-core/data,5 инструментов,9 файлов frozen dataset,
   reviewed rubric,Node version/platform/arch и последовательность3 серий. До загрузки модели
   и перед каждой работой проверяются хеши; expected не передаётся генератору.
   Модель/аппаратная конфигурация декларируются оператором, SHA весов не проверена.
   Контрольные суммы защищают от незаметных случайных изменений, не заменяют подпись/доступ.
2. При сетевой потере сохраняется строка transport_unknown и incomplete summary с not_run.
   Следующие случаи не отправляются, повторов POST нет; ошибка загрузки и недоказанная
   выгрузка также дают incomplete. Квитанции о завершении/выгрузке и SHA каждой строки сохранены.
3. Сравнение3 серий: первична всегда1-я, повторы не увеличивают n. По каждому ответу —
   частоты checks/отказов, число разных исходов/цитат; по задачам/категориям — отдельные метрики.
   Считаются условный CI, исходное согласие и каппа Коэна по каждому критерию у двух людей,
   сравнение модели с итоговой разметкой только среди выданных оценок; coverage отдельно.
   Постоянные метки дают undefined kappa, не ложную единицу. Полнота цитат требует человека.
4. Автопроверка слепых папок:4 допустимых файла, точные ID/ответы/рубрика, пустые checks,
   отсутствие дополнительных меток/category/group/заметок и посторонних файлов.
   Export автоматически выполняет проверку, отдельная команда повторяет её перед выдачей.
   Персональные сведения или подсказки внутри исходного ответа обязан проверить человек.

Локальный launcher
Добавлен эксклюзивный файловый дескриптор на время запуска, без удаления/перехвата по возрасту.
Проверенный уже работающий экземпляр возвращается без новых процессов; чужой владелец
портов/ошибка чтения не разрешают запуск. Новый PID record пишется только после readiness
И проверки, что все3 порта принадлежат только что созданным процессам. Ранний выход ребёнка
(в том числе из-за database locked) не затирает старую запись; завершаются только Process
objects, созданные неудавшимся запуском, до включения модели. Общий LM Studio не останавливается.
Проверены6 сценариев helper (моки занятых портов/ошибки WMI/выхода процесса и настоящий
эксклюзивный файловый lock), живой повторный старт с неизменнымSHA processes.json и полный
штатный Restart. Это не утверждение о проверке всех гонок Windows или живой инъекции блокировки БД.
После тестов стенд ready/idle,модель включена; локальные60/70/80с прежние, общие8/9/10с прежние.

Проверки
11 Node тестов frozen runner +7 прежних pilot +4 анализа/слепого аудита +6 launcher guard прошли.
Инженерный ZIP полностью распакован;11+7+4 теста прошли также из извлечённой копии.
Живые серии завершены и каждый собственный экземпляр модели retired proven=true, без retry.
Время6 вызовов:медиана12,569с,max14,649с; proposal median8,467с,verification median4,069с.
Это2 известных текста, не нагрузочная оценка группы и не универсальный максимум.
Все209 файлов проекта сверены: изменены только2 AI-документа; исполняемый AI-код и101
backend/assets/index файл побайтово прежние. Общие80Node/19Django/335core этого неизменного
исполняемого кода уже проходили на предыдущем этапе; здесь заново их не заявляем.

Ручной старт
Координатор по ответу владельца: «разраб 1 П». Начало сбора запланировано12.11.2026.
Короткий ZIP —7 файлов. Инженерный —14 файлов. Оба провереныCRC/SHA; прежний43-файловый
пакет и его архив сохранены. Предложение:80 реальных работ по2–3 задачам как пилот процесса;
крупная подтверждающая выборка отдельно. Предложены заранее пороги согласия90%/каппа0,8
и будущие ошибки2%/отказы20%; они НЕ утверждены владельцем/преподавателем.
Назначить двух проверяющих и третьего для споров; согласовать объём/рубрику/срок завершения,
основания обработки, необходимые согласия, обезличивание, доступ и сроки удаления ДО сбора.
Организационная форма не является юридическим заключением. При непрояснённых основаниях
сбор переносится. Наступление даты само по себе не разрешает обработку данных.
Пилот не проведён, людей не приглашали, сообщения не отправляли. T01/S02/D01/D02 открыты.

Открыто
V05 и теперь текущий U02 — недооценка; U26/H18 — прежние отказы; одинаковая ошибка двух
проходов остаётся. Третий независимый судья не реализован; новые веса/платные API не добавлялись.
Правила отрицаний не использовались как новый автоматический судья без реальных данных.
AI receipt API готов; backend/frontend применение/очередь — ответственность других разработчиков.
Следующий человеческий вход: реальные обезличенные ответы и независимые разметки.
Код/отчёты сохранены в отдельном backup, безcommit/push/reset.
'''
(out/'REPORT.txt').write_text(report,encoding='utf-8')
(out/'WORKLOG.txt').write_text('''2026-11-11 — active request: continue AI roadmap. Scope unchanged: AI only.
Read active AGENTS/roadmap; chose pilot integrity, series analysis and local launch reliability.
Snapshot previous statistics/harness/launcher; existing historical reports/ZIPs left unchanged.
Created frozen runner with preflight and partial/unknown outcome reports;11 tests passed.
Incoming independent review audited against original H/V datasets. No metric recount occurred.
Owner confirmed coordinator «разраб 1 П», target collection12.11.2026; no consent/approval inferred.
Added blind handout verifier and paired kappa/three-series analysis;7+4 Python tests passed.
Prepared synthetic smoke from known V11/U02, not real_student. Preliminary plan lacked tool pins;
added pins and created separate plan-tools-pinned.json before any inference; original plan retained.
Retired only owned stand model, verified idle/off; ran3 owned loads with2 cases each; all retired proven.
An early analyze command ran before series3 terminal summary and raised FileNotFoundError; it produced
no analysis file and did not dispatch/retry inference. Waited for completion, then computed final analysis.
Observation: V11 correct3/3,U02 undergraded3/3; primary1correct/1wrong, no refusals. No retuning.
Added guard/helper/launcher tests6/6; idempotent live start preserved byte hash of process record.
Full verified restart succeeded; final model ready/idle,local60/70/80 unchanged. No foreign model killed.
Built small human ZIP7files and engineer ZIP14files; CRC/SHA verified; extracted tools11+7+4 pass.
Source audit209 files,2 AI docs changed,101 backend/assets/index unchanged; executable AI unchanged.
Documented H32/V32 separately, cross-session U02 difference, primary/repeat limits, unresolved human gates.
Backup contains current dirty tree, tools, evidence and existing verified Git bundle; no commit/push.
''',encoding='utf-8')
prefix='''## Продолжение AI: пилот, воспроизводимость и запуск · 11.11.2026

Координатор пилота: **разраб 1 П**; начало сбора запланировано **12.11.2026**.
Предложен первый объём80 реальных работ по2–3 задачам; размер/пороги/согласия ещё
утверждаются до сбора. Короткий пакет7 файлов, инженерные инструменты отдельнымZIP.
Реальных ответов и независимых разметок нет; T01/S02/D01/D02 открыты.

**Новый дефект наблюдения:** на двух известных текстах в3 сериях V11 верен3/3,
U02 занижен3/3 вместо прежних отказов. Промпты/gate/checks не менялись.
0/2 нестабильных внутри этих серий не означает правильность: первично1верный/1неверный.
Замороженный runner проверяет SHA до модели, сохраняет unknown и не повторяет POST;
анализ сравнивает3 серии и согласие людей, слепая выгрузка проверяется автоматически.

**Уточнение цифр:** H01–H32:26/0/6,joint26; отдельный V01–V32:25/1/6,joint24.
Это разные наборы, пересчёта не было. Replay160 —160 разных известных текстов;
историческая стабильность48 —8×6. [Разъяснение сSHA](<E:/Startup Tau/outputs/ai-pilot-integrity-2026-11-11/ERRATA_DATASETS.txt>).

28 технических тестов новых/затронутых инструментов прошли, обе упаковки проверены.
Локальный launcher сериализует запуск, проверяет собственные порты до записиPID;
живые повторный старт и полныйRestart прошли. Стенд ready/idle,60/70/80с прежние.
Исполняемый AI и101 backend/assets/index файл неизменны; обновлены2 AI-документа.

[Короткий пилотZIP](<E:/Startup Tau/outputs/ai-pilot-integrity-2026-11-11/LAT-AI-PILOT-START-2026-11-12.zip>) ·
[ИнженерныйZIP](<E:/Startup Tau/outputs/ai-pilot-integrity-2026-11-11/LAT-AI-PILOT-ENGINEER-TOOLS-2026-11-11.zip>) ·
[Отчёт/логи](<E:/Startup Tau/outputs/ai-pilot-integrity-2026-11-11/REPORT.txt>).

'''
for name in ['outputs/STATUS.md','outputs/AI_ROADMAP.md','START_HERE.md']:
 p=root/name;text=p.read_text(encoding='utf-8-sig')
 # Qualify unambiguous historical headline counts; never alter the numbers or source reports.
 for a,b in [('Новый frozen32:26','Набор H01–H32 (evidence-v2h), первый прогон:26'),('Новый frozen32:25','Набор V01–V32 (evidence-v3d), первый прогон:25'),('Новый замороженный32:26','Набор H01–H32, первый прогон:26'),('Новый замороженный набор:26','Набор H01–H32, первый прогон:26')]:text=text.replace(a,b)
 if name=='START_HERE.md':
  title='# LAT AI — начало работы\n';assert text.startswith(title);text=title+'\n'+prefix+text[len(title):]
 else:text=prefix+text
 p.write_text(text,encoding='utf-8')
with (root/'AGENTS.md').open('a',encoding='utf-8') as f:f.write('''
- Продолжение11.11: координатор «разраб 1 П», начало сбора12.11.2026 по ответу владельца. Мини-пилот80 ответов/2–3 задачи и пороги90%/каппа0,8/ошибки2%/отказы20% только предложены; согласия/люди/реальные данные не получены. КороткийZIP7files и инженерныйZIP14files:outputs/ai-pilot-integrity-2026-11-11. Полный43file архив сохранён. T01/S02/D01/D02 открыты.
- H32=H01–H32(26correct/0wrong/6refusal,joint26) и V32=V01–V32(25/1/6,joint24) — разные наборы с разнымиSHA; пересчёта нет. Не называть оба «новый32» безID. Replay160=160 разных известных текстов; stability48=8×6. Разъяснение:ERRATA_DATASETS.txt в новом отчёте.
- Новое наблюдение на неизменном evidence-v3e: V11/U02×3 в3 отдельных загрузках; V11 correct3/3,U02 undergrade3/3 [false,true,true], ранее U02 refused. Внутри0/2 нестабильных,но между историческими запусками исход изменился; причина не установлена. Это известный smoke,не holdout; не скрывать ошибку/не заменять прежние результаты. Промпты/gate не подстраивались.
- Новый frozen runner tools/prepare-assessment-run.mjs + run-frozen-assessment.mjs проверяет SHA AI/инструментов/данных до загрузки; unknown прекращает серию безretry,summary сохраняетnot_run/retirement. analyze-frozen-pilot.py требует3 завершённые серии и всегда берёт1-ю первичной. verify-blind-review.py проверяет выдаваемую пустую папку; персональные данные внутри текста всё равно проверяет человек.
- Launcher: эксклюзивный файловый дескриптор,безage-steal; no-Restart уже работающего собственного экземпляра идемпотентен. PID record обновляется после проверки новых детей и владения портами. Проверены6guardtests,живойno-duplicate start иRestart. Стендready/idle,локальные60/70/80с прежние.28tooltests passed; исполняемыйAI и101защищённый исходник неизменны. Никаких сообщений людям/commit/push не было.
''')
backup=out/'backup';backup.mkdir(exist_ok=False)
shutil.copy2(root/'outputs/ai-continuation-2026-11-11/backup/history.bundle',backup/'history.bundle')
files={f'lat-ai/{name}':root/'lat-ai'/name for name in audit['after_sha256']}
for p in (root/'tools').iterdir():
 if p.is_file() and p.suffix in ['.py','.mjs','.ps1']:files['tools/'+p.name]=p
for name in ['AGENTS.md','START_HERE.md','outputs/STATUS.md','outputs/AI_ROADMAP.md']:files[name]=root/name
for p in out.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(out)
 if rel.parts[0] in ['backup','extracted-package-check','ENGINEER-TOOLS','LAT-AI-PILOT-START-2026-11-12']:continue
 if p.suffix not in ['.json','.jsonl','.txt','.log','.mjs','.py','.ps1','.sha256','.zip']:continue
 files['evidence/'+rel.as_posix()]=p
files['history.bundle']=backup/'history.bundle'
manifest={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in files.items()}
target=backup/'LAT-AI-PILOT-INTEGRITY-SOURCE.zip'
with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
 for name,p in files.items():z.write(p,name)
 z.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(target) as z:
 assert z.testzip() is None
 for name,sha in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==sha
result={'path':str(target),'project_files':209,'files':len(manifest)+1,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'verified':True,'git_bundle':'Copy of earlier verified history bundle; HEAD unchanged; no git writes.'}
(backup/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
