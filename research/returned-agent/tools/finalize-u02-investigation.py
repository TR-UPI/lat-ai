from pathlib import Path
import json,hashlib,subprocess,zipfile,shutil
root=Path(__file__).resolve().parent.parent;out=root/'outputs/u02-investigation-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
offline=read(out/'offline-analysis.json');summary=read(out/'investigation-summary.json')
fingerprint=read(out/'model-fingerprint.json');after_model=read(out/'model-fingerprint-after.json')
assert fingerprint['sha256']==after_model['sha256']
previous=read(root/'outputs/ai-pilot-integrity-2026-11-11/source-and-package-audit.json')['after_sha256']
names=subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],cwd=root/'lat-ai').decode().split('\0')
current={name:hashlib.sha256((root/'lat-ai'/name).read_bytes()).hexdigest() for name in sorted(set(filter(None,names))) if (root/'lat-ai'/name).is_file()}
assert current==previous,'Project tree changed during diagnostic'
status=read(out/'final-runtime-status.json');assert status['tutor']['ready'] and not status['tutor']['busy'] and not status['tutor']['quarantined']
report='''LAT AI — почему U02 изменился с отказа на заниженную оценку
11 ноября2026. Только расследование AI; промпты, рубрики, gate и исполняемый код не менялись.

Главный вывод
Переход локализован в модельном выводе первого прохода и воспроизведён при разной истории
вычислений экземпляра Qwen/LM Studio. Старый/новый оценщики одинаково обрабатывают те же raw.
При первом U02 на свежей загрузке или после N05→U15 первый проход признаёт все3 критерия;
второй выдаёт[false,true,true], поэтому gate возвращает отказ.
После V11 первый проход тоже выдаёт[false,true,true]; gate видит согласие и выдаёт2/3.
Это объясняет смену отказа на занижение без изменения промптов и рубрик.

Что изменилось в наблюдаемом смысле
U02: «Результат на экране — 32. Он получается склейкой: оператор + соединяет строку «3»
со строкой «2», а не складывает числа.»
Задание: print("3" + "2"). Первый критерий требует назвать тип обоих операндов.
В ответе оба прямо названы строками внутри описания операции. Авторская метка —[true,true,true].
Исторический proposal ссылался на S2 для типов, новый отдаёт start/end=null без counter.
Verifier во всех6 исторических,3 недавних и12 диагностических U02 сохраняет[-1,0,0].
Отрицания/противоречия не сработали: counter=null. Ввод/вывод не обрезан, finish_reason=stop,
reasoning_tokens=0, output_tokens ниже192. Это не timeout, не невалидный JSON и не отказ модерации.
Оба прохода могут пропустить один явный факт; согласие не означает правильность.
Дополнительное наблюдение для ручного разбора: verifier criterion_2=0 ссылается на предложение
о результате32, а не на описание склейки. Gate использует его checks; финальные цитаты
берёт из proposal. Смысл ссылки verifier автоматически не проверяется.

История и проверка входов
- Сопоставлены6 U02 из stability48 и3 U02 из последней проверки инструмента.
  Текст ответа, метки и input_tokens совпадают; меняется только proposal criterion_1.
- Исторический snapshot D сверён с6 исходными SHA candidate-d-freeze.json.
  assessment.mjs,assessment-verifier.mjs,local-model.mjs и verifier rubric побайтово прежние.
  Изменения между D/E — контекст цитат if/else и metadata revision; для L1.types.1 не влияют.
- Через настоящий LocalModel с fetch-заглушкой реконструированы оба HTTP-запроса старой
  и текущей версий. При одинаковом model ID их тела полностью совпали. Это реконструкция,
  а не заявление, что исторические байты сетевого запроса были записаны тогда.
- Перекрёстная матрица raw2×2: старый proposal с любым verifier →отказ; новый proposal с
  любым verifier →[false,true,true]. Все12 новых U02 дают один результат в старом и новом validator.
- Во всех новых живых U02 записаны полные request/response bodies. После нормализации только
  уникального model ID два SHA постоянны и совпадают с реконструкцией. Другие ответы не входят
  в messages U02; в запросе только его system/user. Запросы идут прямо LocalModel→LM Studio:
  журнал AI worker, Django, frontend и применение прогресса в эксперименте не участвуют.

Фиксированный эксперимент на свежих загрузках
C1: U02 первым          →отказ (proposal3/3,verifier2/3)
A1: N05→U15→U02         →отказ
B1: V11→U02             →занижение2/3 (оба прохода2/3)
B2: V11→U02             →занижение2/3
A2: N05→U15→U02         →отказ
C2: U02 первым          →отказ
Порядок C,A,B,B,A,C и код заморожены сSHA до inference. Каждая строка — свой доказанно
загруженный и выгруженный экземпляр. Это2 повтора на условие, а не статистический допуск.

Внутри одного экземпляра: уточнение причинной гипотезы
После первого эксперимента заранее заморожены два отдельных follow-up протокола.
B→A→B в одном экземпляре: занижение →занижение →занижение.
A→B→A в другом экземпляре: отказ →отказ →отказ.
Здесь A=N05,U15,U02; B=V11,U02. Instance ID внутри каждой тройки одинаковый.
Простая гипотеза «результат задаёт только последнее предшествующее задание» НЕ подтвердилась.
Наблюдаемый режим закрепляется после первого вычисления U02 в экземпляре и сохраняется
при дальнейшей смене последовательности. Перезагрузка плюс фиксированный предшествующий
порядок воспроизводит разные режимы. Все исходы, в том числе отрицательный результат первой
гипотезы B-A-B, сохранены; не заменяли прогоны удачными повторами.

Что доказано и что остаётся неизвестным
Доказан наблюдаемый эффект истории вычислений/состояния экземпляра при неизменных входах;
выделена конкретная смена proposal criterion_1, которая делает gate согласованно неверным.
Стабильные повторы одного текста в одном порядке могли скрывать зависимость от состояния.
Кэш/контекстные checkpoints либо численные особенности вычислений — гипотезы внутреннего
механизма. Они НЕ изолированы этим экспериментом. Снимок runtime показывает checkpoints32,
flash_attention=true,eval_batch2048,physical_batch512,parallel1,KV offload=true,context8192;
конфигурации8 экземпляров совпали. Из наличия этих настроек нельзя вывести виновный компонент.
Нет доказательства, что модель «помнит разговоры» или что старая оценка пришла из журнала.
Не меняли cache/seed/GPU настройки и не применяли недокументированные параметры.

Модель и воспроизводимость
Qwen3.5-9B-Q4_K_M.gguf,5680522464 байта; SHA до и после расследования одинаковый:
03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8.
LM Studio CLI43d4b26; backend llama.cpp-win-x86_64-nvidia-cuda12-avx2 2.68.0;
RTX2050 4096MiB,driver591.86; Node24.11.1. Текущий runtime/веса зафиксированы.
В исторических опытах SHA весов не записывался, поэтому их полное побайтовое тождество
задним числом не доказано. Но текущий эксперимент воспроизводит оба исхода на одном файле.
system_fingerprint в текущем API равен ID экземпляра, не SHA весов; хеш снят отдельно.

Объём и сохранность
8 диагностических загрузок;27 оцениваний известных текстов;54 chat-completion POST.
Из них12 наблюдений U02:7 отказов,5 занижений. Это описание диагностики, не частота ошибок
на учениках и не новый holdout. Каждый свой экземпляр retired proven=true,unknown/retry нет.
Полные тела, времена стадий, model config, протоколы,SHA,raw и журнал событий сохранены.
Все209 файлов проекта побайтово прежние, включая промпты/рубрики и101 backend/assets/index.
Штатный стенд возвращён ready/idle,модель включена,локальные60/70/80с прежние.

Следующие действия по roadmap
1. Дополнить план реального пилота заранее заданным порядком работ и условиями первой/повторной
   обработки: фиксировать прогрев, свежесть экземпляра и последовательность, не только temperature0.
   Три серии с одним и тем же порядком не закрывают найденную зависимость. Новые порядки замораживать
   ДО результатов; прежние frozen наборы/отчёты не переписывать.
2. Передать воспроизводимый минимальный случай специалисту по runtime для изоляции cache/checkpoint/
   численного пути. Материалы подготовлены локально, внешняя отправка/issue не выполнялись.
3. Сам по себе свежий экземпляр переводит U02 в отказ, но не исправляет постоянную ошибку verifier.
   Перестановку/прогрев заданий не выдавать за исправление оценки. Нужна отдельная проверяемая защита
   от согласованно неверного решения либо более независимый судья, без автодобавления балла по regex.
4. До разрешения дефекта сохранять теневой режим и ручную проверку; фактический пилот/допуск
   преподавателя не выполнены. Пакет отдельной ручной проверки U02 приложен.

Воспроизведение
Сначала изучить order-protocol.json и summary всех трёх экспериментов. Скрипты freeze/run
пишут в новые фиксированные каталоги; повторный запуск в существующие пути запрещён.
Для нового диагностического запуска использовать отдельную копию скриптов с НОВЫМ каталогом,
зафиксировать еёSHA до inference; не менять исходный архив и не запускать во время работы
чужой модели. Перед/после — штатный retire/enable только своего экземпляра.
Реконструкция: tools/investigate-u02-offline.mjs; свежие загрузки:diagnose-u02-order.mjs;
crossover:diagnose-u02-crossover.mjs иdiagnose-u02-reverse-crossover.mjs;
сводка/проверки:analyze-u02-investigation.mjs. Старый snapshot D нужен для сравнения validator.
'''
(out/'REPORT.txt').write_text(report,encoding='utf-8')
(out/'SOURCES.txt').write_text('''Primary local evidence: historical SHA-verified source snapshot,6 historical raw U02,3 recent raw U02,12 new raw U02 with full request/response bodies; frozen protocols and model metadata.
Official documentation consulted for load parameters and CLI, not as proof of the internal cause:
LM Studio Load a model — https://lmstudio.ai/docs/developer/rest/load
LM Studio lms load — https://lmstudio.ai/docs/cli/local-models/load
Actual config fields are captured from the installed runtime; documentation does not establish cache as the cause.
Server log for2026-11-11 was zero bytes; no historical server trace was invented.
''',encoding='utf-8')
(out/'WORKLOG.txt').write_text('''2026-11-11. Request: investigate U02 undergrade instead of refusal; no prompt/backend/frontend changes.
Read active instructions and roadmap. Compared6 historical stability U02 vs3 recent series.
Created read-only offline reconstruction: old/current normalized payloads identical; crossed raw matrix2x2 localizes change to proposal criterion1.
Historical D snapshot6 hashes verified. Current model list/GPU/CLI read; target model only used.
Sandbox could not read ~/.lmstudio; approved read-only inspection resolved actual GGUF path.
Default ~/.lmstudio/models target path absent; model-index pointed to E:/Horror game/LocalAI/models.
No conversations/credentials read, no runtime settings changed. Current server log0bytes, no old trace available.
GGUF SHA and current backend version recorded; historical weight SHA absent.
Frozen C,A,B,B,A,C protocol before inference; stand's owned model retired, status off/idle verified.
Six owned loads/12 assessments finished,all retired proven; freshA/C refuse,B undergrades.
Frozen B-A-B follow-up,one instance7 assessments. All3 U02 undergraded; immediate-previous-only hypothesis not supported.
Frozen reverse A-B-A follow-up,one instance8 assessments. All3 U02 refused. First observed mode persisted within instance.
Total8loads27assessments54POST;12U02 =7refusals5undergrades. No transport failures/automatic retries.
All U02 request hashes match reference; config snapshots identical; old/current validators identical on12raw outputs.
Full project209 hashes unchanged. Restored stand model to ready/idle; weightSHA after equals before.
No prompt/gate/rubric edits, no backend/frontend writes, no model downloads, no messages/issue/push/commit.
Report,manual-review supplement,source/evidence archive and roadmap updates saved. Internal cache/numerical mechanism remains unisolated.
''',encoding='utf-8')
(out/'source-audit.json').write_text(json.dumps({'files':len(current),'changed':[],'all_project_files_unchanged':True,'protected_files':sum(p.startswith(('backend/','assets/')) or p=='index.html' for p in current),'after_sha256':current},indent=2),encoding='utf-8')
manual=out/'U02-HUMAN-REVIEW';manual.mkdir(exist_ok=False)
(manual/'READ_ME.txt').write_text('''LAT AI — отдельная диагностическая проверка U02, не слепой пилот.
Это известный авторский ответ с показанными машинными результатами. Не смешивать его с новой слепой разметкой реальных работ.
Нужно подтвердить трактовку критериев/смысл цитат, не оценить статистическое качество модели.
Результаты модели/авторская метка — материал для разбора, не инструкция принять именно их.
Кто проверил / дата / решение: НЕ ЗАПОЛНЕНО.
Runtime-специалисту: протокол свежих загрузок C,A,B,B,A,C и двух crossover описан в ROOT_CAUSE_NOTE.txt;
все полные сетевые тела и config доступны в отчёте расследования. Внешняя отправка не выполнялась.
''',encoding='utf-8')
rubric=read(root/'lat-ai/integration/ai/core/data/assessment-rubrics.json')['tasks']['L1.types.1']
case={'task_key':'L1.types.1','code':rubric['code'],'criteria':rubric['criteria'],'answer':offline['answer'],'author_expected':offline['author_expected'],'historical_proposal':[True,True,True],'stable_verifier':[False,True,True],'undergrading_proposal':[False,True,True],'teacher_checks':[None,None,None],'teacher_reason':'','questions':['Явно ли названы типы обоих операндов во втором предложении?','Достаточно ли первого предложения «Результат на экране — 32» для критерия о склейке?','Какие точные фрагменты поддерживают каждый критерий и есть ли противоречия?']}
(manual/'CASE_REVIEW.json').write_text(json.dumps(case,ensure_ascii=False,indent=2),encoding='utf-8')
(manual/'ROOT_CAUSE_NOTE.txt').write_text('''Наблюдение на неизменных payload/модели/оценщике: при свежем экземпляре C=U02 первым и A=N05,U15,U02 дают отказ2/2 каждое; B=V11,U02 даёт2/3в2/2.
Внутри экземпляра B-A-B сохраняет три занижения, A-B-A — три отказа. Проверены оба порядка.
Смена proposal criterion1 [true→false] при постоянном verifier[false,true,true] превращает расхождение в неверное согласие.
Гипотеза только о последнем предыдущем задании не подтверждена. Первый режим сохраняется до выгрузки.
Точный механизм cache/checkpoint/численных вычислений не изолирован. Не выдавать наблюдение за доказанный баг конкретного компонента.
GGUF Qwen3.5-9B-Q4_K_M SHA03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8;
runtime llama.cpp NVIDIA CUDA12 AVX2 2.68.0;CLI43d4b26;context8192;batch2048/physical512;checkpoints32;flash_attention=true;parallel1;temperature0;max_tokens192.
Полный отчёт: outputs/u02-investigation-2026-11-11/REPORT.txt. Никаких исправлений промптов или снижения порогов не применено.
''',encoding='utf-8')
manual_zip=out/'LAT-AI-U02-HUMAN-REVIEW-2026-11-11.zip'
with zipfile.ZipFile(manual_zip,'x',zipfile.ZIP_DEFLATED) as z:
 for p in manual.iterdir():z.write(p,manual.name+'/'+p.name)
