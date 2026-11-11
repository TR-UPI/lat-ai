"""Post-hoc descriptive clarification requested in Claude review; no inference."""
from pathlib import Path
from collections import Counter
import json, hashlib
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/claude-reviewed-ai-continuation-2026-11-11'
OLD=ROOT/'outputs/u02-runtime-controls-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
d=read(ROOT/'outputs/sdk-fix-and-history-scan-2026-11-11/known128-details.json')
plan=read(OLD/'known128-plan.json')
for n in (1,2,3):
    folder=OLD/f'known128-live-{n}'
    summary=read(folder/'summary.json')
    for name,digest in summary['result_sha256'].items():assert sha(folder/name)==digest
lines=['LAT AI — пояснение после рецензии Claude, 11.11.2026',
       'POST-HOC описательный отчёт по уже сохранённым данным; новых запросов нет.',
       'Исходные протоколы, ответы, метки и первичная серия1 не менялись.',
       'Ошибок среди выданных по сериям: 0/109, 0/109, 2/109. Выдано109/128 в каждой.',
       'Это известные авторские тексты, 3 кластера порядок+экземпляр+время.',
       '2/128 хотя бы раз ошибочных — объединение в этих трёх повторах, не риск на учениках.',
       '7/128 меняли итог; отсутствие изменения у остальных не доказывает инвариантность.',
       '', 'СЕМЬ МЕНЯВШИХСЯ ТЕКСТОВ: исход/вектор (T/F), позиция в серии']
vec=lambda v:'отказ' if v is None else ''.join('T' if x else 'F' for x in v)
for c in d['per_case']:
    if not c['different_outcomes']:continue
    positions=[plan['execution_orders'][n].index(c['id'])+1 for n in range(3)]
    lines.append(c['id']+' | '+c['task']+' | '+' | '.join(f'{c["outcomes"][n]}/{vec(c["actual_by_series"][n])}, pos{positions[n]}' for n in range(3)))
lines+=['','ЗАДАЧИ, а не префиксы наборов L/N/U/H:','задача | n | меняли итог | серия1 correct/refusal/under/over | серия2 | серия3']
for task in sorted(d['by_task']):
    cases=[c for c in d['per_case'] if c['task']==task]
    totals=[Counter(c['outcomes'][n] for c in cases) for n in range(3)]
    lines.append(task+' | '+str(len(cases))+' | '+str(sum(c['different_outcomes'] for c in cases))+' | '+' | '.join('/'.join(str(t[x]) for x in ['correct','refusal','undergrade','overgrade']) for t in totals))
lines+=['','СМЕНА СОСТАВА ОТКАЗОВ, серия1 -> серия3:']
for c in d['per_case']:
    if (c['actual_by_series'][0] is None)!=(c['actual_by_series'][2] is None):
        lines.append(c['id']+': '+c['outcomes'][0]+' -> '+c['outcomes'][2])
h=next(c for c in d['per_case'] if c['id']=='H23');assert h['actual_by_series']==[None,None,None]
lines+=['','H23: отказ3/3, поэтому любая другая эталонная метка без исключения случая не',
        'меняет correct/wrong/refusal. Исключение post-hoc дало бы n127/refusal18,',
        'выдано109 и ошибки0/0/2; это только чувствительность, не новый primary.',
        'V05: весь V01–V32 отсутствует в каноническом regression128-with-evidence.json,',
        'из которого prepare-known128-history-scan.mjs заранее заморозил план. Это',
        'граница заданного скана128, не исключение отдельной ошибки после результатов.',
        'Корпус не охватывает все160 уже известные тексты. V05 остаётся открытым.',
        '', 'U46: сохранённые raw обоих проходов имеют finish_reason=stop и корректный JSON.']
for n in (1,2,3):
    r=read(OLD/f'known128-live-{n}'/f'R{n}-U46.json')
    for name in ['candidate','verification']:
        p=r['raw'][name];parsed=json.loads(p['answer'])
        lines.append(f'Серия{n} {name}: finish={p["finish_reason"]}, output_tokens={p["stats"]["total_output_tokens"]}, JSON={json.dumps(parsed,ensure_ascii=False)}')
lines+=['Терминальные HTTP200 и явное counter:null в серии3 сохранены. Признаков',
        'обрезания length/ошибки JSON в этих данных нет; поле не было придумано парсером.',
        'Полные HTTP-тела не сохранены: побайтовый повторный разбор всей оболочки невозможен.',
        'Нельзя из одного поля counter:null установить внутреннюю причину ошибки модели.',
        '', 'ПАРАМЕТРЫ И ТЕРМИНЫ',
        'Frozen LocalModel structured request: temperature0, top_p0.8, max_tokens192,',
        'reasoning_effort=none, stream=false. Seed генерации не передавался/не фиксировался.',
        'order_seed фиксирует перестановку случаев, а не генерацию модели.',
        'Медиана10.7694с/max16.4514с — на оценивание из двух последовательных POST,',
        'последовательный скан без конкуренции; не нагрузочный тест класса.',
        'Raw11/14 — разные JSON, не метрика векторов/семантических цитат.',
        'Термин joint в прежних отчётах означает «балл И цитаты верны», а не',
        'таблицу согласия proposal/verifier. Его отсутствие не отменяет записанные',
        'расхождения review_disagreement; независимость проходов не установлена.',
        'Никаких причинных утверждений о порядке/кэше и новых доверительных интервалов.',
        '', 'SDK: поздний abort не воспроизвёлся в двух успешных загрузках с helper v1;',
        'процесс удержан за обеими прежними границами и завершился exit0. Это отдельный',
        'smoke, скан128 использовал CLI. Helper v2:6 tests, без новой live проверки.',
        'Реальный timeout/SIGINT/поздний provisioning не проверены; правило карантина отдельно.']
with (OUT/'SCAN_REVIEW_ADDENDUM.txt').open('x',encoding='utf-8') as f:f.write('\n'.join(lines)+'\n')
print('\n'.join(lines[:28]))
