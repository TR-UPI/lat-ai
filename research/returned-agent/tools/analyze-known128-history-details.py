"""Secondary descriptive diagnostics; frozen before known128 inference."""
from pathlib import Path
import json,hashlib,collections,statistics,importlib.util
root=Path(__file__).resolve().parent.parent
base=root/'outputs/u02-runtime-controls-2026-11-11'
out=root/'outputs/sdk-fix-and-history-scan-2026-11-11'
spec=importlib.util.spec_from_file_location('v2',root/'tools/analyze-frozen-pilot-v2.py');v2=importlib.util.module_from_spec(spec);spec.loader.exec_module(v2)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
protocol=read(out/'scan-execution-record.json')
assert protocol['secondary_analysis_sha256']==sha(Path(__file__))
assert protocol['plan_sha256']==sha(base/'known128-plan.json')
plan=read(base/'known128-plan.json');dirs=[base/f'known128-live-{n}' for n in [1,2,3]]
analysis=v2.analyze(base/'known128-plan.json',dirs)
cases=read(base/'known128-frozen/primary-cases.json');details=[];all_rows=[]
def outcome(row):
    if row['actual'] is None:return 'refusal'
    if row['actual']==row['expected']:return 'correct'
    delta=sum(row['actual'])-sum(row['expected'])
    return 'undergrade' if delta<0 else 'overgrade' if delta>0 else 'wrong_criteria_same_total'
def sig(value):return json.dumps(value,ensure_ascii=False,sort_keys=True)
for case in cases:
    key=case['id'];rows=[read(folder/f'R{n}-{key}.json') for n,folder in enumerate(dirs,1)]
    all_rows+=rows
    dispatches=[[read(folder/f'R{n}-{key}-{stage}-dispatch.json') for stage in ['proposal','verification']] for n,folder in enumerate(dirs,1)]
    request_hashes=[[d['request_sha256'] for d in ds] for ds in dispatches]
    assert all(h==request_hashes[0] for h in request_hashes),'Same case request changed: '+key
    for row in rows:
        assert len(row['stages'])==2 and all(s['http_status']==200 and s['terminal_body'] for s in row['stages'])
    proposal=[json.loads(r['raw']['candidate']['answer']) for r in rows]
    verification=[json.loads(r['raw']['verification']['answer']) for r in rows]
    checks=[r['actual'] for r in rows];evidence=[(r.get('result') or {}).get('evidence') for r in rows]
    details.append({'id':key,'task':case['task_key'],'category':case.get('category','unclassified'),'expected':case['expected'],'outcomes':[outcome(r) for r in rows],'actual_by_series':checks,'positions':[r['position'] for r in rows],'instances':[r['instance'] for r in rows],'different_outcomes':len(set(map(sig,checks)))>1,'different_total_score':len({None if c is None else sum(c) for c in checks})>1,'different_final_evidence':len(set(map(sig,evidence)))>1,'different_raw_proposal':len(set(map(sig,proposal)))>1,'different_raw_verifier':len(set(map(sig,verification)))>1,'request_sha256':request_hashes[0],'latency_ms':[r['ms'] for r in rows]})
counts_by_series=[dict(collections.Counter(outcome(read(folder/f'R{n}-{c["id"]}.json')) for c in cases)) for n,folder in enumerate(dirs,1)]
transitions={f'{a+1}_to_{b+1}':dict(collections.Counter(d['outcomes'][a]+' -> '+d['outcomes'][b] for d in details)) for a,b in [(0,1),(0,2),(1,2)]}
summary={'plan_sha256':protocol['plan_sha256'],'unique_known_cases':len(cases),'loads':3,'completed_assessments':len(all_rows),'completed_model_posts':sum(len(r['stages']) for r in all_rows),'primary_series':1,'primary_outcomes':counts_by_series[0],'descriptive_series_outcomes':counts_by_series,'varying_final_outcomes':sum(d['different_outcomes'] for d in details),'varying_final_outcome_fraction':sum(d['different_outcomes'] for d in details)/len(details),'varying_raw_proposal':sum(d['different_raw_proposal'] for d in details),'varying_raw_verifier':sum(d['different_raw_verifier'] for d in details),'varying_final_evidence_including_refusal':sum(d['different_final_evidence'] for d in details),'incorrect_at_least_once':sum(any(o not in ['correct','refusal'] for o in d['outcomes']) for d in details),'same_case_request_hashes_equal_all_series':True,'transitions_descriptive':transitions,'by_task':{task:{'cases':len(selected),'varying_final_outcomes':sum(d['different_outcomes'] for d in selected)} for task in sorted({d['task'] for d in details}) for selected in [[d for d in details if d['task']==task]]},'per_case':details,'limitations':'Known synthetic diagnostic only; no unseen labels and no real students. Three load/order clusters, not 384 independent cases. Changes can reflect order, instance or numerical state; no per-case cold/warm control. Equal results in these orders do not prove invariance. Exact wrong checks include undergrade, overgrade and wrong criteria with same total. Evidence variation is not semantic citation accuracy; no new joint metric claimed.'}
for name,value in [('known128-analysis.json',analysis),('known128-details.json',summary)]:
    with (out/name).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
print(json.dumps({k:v for k,v in summary.items() if k not in ['per_case','transitions_descriptive','limitations']},ensure_ascii=False))
