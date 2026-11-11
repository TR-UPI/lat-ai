from pathlib import Path
import json
root=Path(__file__).resolve().parents[1];base=root/'outputs/assessment-v3-2026-11-11';old=root/'outputs/assessment-evidence-v2-2026-11-11'
oracle={c['id']:c['required_fragments'] for c in json.loads((old/'regression-evidence-oracle.json').read_text(encoding='utf-8'))['cases']}
cases=json.loads((base/'regression128.json').read_text(encoding='utf-8'))
for c in cases:
 if 'evidence_anchors' not in c:c['evidence_anchors']=oracle[c['id']]
(base/'regression128-with-evidence.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8')
probe=json.loads((base/'probe16.json').read_text(encoding='utf-8'));ids={c['id'] for c in probe}
for name,items in [('probe16-with-evidence',[c for c in cases if c['id'] in ids]),('remaining112',[c for c in cases if c['id'] not in ids])]:
 (base/(name+'.json')).write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
sentinels=['N05','U15','U02','U26','H18','H14','N18','H30']
for session in range(1,3):
 rows=[]
 for repeat in range(1,4):
  # Rotate the task order; same source text, distinct request identity.
  order=sentinels[repeat-1:]+sentinels[:repeat-1]
  for key in order:
   c=next(c for c in cases if c['id']==key)
   rows.append({**c,'id':f'S{session}R{repeat}-{key}','source_id':key,'repeat':repeat,'session':session})
 (base/f'stability-session{session}.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8')
(base/'ACCEPTANCE.txt').write_text('''План до результатов нового набора:
1. Исправить полные цитаты N05/U15 и положительные U02/U26/H18.
2. Не внедрять кандидата с новыми ошибочными выданными оценками относительно
   известных меток; отдельно считать отказы и смысловое покрытие цитат.
3. Цель на known128: >=95% верных оценок с достаточными цитатами,0 неверных.
4. Стабильность:8 заранее выбранных ответов ×3 повтора ×2 загрузки=48.
   Не заменять плохой повтор хорошим; сравнить checks, отказ и цитаты отдельно.
5. Заморозить код до holdout32. Цель:0 неверных оценок/неполных положительных
   цитат и >=90% выдачи верных оценок; авторские метки не означают допуск учителя.
6. При провале не подстраивать код под тот же32 и называть его новым.
7. Затем AI-only read-only receipt recovery и его тесты; остановиться перед
   T01/S02/D01, где нужны преподаватель/внешние люди/явный выбор допуска.
''',encoding='utf-8')
print('Prepared128 with evidence, diagnostic16, remaining112, stability48')
