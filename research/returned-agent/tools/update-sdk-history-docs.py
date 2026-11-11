"""Update current navigation only after completed frozen scan and stand restoration."""
from pathlib import Path
import json
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/sdk-fix-and-history-scan-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
d=read(OUT/'known128-details.json');a=read(OUT/'known128-analysis.json');p=a['primary']
assert read(OUT/'scan-process-proof.json')['exit_code']==0
assert (OUT/'stand-restored-status.json').is_file()
marker='## SDK и скан 128 × 3 завершены · 11.11.2026'
section=f'''{marker}

**Текущее состояние.** SDK helper проверен на двух живых загрузках: после dispose
и обоих прежних deadline процесс завершился exit 0. Исторический сбой сохранён.
Замороженный скан завершён: 128 известных текстов, 3 порядка/3 свежих экземпляра,
384 оценивания и 768 terminal POST; без повторов unknown. Первичная серия №1:
**{p['correct']} верных, {p['wrong']} неверных, {p['abstentions']} отказов**. Итоговый вектор/отказ менялся у
**{d['varying_final_outcomes']}/128** текстов. Это 3 load/order кластера, не 384 независимых работы.
Порядок и экземпляр смешаны; никакой популяционной точности этим не доказано.
В третьей серии — **107 верных, 2 неверных, 19 отказов**: U02 занижен, U46 получил
неверный полный балл после пропуска противоречия. Автоматически выпускать полный
балл по согласию двух проходов нельзя считать безопасным. U02 также показал
изменение verifier при checkpoints32; прежнее постоянство было ограничено серией.

Промпты/рубрики/gate и все 209 файлов проекта сохраняются. Обычный стенд восстановлен;
локальные лимиты 60/70/80 с прежние. Добавлен отдельный offline-прототип сигналов для
человека: не меняет баллы/worker, не валидирован на реальных работах. Подготовка пилота
проверяет отдельного adjudicator и нормализованные IDs разметчиков. 35 технических
тестов (4 SDK + 31 prototype/pilot) прошли; это не педагогическая приёмка.

Следующие AI-шаги: независимый ручной разбор цитат/меток (включая H23), реальный
теневой пилот и проверка полезности сигналов. Координатор «разраб 1 П», сбор запланирован
на 12.11.2026; реальные данные и решения людей ещё отсутствуют. T01/S02/D01/D02 открыты.
Не менять промпты, не повторять известные тексты для заявления нового holdout.
Отправка Claude поручена владельцем; фактический статус и ответы фиксируются отдельно,
подготовленные сообщения не считаются доставленными: outputs/claude-review-2026-11-11.

[Текущий отчёт](<E:/Startup Tau/outputs/sdk-fix-and-history-scan-2026-11-11/REPORT.txt>) ·
[Пилот и ручной разбор ZIP](<E:/Startup Tau/outputs/sdk-fix-and-history-scan-2026-11-11/LAT-AI-PILOT-AND-HISTORY-REVIEW-2026-11-11.zip>) ·
[Прототип сигналов](<E:/Startup Tau/outputs/review-signals-prototype-2026-11-11/REPORT.txt>).

Ниже — история прежних этапов. Прежнее «скан не запущен» относится к моменту SDK-сбоя;
его заменяет текущая запись выполнения, а старые frozen-артефакты остаются неизменными.

'''
for name in ['START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md']:
    path=ROOT/name;old=path.read_text(encoding='utf-8-sig');assert marker not in old,name
    if old.startswith('# LAT AI'):
        first,rest=old.split('\n',1);new=first+'\n\n'+section+rest.lstrip('\n')
    else:new=section+old
    path.write_text(new,encoding='utf-8')
path=ROOT/'AGENTS.md';old=path.read_text(encoding='utf-8-sig')
note=f'''\n- Актуальный этап SDK/history scan 11.11: SDK live fix exit0 после старых deadline; 128 известных текстов ×3 порядка/3 loads полностью выполнены (384 assessments/768 terminal POST). Первичная серия1: {p['correct']}correct/{p['wrong']}wrong/{p['abstentions']}refusal; {d['varying_final_outcomes']}/128 разных итогов между сериями. Не unseen, не 384 независимых кейса, order и instance смешаны. Source209/prompts/backend/frontend неизменны, stand восстановлен,60/70/80 прежние. Отдельный advisory-only review-signals prototype не меняет grade/gate и ещё не проверен на real_student. prepare-shadow-pilot требует третьего adjudicator ID;31tests+4SDK passed. Отчёты/ZIP/backup:outputs/sdk-fix-and-history-scan-2026-11-11;prototype:outputs/review-signals-prototype-2026-11-11. Владелец явно разрешил отправлять отчёты этапов в Claude desktop; проверять реальную доставку и ответ, сохранять разбор замечаний; статус outputs/claude-review-2026-11-11/DELIVERY-STATUS.txt. Не выдавать подготовленные тексты за рецензию. Реальный пилот/люди/T01/S02/D01/D02 открыты, координатор разраб 1 П, старт12.11.2026. No commit/push.\n'''
assert 'Актуальный этап SDK/history scan 11.11' not in old
path.write_text(old.rstrip()+'\n'+note,encoding='utf-8')
print('Updated current navigation and AGENTS; historical frozen reports preserved.')
