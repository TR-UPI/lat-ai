from pathlib import Path
import json
root=Path(__file__).resolve().parents[1];base=root/'outputs/assessment-evidence-v2-2026-11-11'
load=lambda p:json.loads((base/p).read_text(encoding='utf-8-sig'))
http=load('worker-http/summary.json');checks=load('checks/results.json');audit=load('source-audit.json')
assert http['cases']==5 and http['accepted']==5 and not http['health']['tutor']['quarantined']
assert all(r['exit_code']==0 for r in checks.values())
report=base/'REPORT.txt';text=report.read_text(encoding='utf-8')
text=text.replace('Финальные проверки/статус будут дополнены после запуска локального worker.\nНа изолированном H ранее прошли67/67 Node и проверки контрактов/20 pin-хешей.',f'''На принятом исходнике прошли67/67 Node integration,19/19 Django и335/335
тестов архивного baseline core (последние не являются тестом новых промптов).
Проверки3 схем и20 pin-хешей прошли. Отдельно H тестирует вторую стадию,
расхождение критериев, обрезку, отмену и карантин неизвестного POST.
Локальный стенд пересобран и включён с тем же профилем60/70/80с.
Private worker HTTP:5/5 проверок ожидаемого поведения;{http['correct']} корректных оценок,
{http['abstained']} отказов без checks/балла. Первые2 запроса выполнялись одновременно,
проверяя прежнюю очередь; максимальная длительность{http['max_ms']/1000:.2f}с с ожиданием.
Каждая полученная terminal-квитанция повторно прочитана и совпала побайтово
по JSON-значению. Неизвестные POST не повторялись. Health:ready,idle,
без карантина. Созданы только синтетические записи AI-журнала; через Django
не создавались аккаунты/попытки. Стенд доступен на http://127.0.0.1:5173/#/courses.
Файлы:checks/results.json,worker-http/summary.json,restart-local-stand.log.''')
report.write_text(text,encoding='utf-8')
section='''## Цитаты и противоречия: evidence-v2h · 11.11.2026 · Проверено на этом ПК

В AI-модуль принят оценщик с непрерывными цитатами, конкретным counter-фрагментом
и вторым проходом на исходном ответе. При расхождении критериев возвращается
unavailable без балла. Backend/frontend-код и общий контракт не изменены.

Новый замороженный32:26 верных оценок с достаточными цитатами,6 отказов,
0 ошибочных выданных оценок относительно авторских меток. Покрытие81,25%,
это НЕ32/32 успешных оценок. В прежней v1-стадии на тех же ответах:26 верных,
6 ошибочных,15/32 checks+цитаты. Найдены8/8 заранее указанных противоречащих
фрагментов;55 положительных цитат H прошли проверку опорных фраз.
Предварительно отмеченный спорный H23: без него26 верных и5 отказов/31.
Код и метки не изменялись после просмотра; этот32 теперь известный набор.

Известный regression96: H replay85 верных,11 отказов,0 ошибочных,83 совместно
с цитатами. Это replay сохранённых raw, не live H. G без второго прохода имел
7 ошибок на96, поэтому его32/32 на новых ответах не повод отключать проверку.
Открыты2 частичные цитаты N05/U15 и отказы на правильных перефразировках,
включая H18. Совпадение двух инструкций одной модели не гарантирует истину.
T01/S02 открыты; следующий этап — снизить отказы/ошибки цитат и проверить
на ещё одном новом замороженном наборе, затем независимая разметка учителя.

Проверки67 Node,19 Django,335 baseline core и contracts прошли. Private AI
HTTP5/5 ожидаемых исходов, очередь двух клиентов и replay квитанций проверены.
Все101 backend/frontend/index файла сохранены. Стенд включён,ready/idle,
без карантина; локальные60/70/80с неизменны, общие8/9/10с не повышены.
H32:медиана10,98с,максимум16,51с; перенос бюджета на другие ПК не проверен.
[Отчёт](<E:/Startup Tau/outputs/assessment-evidence-v2-2026-11-11/REPORT.txt>) ·
[Лог](<E:/Startup Tau/outputs/assessment-evidence-v2-2026-11-11/WORKLOG.txt>) ·
[Следующие AI-задачи](<E:/Startup Tau/outputs/assessment-evidence-v2-2026-11-11/AI_FINDINGS.txt>).

'''
for name in ['outputs/AI_ROADMAP.md','outputs/STATUS.md']:
 p=root/name;old=p.read_text(encoding='utf-8-sig');marker='## Новые ответы: оценивание evidence-v1'
 assert old.startswith('## В работе:') and marker in old
 p.write_text(section+old[old.index(marker):],encoding='utf-8')
