"""Freeze advisory rules before real pilot data; export a separate post-label review queue."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,importlib.util,subprocess,argparse
ROOT=Path(__file__).resolve().parent.parent
FILES=['tools/review-signals.mjs','tools/review-signals-batch.mjs','tools/review-signal-pilot.py','tools/prepare-shadow-pilot.py','tools/analyze-frozen-pilot-v2.py','tools/analyze-frozen-pilot.py','tools/assessment-statistics.py','lat-ai/integration/ai/core/src/assessment-verifier.mjs','lat-ai/integration/ai/core/data/assessment-verifier-rubrics.json']
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,value):
    with Path(p).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def timestamp(value):
    result=datetime.fromisoformat(value.replace('Z','+00:00'))
    if result.tzinfo is None:raise ValueError('Timezone required')
    return result
def freeze_rules(protocol):
    value={'revision':'lexical-review-only-v1-2026-11-11','created_utc':datetime.now(timezone.utc).isoformat(),'advisory_only':True,'changes_score':False,'files_sha256':{name:sha(ROOT/name) for name in FILES},'evaluation_policy':'Only independently labeled real_student pilot after this freeze. Synthetic tests establish mechanics only. Primary series1; report workload, flagged wrong grades, false flags, and unsupported/technical cases. Never change scores or gate. No flag does not certify correctness.'}
    save(protocol,value);Path(str(protocol)+'.sha256').write_text(sha(protocol)+'\n',encoding='ascii');return value
def verify_rules(protocol):
    if sha(protocol)!=Path(str(protocol)+'.sha256').read_text().strip():raise ValueError('Signal protocol changed')
    rules=read(protocol)
    if set(rules.get('files_sha256',{}))!=set(FILES):raise ValueError('Unexpected signal dependencies')
    for name,digest in rules['files_sha256'].items():
        if sha(ROOT/name)!=digest:raise ValueError('Signal source changed: '+name)
    if rules.get('advisory_only') is not True or rules.get('changes_score') is not False:raise ValueError('Advisory-only protocol required')
    return rules
def preflight(protocol,plan_path):
    rules=verify_rules(protocol);plan=read(plan_path)
    if sha(plan_path)!=Path(str(plan_path)+'.sha256').read_text().strip():raise ValueError('Model plan changed')
    if plan.get('data_origin')!='real_student':raise ValueError('Quality evaluation requires real_student pilot; known/synthetic cases forbidden')
    dataset=Path(plan['frozen_dir']);manifest=read(dataset/'freeze.json')
    if manifest.get('data_origin')!='real_student':raise ValueError('Real pilot freeze required')
    if timestamp(rules['created_utc'])>=timestamp(manifest['frozen_utc']):raise ValueError('Signal rules must precede the real dataset freeze')
    for name in ['integration/ai/core/src/assessment-verifier.mjs','integration/ai/core/data/assessment-verifier-rubrics.json']:
        if plan['source_sha256'].get(name)!=sha(ROOT/'lat-ai'/name):raise ValueError('Verifier revision differs from pilot')
    return plan
def export(protocol,plan_path,runs,node_path,new_out):
    plan=preflight(protocol,plan_path)
    spec=importlib.util.spec_from_file_location('pilot_v2',ROOT/'tools/analyze-frozen-pilot-v2.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    analysis=module.analyze(plan_path,runs)
    if not analysis['human_pair_agreement']['available']:raise ValueError('Two independent human review records required')
    roles_spec=importlib.util.spec_from_file_location('pilot_roles',ROOT/'tools/prepare-shadow-pilot.py');roles=importlib.util.module_from_spec(roles_spec);roles_spec.loader.exec_module(roles)
    frozen=Path(plan['frozen_dir']);roles.validate_reviewer_roles(read(frozen/'review-A.frozen.json'),read(frozen/'review-B.frozen.json'),read(frozen/'adjudication.frozen.json'))
    cases=read(Path(plan['frozen_dir'])/'primary-cases.json');inputs=[];models={}
    for n,folder in enumerate(map(Path,runs),1):
        for case in cases:
            row=read(folder/f'R{n}-{case["id"]}.json');models[(n,case['id'])]=row
            inputs.append({'id':case['id'],'series':n,'task_key':case['task_key'],'student_answer':case['answer'],'verification':row['raw']['verification']})
    out=Path(new_out);out.mkdir(parents=True,exist_ok=False)
    save(out/'signal-inputs.json',inputs)
    completed=subprocess.run([str(node_path),str(ROOT/'tools/review-signals-batch.mjs'),str(out/'signal-inputs.json'),str(out/'signals.json')],capture_output=True,text=True,encoding='utf-8',check=False,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    (out/'batch.log').write_text(completed.stdout+'\n'+completed.stderr,encoding='utf-8')
    if completed.returncode:raise RuntimeError('Signal batch failed; keep output and inspect log, do not overwrite')
    payload=read(out/'signals.json')
    if payload['input_sha256']!=sha(out/'signal-inputs.json'):raise ValueError('Signal inputs changed')
    rows=payload['rows'];signals={(r['series'],r['id']):r for r in rows}
    if set(signals)!=set(models) or len(rows)!=len(models):raise ValueError('Signal row identity mismatch')
    for r in rows:
        if r.get('advisory_only') is not True or r.get('changes_score') is not False or r.get('changes_gate') is not False:raise ValueError('Unexpected scoring output')
    queue=[];metrics={'unique_primary_cases':len(cases),'primary_flagged':0,'wrong_graded':0,'wrong_graded_flagged':0,'correct_graded':0,'correct_graded_flagged':0,'refused':0,'refused_flagged':0,'unsupported':0,'technical_errors':0}
    for case in cases:
        key=case['id'];signal=signals[(1,key)];model=models[(1,key)];flag=signal['manual_review_suggested'] is True
        metrics['primary_flagged']+=flag;metrics['unsupported']+=signal['status']=='unsupported_task';metrics['technical_errors']+=signal['status']=='technical_error'
        category='refused' if model['actual'] is None else 'correct_graded' if model['actual']==case['expected'] else 'wrong_graded'
        metrics[category]+=1;metrics[category+'_flagged']+=flag
        if flag:queue.append({'id':key,'task_key':case['task_key'],'answer':case['answer'],'human_adjudicated_checks':case['expected'],'primary_model_checks':model['actual'],'signals_by_series':[signals[(n,key)] for n in [1,2,3]],'teacher_decision':None,'teacher_reason':None,'reviewed_by':None})
    report={'rule_protocol_sha256':sha(protocol),'model_plan_sha256':sha(plan_path),'advisory_only':True,'primary_series':1,'metrics_counts':metrics,'limitations':'Real-data origin and independence are recorded declarations. These counts measure flags against existing adjudicated labels; queue usefulness requires separate human decisions. Repeats do not enlarge independent n. Unsupported/no-signal cases are not certified safe. Scores/gate and blind annotation files are never overwritten.'}
    save(out/'review-queue.json',{'audience':'Unblinded post-label coordinator/teacher review, never initial blind annotators','cases':queue});save(out/'signal-analysis.json',report)
    save(out/'MANIFEST.json',{p.name:sha(p) for p in out.iterdir() if p.is_file()})
    return report
if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True);f=sub.add_parser('freeze');f.add_argument('new_protocol');r=sub.add_parser('analyze');r.add_argument('protocol');r.add_argument('model_plan');r.add_argument('run1');r.add_argument('run2');r.add_argument('run3');r.add_argument('node');r.add_argument('new_output');a=p.parse_args()
    result=freeze_rules(a.new_protocol) if a.mode=='freeze' else export(a.protocol,a.model_plan,[a.run1,a.run2,a.run3],a.node,a.new_output)
    print(json.dumps(result,ensure_ascii=False))
