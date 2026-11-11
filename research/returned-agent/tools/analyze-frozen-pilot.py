"""Compare three predeclared series; primary is always series 1, never the best repeat."""
from pathlib import Path
import json,hashlib,importlib.util,collections,statistics,argparse
spec=importlib.util.spec_from_file_location('metrics',Path(__file__).with_name('assessment-statistics.py'));metrics=importlib.util.module_from_spec(spec);spec.loader.exec_module(metrics)
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
digest=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()

def agreement(a,b):
    if len(a)!=len(b) or not a:raise ValueError('Agreement needs paired observations')
    observed=sum(x==y for x,y in zip(a,b))/len(a)
    ca,cb=collections.Counter(a),collections.Counter(b)
    chance=sum(ca[k]*cb[k] for k in set(ca)|set(cb))/len(a)**2
    return {'n':len(a),'agreement':observed,'cohen_kappa':None if chance==1 else (observed-chance)/(1-chance),'kappa_note':'Undefined when both marginal distributions are constant.' if chance==1 else 'Descriptive; no independence or population guarantee.'}

def human_agreement(folder,primary):
    a=read(Path(folder)/'review-A.frozen.json');b=read(Path(folder)/'review-B.frozen.json')
    # Synthetic smoke fixture deliberately has no claimed human reviewers.
    if 'reviewer_id' not in a or 'reviewer_id' not in b:return {'available':False,'reason':'No real human review pairs in this fixture'}
    aa={r['id']:r for r in a['cases']};bb={r['id']:r for r in b['cases']};keys=[c['id'] for c in primary]
    if set(aa)!=set(keys) or set(bb)!=set(keys) or a['reviewer_id']==b['reviewer_id']:raise ValueError('Invalid human review pairs')
    for table in [aa,bb]:
        for row in table.values():
            if not isinstance(row['checks'],list) or len(row['checks'])!=3 or any(type(v) is not bool for v in row['checks']):raise ValueError('Invalid human checks')
    return {'available':True,'reviewers':[a['reviewer_id'],b['reviewer_id']],'exact_vectors':agreement([tuple(aa[k]['checks']) for k in keys],[tuple(bb[k]['checks']) for k in keys]),'by_criterion':[agreement([aa[k]['checks'][i] for k in keys],[bb[k]['checks'][i] for k in keys]) for i in range(3)],'disagreements':[k for k in keys if aa[k]['checks']!=bb[k]['checks']]}

def analyze(plan_file,run_dirs):
    if len(run_dirs)!=3:raise ValueError('Exactly three series required')
    plan_path=Path(plan_file);plan=read(plan_path);plan_hash=digest(plan_path)
    if plan_hash!=Path(str(plan_path)+'.sha256').read_text().strip():raise ValueError('Plan hash mismatch')
    if plan.get('primary_series')!=1 or plan.get('series')!=[1,2,3]:raise ValueError('Unrecognized series plan')
    folder=Path(plan['frozen_dir'])
    for name,expected in plan['dataset_sha256'].items():
        if Path(name).name!=name or digest(folder/name)!=expected:raise ValueError('Frozen dataset hash mismatch')
    primary=read(folder/'primary-cases.json');all_rows=[];per_series=[]
    for n,directory in enumerate(run_dirs,1):
        directory=Path(directory);summary=read(directory/'summary.json');provenance=read(directory/'provenance.json')
        if summary['plan_sha256']!=plan_hash or provenance['plan_sha256']!=plan_hash or summary['series']!=n or provenance['series']!=n:raise ValueError('Wrong plan or series/order')
        if summary['status']!='complete' or not summary['retirement_proven']:raise ValueError('Incomplete series; inspect summary, never omit missing work')
        cases=read(folder/f'repeat{n}.json');rows=[]
        if len(cases)!=len(primary) or len(summary['result_sha256'])!=len(cases):raise ValueError('Result count mismatch')
        for c in cases:
            name=c['id']+'.json'
            if Path(name).name!=name or digest(directory/name)!=summary['result_sha256'].get(name):raise ValueError('Result hash mismatch')
            row=read(directory/name)
            if row['id']!=c['id'] or row['source_id']!=c['source_id'] or row['task_key']!=c['task_key'] or row['expected']!=c['expected']:raise ValueError('Result identity mismatch')
            if row['status']=='assessed':
                if not isinstance(row['actual'],list) or len(row['actual'])!=3 or any(type(x) is not bool for x in row['actual']):raise ValueError('Invalid assessed checks')
            elif row['status']!='refused' or row['actual'] is not None:raise ValueError('Invalid terminal status')
            rows.append({**row,'category':c.get('category','unclassified'),'series':n})
        per_series.append(metrics.summarize(rows));all_rows+=rows
    first=[r for r in all_rows if r['series']==1];groups={c['id']:[r for r in all_rows if r['source_id']==c['id']] for c in primary}
    stability=[]
    for key,rows in groups.items():
        if len(rows)!=3:raise ValueError('Source ID mismatch between series')
        outcomes=collections.Counter('refused' if r['actual'] is None else json.dumps(r['actual']) for r in rows)
        stability.append({'id':key,'calls':3,'outcome_counts':dict(outcomes),'distinct_outcomes':len(outcomes),'distinct_evidence':len({json.dumps((r.get('result') or {}).get('evidence'),ensure_ascii=False) for r in rows})})
    stage_names={s['stage'] for r in all_rows for s in r.get('stages',[])}
    def timing(values):return {'n':len(values),'median_ms':statistics.median(values) if values else None,'max_ms':max(values) if values else None}
    accepted=[r for r in first if r['actual'] is not None]
    unstable=sum(r['distinct_outcomes']>1 for r in stability)
    return {'plan_sha256':plan_hash,'data_origin':plan['data_origin'],'primary_series':1,'primary':metrics.summarize(first),'series_descriptive':per_series,'unique_cases':len(primary),'model_calls':len(all_rows),'by_category':{k:metrics.summarize([r for r in first if r['category']==k]) for k in sorted({r['category'] for r in first})},'by_task':{k:metrics.summarize([r for r in first if r['task_key']==k]) for k in sorted({r['task_key'] for r in first})},'instability':{'cases':unstable,'fraction':unstable/len(primary),'per_case':stability},'latency_all_calls':timing([r['ms'] for r in all_rows]),'latency_by_stage':{k:timing([s['ms'] for r in all_rows for s in r.get('stages',[]) if s['stage']==k]) for k in sorted(stage_names)},'human_pair_agreement':human_agreement(folder,primary),'model_vs_adjudicated_accepted_only':[agreement([r['actual'][i] for r in accepted],[r['expected'][i] for r in accepted]) for i in range(3)] if accepted else None,'limitations':'First series only for primary metrics. Repeats never increase independent n. Kappa excludes model refusals; coverage is reported separately. Binomial bound assumes representative independent works and reliable labels; clustered pupils/classes and synthetic tests do not establish population risk. Semantic citation correctness requires human review. Hashes detect accidental changes, not an adversary rewriting both files and manifests.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('run1');p.add_argument('run2');p.add_argument('run3');p.add_argument('new_output');a=p.parse_args()
    result=analyze(a.plan,[a.run1,a.run2,a.run3]);
    with Path(a.new_output).open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'primary':result['primary'],'unstable_cases':result['instability']['cases'],'unique_cases':result['unique_cases'],'calls':result['model_calls']}))
