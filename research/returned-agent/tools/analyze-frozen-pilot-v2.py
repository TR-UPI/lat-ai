"""V2 provenance/order checks followed by the unchanged primary-series statistics."""
from pathlib import Path
import json, hashlib, importlib.util, argparse
spec=importlib.util.spec_from_file_location('old_analysis',Path(__file__).with_name('analyze-frozen-pilot.py'))
base=importlib.util.module_from_spec(spec);spec.loader.exec_module(base)
read=base.read
digest=base.digest

def analyze(plan_file,run_dirs):
    if len(run_dirs)!=3:raise ValueError('Exactly three series required')
    plan=read(plan_file)
    if plan.get('format')!=2 or plan.get('load_policy')!='fresh_owned_instance_per_series_no_warmup':raise ValueError('Expected v2 fresh-instance plan')
    orders=plan.get('execution_orders',[])
    if len(orders)!=3 or len({tuple(o) for o in orders})!=3:raise ValueError('Three different orders required')
    ids={c['id'] for c in read(Path(plan['frozen_dir'])/'primary-cases.json')}
    if any(len(o)!=len(ids) or set(o)!=ids for o in orders):raise ValueError('Order is not a permutation')
    instances=[]
    for n,d in enumerate(run_dirs,1):
        folder=Path(d);summary=read(folder/'summary.json');provenance=read(folder/'provenance.json')
        if summary.get('format')!=2 or summary.get('execution_order')!=orders[n-1] or provenance.get('execution_order')!=orders[n-1]:raise ValueError('Execution order mismatch')
        hashes=summary.get('provenance_sha256',{})
        required={'environment-before.json','environment-after.json','loaded-model.json','provenance.json'}|set(summary['result_sha256'])
        if not required<=set(hashes):raise ValueError('Missing provenance hashes')
        for name,value in hashes.items():
            if Path(name).name!=name or digest(folder/name)!=value:raise ValueError('Provenance bytes changed')
        for name in ['environment-before.json','environment-after.json']:
            if read(folder/name)!=plan['environment']:raise ValueError('Environment mismatch')
        series_instance=None
        prior_calls=[]
        for pos,key in enumerate(orders[n-1],1):
            row=read(folder/f'R{n}-{key}.json')
            if row.get('position')!=pos or row.get('fresh_before_case')!=(pos==1) or row.get('predecessor_case_ids')!=orders[n-1][:pos-1]:raise ValueError('Row history mismatch')
            if not row.get('instance'):raise ValueError('Missing instance ID')
            if series_instance is None:series_instance=row['instance']
            if row['instance']!=series_instance:raise ValueError('Instance changed within series')
            for stage in ['proposal','verification']:
                name=f'R{n}-{key}-{stage}-dispatch.json'
                if name not in hashes:raise ValueError('Missing dispatch provenance')
                dispatch=read(folder/name)
                if dispatch.get('instance')!=series_instance or dispatch.get('source_id')!=key or dispatch.get('stage')!=stage:raise ValueError('Dispatch identity mismatch')
                previous=dispatch.get('predecessor_calls')
                if not isinstance(previous,list) or [(c['source_id'],c['stage']) for c in previous]!=prior_calls:raise ValueError('Dispatch history mismatch')
                prior_calls.append((key,stage))
        models=read(folder/'loaded-model.json').get('models',[])
        loaded=[i for m in models for i in m.get('loaded_instances',[]) if i['id']==series_instance]
        if len(loaded)!=1 or loaded[0]['config']!=plan['expected_load_config']:raise ValueError('Loaded config mismatch')
        instances.append(series_instance)
    if len(instances)!=3 or len(set(instances))!=3:raise ValueError('Three distinct owned instances required')
    result=base.analyze(plan_file,run_dirs)
    result['execution']={'orders':orders,'instances':instances,'environment':plan['environment'],'load_policy':plan['load_policy']}
    result['limitations']+=' Different orders are a bounded sensitivity check, not independent samples or proof of order invariance. Each case is fresh only if first in its series; this is NOT a per-case cold/warm experiment. No automated semantic citation review.'
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('plan');p.add_argument('run1');p.add_argument('run2');p.add_argument('run3');p.add_argument('new_output');a=p.parse_args()
    result=analyze(a.plan,[a.run1,a.run2,a.run3])
    with Path(a.new_output).open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
    print(json.dumps({'unique_cases':result['unique_cases'],'unstable_cases':result['instability']['cases'],'primary':result['primary']}))
