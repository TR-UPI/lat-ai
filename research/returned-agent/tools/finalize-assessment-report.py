from pathlib import Path
from datetime import datetime
import json

root = Path(__file__).resolve().parents[1]
out = root / 'outputs/assessment-fix-2026-11-11'
read = lambda name: json.loads((out / name).read_text(encoding='utf-8-sig'))
runs = ['baseline', 'baseline-repeat', 'candidate', 'candidate-repeat', 'candidate2', 'candidate2-repeat', 'candidate3', 'candidate3-repeat', 'candidate4', 'candidate4-repeat']
comparison = {name: read(name + '/summary.json') for name in runs}
comparison['http'] = read('http/summary.json')
comparison['limitations'] = ['Author development cases used during tuning, not independent holdout.', 'Historical undergrade is intermittent; new baseline also accepted original answer.', 'No teacher acceptance or production quality guarantee.']
assert comparison['candidate4']['matched'] == 48
assert comparison['candidate4-repeat']['matched'] == 10
assert comparison['http']['matched'] == comparison['http']['cases'] == 8
assert all(value['exit_code'] == 0 for value in read('checks/results.json').values())
health = read('health-final.json')
assert health['tutor']['ready'] and not health['tutor']['quarantined'] and not health['tutor']['busy']
(out / 'comparison.json').write_text(json.dumps(comparison, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
report = '''LAT AI — название и улучшение AI-оценивания
Дата: 11.11.2026, Asia/Qyzylorda

РЕЗУЛЬТАТ
Актуальные надписи проекта и демонстрационный курс переименованы в LAT AI.
Принята узкая правка AI-оценщика: смысл вывода без обязательных кавычек/слова
print, область отрицания, независимость критериев и прямые подтверждающие
цитаты. Взаимоисключающие утверждения считаются противоречием. Для assess
temperature=0; у explain осталось0.2. Это снижает случайность, но не обещает
битовую воспроизводимость или безошибочную оценку любого ответа.
Сегментация, число критериев и формула балла не менялись. Правильный ответ
не распознаётся по готовой строке и не получает принудительный балл.

СХЕМА И ГРАНИЦЫ
Схема ответа local-assessment-v1 сохранена. assessment_revision=
2026-11-11-evidence-v1 входит в fingerprint AI-журнала; конфликт версии
не вызывает новую генерацию и не переписывает завершённый результат.
Функциональность backend/frontend не менялась: проверены100 файлов,
исключения — две явно запрошенные брендовые надписи (scope-check.json).
Backend хранение ревизии/восстановление после crash — задача его разработчика.
Границы ответственности записаны в AGENTS и TEAM_OWNERSHIP_AND_RECOVERY.md.

ПРОИСХОЖДЕНИЕ ОШИБКИ И ОГРАНИЧЕНИЯ
Старый raw этого ПК: ../local-pc-limits-2026-11-11/benchmark/grade-condition.json.
Правильное объяснение if/else получило criterion_3=-1, т.е.2/3.
На новом baseline исходный ответ уже проходит, включая5 повторов: ошибка
плавающая, детерминированного RED→GREEN для исходной фразы здесь нет.
Текущий результат — измеренное улучшение dev-набора и успешный целевой smoke,
а не доказательство полного устранения недооценки на любых формулировках.
Новые24 случая зафиксированы до настройки; с прежними24 получился dev48.
Он использован при выборе кандидата, поэтому не является независимым holdout.
Преподаватель не проводил приёмку; T01/S02 и общий допуск не закрыты.

СРАВНЕНИЕ НА ОДНОЙ УСТАНОВЛЕННОЙ QWEN3.5-9B
Baseline:46/48, ошибки L1.types.1-6 и N11 (противоречия); повторы10/10.
Кандидат1 (дополнительные части цитат):46/48, новые недооценки N05/N22.
Кандидат2 (узкий смысловой промпт):45/48, новая ошибка N15 и старые противоречия.
Кандидат3 (+temperature=0):46/48, L1.types.1-6 и N15; повторы10/10.
Кандидат4 (+прямые цитаты/независимость/взаимоисключение):48/48; повторы10/10.
Принят только кандидат4. Все raw, длительности, исходники и recovery-события
отклонённых вариантов сохранены. Их модели выгружены с доказательством.
Максимум прямого запроса принятого dev-прогона:5.000с; повторов:4.534с.

ПРОВЕРКИ
55/55 Node integration,19/19 Django,335/335 исходный core baseline.
3 схемы,2 request/6 response examples,20 upstream hashes с local overrides.
Новые технические тесты: отдельная температура assess/explain в двух
протоколах; конфликт ревизии сохраняет receipt без повторной генерации.
git diff --check прошёл. Логи и exit codes — checks/.

ЖИВОЙ ПРОТОТИП:8/8 HTTP
Изолированный синтетический аккаунт, реальные JWT→Django→worker→модель.
Исходный правильный ответ:100%, повтор:100%, перефразировка if выводит да:100%.
Настоящее отрицание вывода:66.67%; только вывод:33.33%; ветка не названа:66.67%.
Противоречие:0%; инъекция инструкций:0%. Все попытки auto_checked.
Raw результатов и timings — http/; никаких оценок вручную не подставлялось.
Существующие попытки и аккаунты сохранены. Перед переименованием курса
база и mapping скопированы в приватную .runtime/i02/backups/lat-brand-20261111-043134.

ЛОКАЛЬНЫЙ ЗАПУСК
http://127.0.0.1:5173/#/courses — оставлен включённым.
Работает LAT AI worker с собственным lat-owned экземпляром, ready=true,
busy=false, quarantine=false (health-final.json). Общая LM Studio сохранена.
Профиль только этого ПК:60с модель+очередь,70с Django,80с браузер.
Общие лимиты проекта не повышены. Runtime создан заново из обновлённого кода;
startup log — restart.log; подробные сервисные логи — приватная .runtime/i02.

БРЕНД И СОВМЕСТИМОСТЬ
Исторические архивы/оригиналы не переименовывались и не переписывались.
LAD_AI_*, X-LAD-IPC, старый тестовый логин и имена БД оставлены совместимыми:
их миграция затронет интеграцию других разработчиков, это не надписи продукта.
Исходное dirty tree сохранено. source-before/ и source-before.json — снимок
до работы; source-changes.json и this-work.patch — изменения именно этого этапа.
Коммит, push, публикация и сообщения команде не выполнялись.

ДАЛЬШЕ ПО ROADMAP
Независимая проверка качества и T01/S02; в AI-части — дополнительные ошибки
на новых ответах, а не настройка по одному удачному примеру. Для crash
reconciliation подготовлены границы работ и6 приёмочных сценариев в
lat-ai/docs/ai/TEAM_OWNERSHIP_AND_RECOVERY.md. Backend/frontend реализация
остаётся у их разработчиков. Эти пункты не объявлены выполненными.

ВОСПРОИЗВЕДЕНИЕ И ЛОГИ
lat-ai/docs/ai/ASSESSMENT_EVALUATION.md — процедура и ограничения.
lat-ai/integration/ai/eval/ — dev48 и repeat10.
lat-ai/tools/evaluate-assessment.mjs — живой измерительный сценарий.
WORKLOG.txt — ход работы, включая неудачи; comparison.json — сводка чисел.
Отчёты и логи обязательны после каждого этапа, требование записано в AGENTS.
'''
(out / 'REPORT.txt').write_text(report, encoding='utf-8')
section = '''## LAT AI: название и AI-оценивание · 11.11.2026 · Проверено на локальном стенде

Название в актуальных надписях и демонстрационном курсе — LAT AI.
Работаем только над ИИ-частью; backend/frontend ведут другие разработчики.
Принят кандидат4: уточнены смысл вывода, область отрицания, независимость
критериев и подтверждающие цитаты. Assess temperature=0, explain остаётся0.2.
Сегментация и формула балла сохранены; схема v1 и совместимые IPC-идентификаторы
сохранены. Ревизия evidence-v1 входит в fingerprint AI-журнала.

Результаты:48/48 dev (baseline46/48),10/10 повторов,8/8 реальных HTTP-проверок.
Исходный правильный ответ и перефразировка получили100%; неполные ответы —
частичный балл, противоречие и инъекция —0%. 55/55 Node,19/19 Django,335/335 core
и проверки контрактов прошли. Сверка100 frontend/backend файлов: только2
брендовые надписи. Отклонённые кандидаты и их логи сохранены.

Ограничение: исходная ошибка плавающая и новый baseline уже принимал эту фразу.
Dev48 использован при настройке, это не независимый holdout и не преподавательский
допуск. T01/S02 остаются открытыми; не объявляем проблему любой недооценки закрытой.
Следующая совместная задача — crash reconciliation: разделение ответственности
и6 сценариев подготовлены в docs/ai/TEAM_OWNERSHIP_AND_RECOVERY.md, реализация не выполнена.

Стенд и модель включены, idle без карантина. Пределы60/70/80с остались только
в профиле этого ПК; общие лимиты не повышались. История попыток сохранена.
[Отчёт](<E:/Startup Tau/outputs/assessment-fix-2026-11-11/REPORT.txt>) ·
[Лог работы](<E:/Startup Tau/outputs/assessment-fix-2026-11-11/WORKLOG.txt>) ·
[Сравнение](<E:/Startup Tau/outputs/assessment-fix-2026-11-11/comparison.json>).

'''
for name in ['AI_ROADMAP.md', 'STATUS.md']:
    path = root / 'outputs' / name
    text = path.read_text(encoding='utf-8')
    assert text.startswith('## LAT AI: название и AI-оценивание')
    next_section = text.index('## Лимиты только для этого ПК')
    path.write_text(section + text[next_section:], encoding='utf-8', newline='\n')
entry = root / 'START_HERE.md'
text = entry.read_text(encoding='utf-8')
start = text.index('**Обновление 11 ноября:')
end = text.index('Передача от 11 ноября')
replacement = '''**Обновление 11 ноября: LAT AI и правка оценивания.** Работаем только над ИИ-частью; backend/frontend ведут другие разработчики. Название актуальных надписей и курса обновлено. Принятый оценщик прошёл48/48 авторских dev-примеров,10/10 повторов и8/8 HTTP-проверок; исходный правильный ответ получает100%. Это не независимая приёмка: T01/S02 открыты. [Отчёт и ограничения](<E:/Startup Tau/outputs/assessment-fix-2026-11-11/REPORT.txt>) · [Воспроизведение](<E:/Startup Tau/lat-ai/docs/ai/ASSESSMENT_EVALUATION.md>).

Прототип и модель включены. Профиль только этого ПК:60с модель/очередь,70с Django,80с браузер; общие лимиты не повышены. Запуск: [START-LAT-AI-THIS-PC.cmd](<E:/Startup Tau/START-LAT-AI-THIS-PC.cmd>) или `tools/start-lat-ai.ps1 -EnableModel`. [Инструкция и откат](<E:/Startup Tau/work/local-pc/README.md>). Ниже сохранена исходная точка приёма передачи; прежние статусы относятся к тому этапу.

'''
entry.write_text(text[:start]+replacement+text[end:], encoding='utf-8', newline='\n')
with (out / 'WORKLOG.txt').open('a', encoding='utf-8') as file:
    file.write('\n14. Общие проверки:55 Node,19 Django,335 baseline, contracts — всё прошло. Стенд пересобран из принятого исходника с прежним локальным профилем60/70/80с; запущен.\n15. HTTP8/8: исходный правильный, перефразировка и повтор100%; отрицание66.67%; только вывод33.33%; без ветки66.67%; противоречие/инъекция0%. Финальный health:ready, idle, без карантина.\n16. Подготовлены REPORT, comparison, source-changes/patch, scope-check; актуализированы STATUS, roadmap, START_HERE и память AGENTS. Граница только AI и обязательность отчётов/логов сохранены. Время завершения: '+datetime.now().astimezone().isoformat()+'\n')
print('Report, comparison, worklog, roadmap and entry point updated.')
