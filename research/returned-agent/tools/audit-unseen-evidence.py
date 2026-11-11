"""Explicit author audit of every selected quote; separate from frozen grade labels."""
from pathlib import Path
from collections import Counter
import json

out = Path(__file__).resolve().parents[1]/'outputs/assessment-unseen-2026-11-11'
rows = json.loads((out/'case-results.json').read_text(encoding='utf-8'))
# F full support, P partial support, N irrelevant to criterion, X contradicted
# by another claim in the answer, - no positive model criterion/no quote.
labels = '''FNN -NF FNN FNN F-- FF- F-N --F --- --- --- FFF
FFF FFF PNN FFF P-- -P- F-F FF- --- FFX --- FFF
FFF FF- FFF FFF F-- -P- F-F FF- --- FF- --- FFF
FFF FFF FNN FFF F-- -F- F-F -FN --- FFX --- FFF'''.split()
notes = {
 'U01':'Цитата о двух текстах поддерживает типы, но не описывает склейку или вывод 32.',
 'U02':'Критерий операции подтверждён цитатой только о результате; утверждение о склейке находится в другом фрагменте.',
 'U03':'«Операнды строковые» не подтверждает ни конкатенацию, ни вывод 32.',
 'U04':'Английская цитата о типах не подтверждает операцию и результат.',
 'U07':'Цитата о типе str не содержит утверждения, что выводится 32.',
 'U15':'«x: 2» содержит только часть первого критерия, не выбор веток и не вывод.',
 'U17':'Выбрано только значение x; утверждение об истинности сравнения находится в следующем фрагменте.',
 'U18':'Цитата говорит только о выполнении if; пропуск else находится в следующем фрагменте.',
 'U22':'Цитата буквально утверждает вывод да, но другая часть ответа прямо отрицает этот же вывод.',
 'U30':'Цитата называет правую границу, но не её исключение; исключение сказано следующим фрагментом.',
 'U39':'Инициализация не является трассировкой сумм и не объясняет однократный print после цикла. Трассировка разделена между несколькими фрагментами.',
 'U44':'Третий критерий подтверждён цитатой о суммах; расположение/кратность print названы другим фрагментом.',
 'U46':'Цитата про один print после цикла противоречит следующему утверждению о том же print внутри цикла три раза.'
}
assert len(rows)==len(labels)==48
audit=[]; counts=Counter()
for row,label in zip(rows,labels):
    assert len(label)==3
    for i,support in enumerate(label):
        assert (support!='-') == row['actual'][i]
        if support!='-':
            assert row['evidence'][i] and row['evidence'][i] in row['answer']
            counts[support]+=1
    audit.append({'id':row['id'],'support':list(label),'checks_match':row['match'],'selected_evidence':row['evidence'],'note':notes.get(row['id'],'Выбранные положительные цитаты подтверждают критерии; при отсутствии положительных критериев цитаты не требуются.')})
summary={'method':'Author review after inference, not independent teacher review. F means the quote supports the entire criterion in context; P only part; N no relevant support; X a quoted positive claim is contradicted elsewhere. All selected quotes are literal substrings. Grade labels remain unchanged.', 'audited_answers':48,'positive_criteria':sum(counts.values()),'support_counts':dict(counts),'answers_with_irrelevant_or_partial_quotes':sum(any(x in r['support'] for x in ['N','P']) for r in audit),'answers_with_contradicted_quotes':sum('X' in r['support'] for r in audit),'answers_with_any_evidence_problem':sum(any(x in r['support'] for x in ['N','P','X']) for r in audit),'exact_checks_and_all_positive_quotes_supported':sum(r['checks_match'] and all(x in ['F','-'] for x in r['support']) for r in audit)}
(out/'evidence-audit.json').write_text(json.dumps({'summary':summary,'cases':audit},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