with zipfile.ZipFile(manual_zip) as z:
 assert z.testzip() is None
 for p in manual.iterdir():assert z.read(manual.name+'/'+p.name)==p.read_bytes()
prefix='''## U02: переход отказ → занижение воспроизведён · 11.11.2026

Промпты, рубрики, gate и все209 файлов проекта неизменны. U02 меняет первый проход:
3/3 против verifier2/3 →отказ; proposal2/3 против того же verifier2/3 →занижение.
Реконструкция старых/новых payload совпала;12 новых U02 имеют одинаковые requestSHA
после нормализации только instance ID. Старый/новый validator дают одинаковые результаты.

На свежих загрузках U02 первым(C) и послеN05→U15(A) отказывает2/2 в каждом условии;
послеV11(B) занижается2/2. Внутри одного экземпляра B-A-B остаётся занижением3/3,
A-B-A остаётся отказом3/3. Важна история до первого U02/состояние экземпляра,
а не просто последнее задание. Внутренний механизм cache/checkpoint/численных
вычислений НЕ изолирован; перестановка или reload не исправляют ошибку verifier.

Всего8загрузок,27известных оцениваний(54modelPOST),12наблюденийU02:7отказов/5занижений.
Это диагностика,НЕ новый holdout/риск на учениках. Raw,полные HTTP тела,config,SHA сохранены;
все8 своих моделей retired proven;unknown/retry нет. Штатный стенд возвращёнready/idle.
GGUF SHA до/после одинаков;исторической SHA весов нет. Backend/frontend не тронуты.
До реального пилота фиксировать порядок/прогрев/свежесть экземпляра,включить заранее
заданные разные порядки; одинаковый порядок3 серий не закрывает обнаруженный риск.

[Отчёт и протокол](<E:/Startup Tau/outputs/u02-investigation-2026-11-11/REPORT.txt>) ·
[Отдельная ручная проверкаZIP](<E:/Startup Tau/outputs/u02-investigation-2026-11-11/LAT-AI-U02-HUMAN-REVIEW-2026-11-11.zip>).

'''
for name in ['outputs/STATUS.md','outputs/AI_ROADMAP.md','START_HERE.md']:
 p=root/name;text=p.read_text(encoding='utf-8-sig')
 if name=='START_HERE.md':
  title='# LAT AI — начало работы\n';assert text.startswith(title);text=title+'\n'+prefix+text[len(title):]
 else:text=prefix+text
 p.write_text(text,encoding='utf-8')