p=root/'START_HERE.md';old=p.read_text(encoding='utf-8-sig');old=old.replace('**Последняя проверка 11 ноября: новые ответы — 44/48.**','**Предыдущая проверка 11 ноября: новые ответы — 44/48.**',1)
intro='''**Последний этап 11 ноября: исправлены диапазоны цитат и добавлена проверка противоречий.** Новый замороженный набор:26 верных оценок с достаточными цитатами,6 отказов,0 ошибочных выданных оценок из32 по авторской разметке. Отказ не считается верной оценкой. AI evidence-v2h установлен на локальный стенд; backend/frontend-код не менялся. Все технические проверки прошли. Остались частичные цитаты на известных случаях и отказы на правильных перефразировках; T01/S02 открыты. [Отчёт](<E:/Startup Tau/outputs/assessment-evidence-v2-2026-11-11/REPORT.txt>) · [Лог](<E:/Startup Tau/outputs/assessment-evidence-v2-2026-11-11/WORKLOG.txt>). Ниже сохранена история предыдущих этапов.

'''
assert old.startswith('# LAT AI — начало работы\n\n')
p.write_text(old.replace('# LAT AI — начало работы\n\n','# LAT AI — начало работы\n\n'+intro,1),encoding='utf-8')
p=root/'AGENTS.md';old=p.read_text(encoding='utf-8-sig').replace('- Последний этап 11.11: frozen unseen48','- Предыдущий этап 11.11: frozen unseen48')
p.write_text(old+'''\n- Последний этап 11.11: AI evidence-v2h-verified — диапазоны исходных цитат, counter-ID и второй замороженный evidence-v1 проход. Совпадение всех3 критериев обязательно; расхождение даёт unavailable без балла. Новый frozen32:26 верных с достаточными цитатами,6 отказов,0 неверных выданных оценок; не32/32. Все8 counter найдены,55 положительных цитат покрывают заранее заданные фразы. Известный96: H replay85 верных,11 отказов,0 неверных,83 joint (НЕ live H); N05/U15 неполные цитаты остаются. G сам по себе89/96 и не применяется. H18 правильный ответ получает отказ; снижение недооценки ещё не завершено. Код/метки заморожены до inference, после не менялись; набор32 теперь известен, следующая настройка требует нового.67 Node+19 Django+335 baseline core,contracts,HTTP5/5 прошли.101 backend/frontend/index файла неизменны. Локальный стенд включён с прежним60/70/80с; H live медиана10,98с,max16,51с. Общие лимиты8/9/10с не менять под этот ПК; другой аппаратный бюджет не проверен. Отчёт/логи:outputs/assessment-evidence-v2-2026-11-11. T01/S02 открыты; две инструкции одной модели не независимые судьи.\n''',encoding='utf-8')
with (base/'AI_FINDINGS.txt').open('a',encoding='utf-8') as f:f.write('''\nИтог нового frozen32: H26 верных с цитатами,6 отказов,0 неверных выданных.
Правильный H18 стал отказом,5 других отказов связаны с противоречиями.
Первый проход нашёл8/8 counter; H55/55 положительных цитат покрывают якоря.
G32/32 здесь не отменяет7 ошибок на известных96; gate не отключён.
Следующий набор должен быть новым: этот32 после текущей проверки уже известен.
Подробная методика, первичные и sensitivity-метрики — REPORT.txt.
''')
with (base/'WORKLOG.txt').open('a',encoding='utf-8') as f:f.write(f'''\n11. Promoted source checks:67/67 Node,19/19 Django,335/335 archived baseline core;3 schemas/20 pins pass. Source audit:197→202 files,10 AI/docs differences,101 protected files unchanged, frozen candidate/holdout SHA unchanged. Patch saved.
12. Local stand rebuilt/restarted using existing60/70/80s profile, existing data retained. Private-worker smoke5/5:{http['correct']} correct,{http['abstained']} unavailable without grade; first2 concurrent; each terminal receipt replayed unchanged. Max{http['max_ms']/1000:.2f}s with queue. No backend accounts/attempts created. Final health ready/idle, no quarantine. Logs in worker-http/ and restart-local-stand.log.
13. Report, next AI findings, START_HERE, canonical STATUS/roadmap and AGENTS updated. H32 reviewed manually against per-criterion evidence; mixed-fact sentence limitation noted. No tuning after holdout, no external messages, no commit/push. T01/S02 remain open.
''')
print(json.dumps({'report':str(report),'http_passed':http['accepted'],'docs_updated':4,'protected_files':audit['protected_backend_frontend_files']},ensure_ascii=False))
