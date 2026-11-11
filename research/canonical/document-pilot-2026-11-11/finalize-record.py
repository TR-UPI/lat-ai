from pathlib import Path
import hashlib,json,re,shutil,zipfile
project=Path(r'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-08/shag-model-selection')
worktree=Path(r'C:/Users/ASUS ROG STRIX/.codex/worktrees/lad-document-pilot/git-restore-check')
out=project/'outputs/document-pilot-2026-11-11'
deliver=Path(r'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-10/lad-ai-c-users-asus-rog-3/outputs')
archive=deliver/'LAD-AI-document-pilot-2026-11-11.zip'
verification=json.loads(archive.with_suffix('.verification.json').read_text(encoding='utf-8'))
with zipfile.ZipFile(archive) as z:
    entries=json.loads(z.read('LAD-AI-Document-Pilot/MANIFEST.json'))['files']
baseline=Path(r'C:/Users/ASUS ROG STRIX/Documents/Codex/lat-return-1111/workspace/lat-ai')
old={p.relative_to(baseline).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in baseline.rglob('*') if p.is_file()}
new={entry['path']:entry['sha256'] for entry in entries}
delta={'baseline_files':len(old),'release_files':len(new),'unchanged':[p for p in old if old[p]==new.get(p)],
       'changed':[p for p in old if p in new and old[p]!=new[p]],'added':sorted(new.keys()-old.keys()),'removed':sorted(old.keys()-new.keys())}
(out/'source-delta.json').write_text(json.dumps(delta,ensure_ascii=False,indent=2),encoding='utf-8')
for name in ['PILOT_RUN_REPORT.txt','NODE_PILOT_REPORT.txt','DJANGO_PILOT_REPORT.txt','FRONTEND_PILOT_REPORT.txt','FINAL_PILOT_REVIEW.txt','DOCUMENT_PILOT_SPEC.md']:
    shutil.copyfile(worktree/'docs/ai'/name,out/name)
for name in ['live-pilot-test.py','geography-pilot-test.py','final-http-check.py','verify-pilot.py']:
    shutil.copyfile(worktree/'.runtime'/name,out/name)
for path in (worktree/'.runtime/pilot-check').glob('synthetic-*.jsonl'):
    shutil.copyfile(path,out/path.name)
shutil.copyfile(worktree/'.runtime/pilot-check/test-runtime.jsonl',out/'test-runtime.jsonl')
shutil.copyfile(archive.with_suffix('.verification.json'),out/'archive-verification.json')
report=(out/'PILOT_RUN_REPORT.txt').read_text(encoding='utf-8')
report+='\nУПАКОВКА\n'+json.dumps(verification,ensure_ascii=False,indent=2)+'\n'
report+='Архив распакован в отдельный путь с пробелами: prepare/migrate/seed и Django check прошли.\nВсе закреплённые Python requirements разрешены и скачаны wheel-only из PyPI.\nЭто проверка на том же ПК с внешним разрешённым Python, не чистая Windows VM.\n'
report+=f"Сравнение с209source: unchanged={len(delta['unchanged'])}, changed={len(delta['changed'])}, added={len(delta['added'])}, removed={len(delta['removed'])}.\n"
(out/'REPORT.txt').write_text(report,encoding='utf-8')
(deliver/'LAD-AI-document-pilot-REPORT.txt').write_text(report,encoding='utf-8')
summary='''**DOC01 — рабочий локальный пилот по документам, 11.11.2026:** по решению владельца проверка/подсказки/баллы/прогресс автоматические, обязательного преподавателя нет; документы любых учебных тем. T01 больше не обязательный gate пилота, но точность модели не объявлена100%. В отдельной копии принятого209source реализованы private upload TXT/PDF/DOCX/PPTX, selected excerpt100–6000, мини-курс/MCQ, durable очередь/receipt, точные цитаты, слепая перепроверка той же моделью, подсказки и автооценка. Source: `C:/Users/ASUS ROG STRIX/.codex/worktrees/lad-document-pilot/git-restore-check`; прежние191/209 и dirty состояние сохранены.91/91 Node,335/335 core,37/37 Django,4/4 новых frontend;47/47 HTTP,3 ready темы16–20с + новая география16,125с с полным циклом баллов. После source_excerpt повтор15documents/4frontend. Стенд5174/API8001/admin8001/admin/; старыйtf11kit5173/8000/8372 работает. SourceZIP244files/245entries SHA996c6e3c1052949b756b755930eb6821c8ba6aa8ef62b0a75550ef71d6d6f76f сREADME/requirements/launcher; модель/базы/секреты исключены. [Отчёт](<C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-08/shag-model-selection/outputs/document-pilot-2026-11-11/REPORT.txt>). ПолныйUI/чистыйПК ещё не приняты;12/12 подсказок заменены нейтральными, полнота урока/цитат ограничена, выбранный исходный текст показан перед тестом. Без новых весов/API/RAG; без merge/commit/push.\n\n'''
road=project/'outputs/AI_ROADMAP.md'
raw=road.read_text(encoding='utf-8')
raw=re.sub(r'\*\*DOC01 — новый scope[^\n]*\n\n',lambda _:summary,raw,count=1)
if '| R-117 |' not in raw:
    raw+='''\n| R-117 | Живые синтетические прогоны DOC01 | Сохранены3 исходныхfailed; исправлены цитаты черезenum, добавлен blindcheck той же модели. Неоднозначный ключ отклоняется, небезопасная подсказка заменяется нейтральной. Финал4темы ready,47HTTP+полныйциклгеографии; качество/персонализация не гарантируются. | DOC01 |\n| R-118 | Упаковка и Windows-проверка | SourceZIP244files,245entriesCRC/SHApassed, requirements wheel-onlyresolved, распакованныйprepare/checkpassed. CopiedPythonAppControl4551 не обходился; используется approvedPythonadapter. ЧистыйПК/полныйUIнепроверены. | DOC01/передача |\n\nПриоритет после DOC01: (1) установка у тестировщика и завершение полного UIсценария; (2) содержательные подсказки и покрытие уроков/цитат на новых документах; (3) прежние U02/V05/U46 и recovery/SDKзадачи по отдельной методике. Обязательная проверка преподавателем в этот пилот не возвращается. Следующий входящий ID: R-119.\n'''
