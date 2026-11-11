from pathlib import Path
import json,collections,statistics,itertools
work=Path(__file__).resolve().parent
out=work.parents[1]/'outputs/f01-2026-11-10'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
raw=read(out/'independent-ratings.json')
mapping={r['review_id']:r for r in read(out/'map-private.json')}
responses={r['review_id']:r for r in read(out/'responses.json')}
final={r['review_id']:dict(r) for r in raw}
decisions=[]
def amend(rid,changes,reason):
 before={k:final[rid][k] for k in changes}
 assert any(before[k]!=v for k,v in changes.items())
 decisions.append({'review_id':rid,**mapping[rid],'before':before,'after':changes,'reason':reason})
 final[rid].update(changes)
 final[rid]['adjudication_reason']=reason

# Specific decisions after direct reading of all 66 accuracy issues.
for rid in ['F3ce3e7bf57a9169','F4f71b2f3fe6cac1','F9abf0152140cb80']:
 amend(rid,{'A':0},'Прямое утверждение «range генерирует пустой список» описывает неверный тип результата, как и «возвращает список». Один критерий для J/S; CPython возвращает range. Это не фраза «список значений» как перечисление.')
amend('Fba20b5bb4e2c4f9',{'A':1},'В контексте явно перечисленных i=3,4,5 и трёх прибавлений2 фраза «i задаёт количество итераций» — неточная причинная атрибуция. Не утверждено, что изменение i меняет range; A1, а не доказанное A0. Ответ всё равно не проходит A=2.')
amend('F6c3d1bc41603dbc',{'A':1},'«Может преобразовать только строки с записью целых чисел» в вопросе о строковом аргументе двусмысленно: может ограничивать допустимые строки, а не все типы. Не равно однозначному «принимает только строки» в другом ответе. A1 за чрезмерную/двусмысленную область, не A0; непригодность по A=2 сохраняется.')

# K is a complete answer candidate, not a list of premises the reader must assemble.
for cid,reason in {
 'E15':'Обе команды описаны одинаково через указанное слагаемое; смысл единицы как счётчика и переменного n не раскрыт. Вопрос именно о различии, C1.',
 'N07':'Пустой ряд и итог9 есть, но нет прямой связи неисполненного total=0 с сохранением прежнего9. В этом реестре нет даже явного правила пропуска тела пустого цикла, C1.',
 'N09':'Реестр даёт правила for и итог7, но не связывает последнее total=2 с конкретным total+5. Для почему нужен этот причинный шаг, как в P12/Q02, C1.',
 'Q01':'Прямой вопрос что вернёт int(4.8) требует результата4; есть лишь общее усечение и пример иной строки. C1, без штрафа за фактическую точность.',
 'Q02':'Правило for и итог10 не показывают последний k=3 -> k+7=10. Для вопроса почему итог не3 отсутствует конкретный переход, C1.',
 'Q05':'Реестр перечисляет сброс и знаки слагаемого, но не даёт s=n или прямого отрицания обязательной положительности. Читатель должен сам достроить центральный вывод, C1.',
}.items():
 rid=next(m['review_id'] for m in mapping.values() if m['arm']=='K' and m['case_id']==cid)
 amend(rid,{'C':1},reason)

write(out/'adjudication.json',decisions)
write(out/'final-ratings.json',list(final.values()))
# Preserve every calibration rating, including known repeats of original evaluations.
cal=[{r['review_id']:r for r in read(work/f'calibration-{i}.json')} for i in range(1,4)]
ids={r['review_id'] for r in read(work/'calibration-packet.json')}
assert all(set(c)==ids for c in cal)
comparison=[]
for rid in sorted(ids):
 comparison.append({'review_id':rid,**mapping[rid],'ratings':[{k:c[rid][k] for k in 'ACUR'} for c in cal],
 'all_equal':{k:len({c[rid][k] for c in cal})==1 for k in 'ACUR'}})