with (root/'AGENTS.md').open('a',encoding='utf-8') as f:f.write('''
- U02 investigation11.11: user explicitly forbids prompt/backend/frontend changes. All209 project files unchanged. Frozen27 known assessments/8owned loads(54POST) reproduce first-pass state dependence: freshC(U02 first) andA(N05,U15,U02) refused2/2 each; B(V11,U02) undergraded2/2. Within same instance B-A-B undergraded3/3,A-B-A refused3/3. First observed U02 mode persists; immediate-previous-only hypothesis not supported. Cache/checkpoint/numerical mechanism NOT isolated; do not claim specific runtime bug proven. Verifier always[false,true,true],proposal change causes disagreement→wrong agreement. Old/current validators identical; normalized U02payload SHA identical12/12. Report:outputs/u02-investigation-2026-11-11/REPORT.txt;manualZIP separate. All own instances retired proven,stand restoredready/idle,limits unchanged. ModelSHA03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8 before/after;historical weightSHA absent. No automatic retries,external messages,commit/push. Next pilot must predeclare different orders/freshness/warmup; fixed-order repeats alone hide this effect. Do not present reload/order warmup as a grading fix;U02 remains unresolved for reliable scoring.
''')
backup=out/'backup';backup.mkdir(exist_ok=False)
shutil.copy2(root/'outputs/ai-pilot-integrity-2026-11-11/backup/history.bundle',backup/'history.bundle')
files={f'lat-ai/{name}':root/'lat-ai'/name for name in current}
for p in (root/'tools').iterdir():
 if p.is_file() and p.suffix in ['.py','.mjs','.ps1']:files['tools/'+p.name]=p
