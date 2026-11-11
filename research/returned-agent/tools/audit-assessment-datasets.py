from pathlib import Path
import json,hashlib,importlib.util,collections
root=Path(__file__).resolve().parent.parent;out=root/'outputs/ai-pilot-integrity-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
spec=importlib.util.spec_from_file_location('stats',root/'tools/assessment-statistics.py');stats=importlib.util.module_from_spec(spec);spec.loader.exec_module(stats)
datasets=[]
for folder,metrics in [('assessment-evidence-v2-2026-11-11','candidate-h-holdout-metrics.json'),('assessment-v3-2026-11-11','holdout32-metrics.json')]:
 base=root/'outputs'/folder;p=base/'holdout32.json';cases=read(p)
 datasets.append({'dataset':folder,'first_id':cases[0]['id'],'last_id':cases[-1]['id'],'cases':len(cases),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'metrics':read(base/metrics),'ids':[c['id'] for c in cases]})
a=read(root/'outputs/assessment-evidence-v2-2026-11-11/holdout32.json');b=read(root/'outputs/assessment-v3-2026-11-11/holdout32.json')
allcases=read(root/'outputs/assessment-v3-2026-11-11/regression128-with-evidence.json')+b
source=read(root/'outputs/assessment-v3-2026-11-11/stability48.json')
groups=collections.defaultdict(list)
for c in source:
 r=read(root/'outputs/assessment-v3-2026-11-11/stability48'/f"{c['id']}.json");groups[c.get('source_id',c['id'])].append(r)
stability=[]
for key,rows in sorted(groups.items()):
 outcomes=collections.Counter(json.dumps(r['actual']) for r in rows)
 quotes=collections.Counter(json.dumps((r.get('result') or {}).get('evidence'),ensure_ascii=False) for r in rows)
 stability.append({'source_id':key,'calls':len(rows),'outcomes':dict(outcomes),'distinct_outcomes':len(outcomes),'distinct_evidence':len(quotes)})
report={'datasets':datasets,'shared_case_ids':sorted({c['id'] for c in a}&{c['id'] for c in b}),'shared_exact_task_answers':len({(c['task_key'],c['answer']) for c in a}&{(c['task_key'],c['answer']) for c in b}),'replay160':{'cases':len(allcases),'unique_ids':len({c['id'] for c in allcases}),'unique_task_answer_pairs':len({(c['task_key'],c['answer']) for c in allcases}),'components':dict(collections.Counter(c['id'][0] for c in allcases))},'historical_stability48':{'unique_cases':len(groups),'calls':sum(len(v) for v in groups.values()),'unstable_outcomes':sum(r['distinct_outcomes']>1 for r in stability),'cases':stability},'conditional_one_sided95_upper':{'H_zero_of_26':stats.error_upper95(0,26),'V_one_of_26':stats.error_upper95(1,26)}}
(out/'dataset-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k not in ['datasets','historical_stability48']},ensure_ascii=False))
print(json.dumps({k:v for k,v in report['historical_stability48'].items() if k!='cases'}))
for d in datasets:print(json.dumps({k:v for k,v in d.items() if k not in ['metrics','ids']}))