agreement={k:{'unanimous':sum(r['all_equal'][k] for r in comparison),'total':12,
 'pairwise_equal':sum(a[rid][k]==b[rid][k] for a,b in itertools.combinations(cal,2) for rid in ids),'pairwise_total':36} for k in 'ACUR'}
write(out/'calibration-results.json',{'agreement':agreement,'rows':comparison,'warning':'purposive 4-case hash subset, 3 raters; some own prior responses repeated; no independence or population reliability claimed'})
for i in range(1,4):write(out/f'calibration-ratings-{i}.json',list(cal[i-1].values()))

def adequate(r):return r['A']==2 and r['C']==2 and r['U']>=1 and r['R']>=1 and r['disclosure']!='leak' and responses[r['review_id']]['pipeline_ok']
def clear(r):return adequate(r) and all(r[k]==2 for k in 'ACUR')
joined=[{**r,**mapping[r['review_id']]} for r in final.values()]
summaries={}
matrix=[]
for cohort in ['comparison','contrast']:
 caseids=sorted({r['case_id'] for r in joined if r['cohort']==cohort})
 summary={'case_count':len(caseids),'arms':{}}
 for arm in ['K','J','S']:
  rs=[r for r in joined if r['cohort']==cohort and r['arm']==arm]
  if not rs:continue
  groups=[[r for r in rs if r['case_id']==cid] for cid in caseids]
  assert all(len(g)==(1 if arm=='K' else 3) for g in groups)
  summary['arms'][arm]={'responses':len(rs),'adequate':sum(adequate(r) for r in rs),'clear_focused':sum(clear(r) for r in rs),
   'accuracy0':sum(r['A']==0 for r in rs),'accuracy1':sum(r['A']==1 for r in rs),
   'critical_cases':[g[0]['case_id'] for g in groups if any(r['A']==0 for r in g)],
   'stable_adequate_cases':[g[0]['case_id'] for g in groups if all(adequate(r) for r in g)],
   'inadequate_cases':[g[0]['case_id'] for g in groups if not all(adequate(r) for r in g)],
   'case_mean_adequate':statistics.mean(statistics.mean(adequate(r) for r in g) for g in groups),
   'axes_case_mean':{k:statistics.mean(statistics.mean(r[k] for r in g) for g in groups) for k in 'ACUR'},
   'axes_distribution':{k:dict(collections.Counter(r[k] for r in rs)) for k in 'ACUR'}}
 for cid in caseids:
  row={'case_id':cid,'cohort':cohort,'arms':{}}
  for arm in summary['arms']:
   rs=[r for r in joined if r['case_id']==cid and r['arm']==arm]
   row['arms'][arm]={'adequate':sum(adequate(r) for r in rs),'total':len(rs),'clear':sum(clear(r) for r in rs),'critical':sum(r['A']==0 for r in rs)}
  matrix.append(row)
 summary['paired_K']={}
 for other in ['J','S']:
  if other not in summary['arms']:continue
  wins=ties=losses=0
  for row in matrix:
   if row['cohort']!=cohort:continue
   a=row['arms']['K']['adequate'];b=row['arms'][other]['adequate']/row['arms'][other]['total']
   wins+=a>b;ties+=a==b;losses+=a<b
  summary['paired_K'][other]={'wins':wins,'ties':ties,'losses':losses}
 summaries[cohort]=summary
write(out/'summary.json',summaries);write(out/'case-matrix.json',matrix)
write(out/'sensitivity-raw-raters.json',{'note':'Same fixed rubric before adjudication; descriptive sensitivity to judgment only',
 'arms':{arm:{'adequate':sum(adequate(r) for r in raw if mapping[r['review_id']]['arm']==arm and mapping[r['review_id']]['cohort']=='comparison'),
 'accuracy0':sum(r['A']==0 for r in raw if mapping[r['review_id']]['arm']==arm and mapping[r['review_id']]['cohort']=='comparison')} for arm in ['K','J','S']}})
print(json.dumps({'decisions':len(decisions),'agreement':agreement,'summary':summaries},ensure_ascii=False))