for name in ['AGENTS.md','START_HERE.md','outputs/STATUS.md','outputs/AI_ROADMAP.md']:files[name]=root/name
for p in out.rglob('*'):
 if p.is_file() and p.relative_to(out).parts[0]!='backup' and p.suffix in ['.json','.jsonl','.txt','.log','.sha256','.zip']:files['evidence/'+p.relative_to(out).as_posix()]=p
files['history.bundle']=backup/'history.bundle'
manifest={name:hashlib.sha256(p.read_bytes()).hexdigest() for name,p in files.items()}
target=backup/'LAT-AI-U02-INVESTIGATION-SOURCE.zip'
with zipfile.ZipFile(target,'x',zipfile.ZIP_DEFLATED) as z:
 for name,p in files.items():z.write(p,name)
 z.writestr('MANIFEST.json',json.dumps(manifest,indent=2))
with zipfile.ZipFile(target) as z:
 assert z.testzip() is None
 for name,expected in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==expected
proof={'source_files':209,'all_project_files_unchanged':True,'manual_zip':{'path':str(manual_zip),'files':3,'sha256':hashlib.sha256(manual_zip.read_bytes()).hexdigest(),'verified':True},'backup':{'path':str(target),'files':len(manifest)+1,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'verified':True},'stand_ready':True,'model_weights_unchanged_during_investigation':True}
(out/'delivery-verification.json').write_text(json.dumps(proof,indent=2),encoding='utf-8');print(json.dumps(proof))