road.write_text(raw,encoding='utf-8')
status=Path(r'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-05/new-chat/outputs/shag-platform/STATUS.md')
raw=status.read_text(encoding='utf-8')
raw=re.sub(r'\*\*DOC01 — новый scope[^\n]*\n\n',lambda _:summary,raw,count=1)
entry='''### LOG-0044 · 11.11.2026 · DOC01, автоматический пилот по документам\n\n- Выполнен новый scope владельца: любые учебные темы, автоматические проверка/подсказки/баллы/прогресс без обязательного преподавателя. Старые gates исторические; точность ИИ100% не заявляется.\n- Изолированнаяworktree на209source, старые191/209/dirtyсохранены. SourceZIP244files/245entries3384932байта, SHA996c6e3c1052949b756b755930eb6821c8ba6aa8ef62b0a75550ef71d6d6f76f, всеentryhashes/CRCpassed. README, pinnedrequirements, setup/start/admin/package. Архив в outputsчата lad-ai-c-users-asus-rog-3.\n-91Node/335core/37Django/4frontend,30concurrentSQLite; послеsource_excerpt15documents/4frontendgreen.47HTTPpassed;history16,219s/bio18,235s/math20,297s;freshgeography16,125s,3/3completed, wrong/correct3→2→3безнакрутки. Предыдущие3failedпрогона/raw сохранены; никакихвыдуманныхбаллов.\n- Все12финальныхhints заменены нейтральными после conservativeverifier; отдельныецитатынеполны, урокинепокрываютвсефакты. Owner-onlyselectedexcerpt показанпередтестом. Слепаяперепроверка тойжемоделью не является независимой.\n- Live на5174/8001/8373 с separateSQLite и темжеcooperative lock/точнымexistinginstance. Старыйtf11kit/общийLMнеостановлены, модельнеперезагружена. Test-onlyrawcapture отключёнпослепроверок. Adminlogin/CSS/privatepathdeny/finalhealthpassed. Coldload/SDKabortнепровереныэтимпрогоном.\n- Browser вход/готовыекарточки/баллы подтверждены; uploadautomationblocked(fileURLs), затем CUA stopped: unable to determine current WindowsURL. ПоследующийUIнеуправлялся; полногоUIproofнет.\n- CopiedPythonDLL AppControl4551: защита неизменна, trustedoriginalPython+append-onlyparsers. SourceZIP распакованвдругойпуть prepare/checkpassed; requirementwheelsresolved.32migrationmetadata drifts byte-identicalbaseline209; новыеStudyfieldsвmigration0006закрыты. НовыйПК/cleanWindowsнепроверены.\n- Полныеотчёты/логи/manifest/source-delta: outputs/document-pilot-2026-11-11. Следующее: testerinstall/UI и качествоhints/lesson/citations; U02/V05/U46/SDK остаютсяоткрыты. Commit/push/merge/reset/clean/выключениеПКнепроизводились.\n\n'''
raw=re.sub(r'### LOG-0044 [\s\S]*?(?=### LOG-0043)',lambda _:entry,raw,count=1)
status.write_text(raw,encoding='utf-8')
print(json.dumps({'baseline':len(old),'release':len(new),'changed':len(delta['changed']),'added':len(delta['added']),'removed':len(delta['removed']),'canonical_updated':True}))
