from pathlib import Path
from collections import Counter
import hashlib
import json

root = Path(__file__).resolve().parents[1]
out = root/'outputs/assessment-unseen-2026-11-11'
cases = json.loads((out/'unseen48.json').read_text(encoding='utf-8'))
freeze = json.loads((out/'freeze.json').read_text(encoding='utf-8'))
assert hashlib.sha256((out/'unseen48.json').read_bytes()).hexdigest() == freeze['cases_sha256']
manifest = json.loads((out/'source-before.json').read_text(encoding='utf-8'))
assert all(hashlib.sha256((root/'lat-ai'/x['path']).read_bytes()).hexdigest() == x['sha256'] for x in manifest)
rows = []
for case in cases:
    result = json.loads((out/'first-pass'/f"{case['id']}.json").read_text(encoding='utf-8'))
    assert result['expected'] == case['expected']
    actual = result['actual']
    row = {**case, 'actual': actual, 'match': result['match'], 'ms': result['ms'], 'evidence': result['result']['evidence'] if result['result'] else None}
    row['expected_points'] = sum(case['expected'])
    row['actual_points'] = sum(actual) if actual is not None else None
    row['false_credit'] = [i+1 for i,(e,a) in enumerate(zip(case['expected'],actual)) if a and not e] if actual else []
    row['missed_credit'] = [i+1 for i,(e,a) in enumerate(zip(case['expected'],actual)) if e and not a] if actual else []
    rows.append(row)
def metrics(group):
    return {'cases':len(group),'exact_checks':sum(r['match'] for r in group),'correct_total_points':sum(r['actual_points']==r['expected_points'] for r in group), 'unavailable':sum(r['actual'] is None for r in group),'false_credit_criteria':sum(len(r['false_credit']) for r in group),'missed_credit_criteria':sum(len(r['missed_credit']) for r in group),'undergraded_answers':sum(r['actual_points'] is not None and r['actual_points']<r['expected_points'] for r in group),'overgraded_answers':sum(r['actual_points'] is not None and r['actual_points']>r['expected_points'] for r in group)}
latencies=sorted(r['ms'] for r in rows)
summary={'first_pass':metrics(rows),'by_task':{t:metrics([r for r in rows if r['task_key']==t]) for t in sorted(set(r['task_key'] for r in rows))},'by_category':{t:metrics([r for r in rows if r['category']==t]) for t in sorted(set(r['category'] for r in rows))},'failed_ids':[r['id'] for r in rows if not r['match']],'latency_ms':{'min':min(latencies),'median':(latencies[23]+latencies[24])/2,'p95_nearest_rank':latencies[45],'max':max(latencies)},'frozen_cases_unchanged':True,'original_source_files_unchanged':len(manifest),'teacher_validated':False,'tuned_on_this_set':False}
(out/'metrics.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
(out/'case-results.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
lines=[]
for row in rows:
    lines.extend([f"{row['id']} | {row['task_key']} | {row['category']} | {'PASS' if row['match'] else 'FAIL'}",f"Ответ: {row['answer']}",f"Ожидание: {row['expected']} ({row['expected_points']}/3). Получено: {row['actual']} ({row['actual_points']}/3).",f"Обоснование меток до прогона: {row['rationale']}",f"Цитаты: {json.dumps(row['evidence'],ensure_ascii=False)}",''])
(out/'CASE_REVIEW.txt').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False))
