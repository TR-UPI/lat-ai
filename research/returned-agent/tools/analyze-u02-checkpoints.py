from pathlib import Path
import json,hashlib,statistics,collections
root=Path(__file__).resolve().parent.parent
out=root/'outputs/u02-runtime-controls-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=read(out/'checkpoint-protocol.json');audit=read(out/'checkpoint-recovery-audit.json')
assert audit['terminal_assessments']==20 and audit['terminal_model_posts']==40
assert audit['all_owned_instances_absent_now'] and audit['weights_before_after_match']
assert audit['checkpoint_log_sha256']==sha(out/'checkpoint-live.log')
assert sha(out/'checkpoint-protocol.json')==(out/'checkpoint-protocol.json.sha256').read_text().strip()
assert sha(root/'tools/diagnose-u02-checkpoints.mjs')==plan['script_sha256']
baseline=read(root/'outputs/u02-investigation-2026-11-11/offline-analysis.json')['request_hashes']
rows=[];targets=[];loads=[]
for session in plan['sessions']:
    folder=out/'checkpoint-live'/session['id'];terminal=read(folder/'summary.json')
    assert terminal['retirement_proven'] and terminal['error'] is None
    meta=read(folder/'loaded-model.json');sdk=read(folder/'sdk-load-config.json');instance=meta['loaded_instances'][0]
    assert instance['config']=={**plan['rest_expected_config'],'context_checkpoints':session['checkpoints']}
    assert sdk=={**plan['sdk_expected_config'],'contextCheckpoints':session['checkpoints']}
    loads.append(instance['id'])
    for position,key in enumerate(session['order'],1):
        row=read(folder/f'{position}-{key}.json');assert row['id']==key and row['position']==position and row['instance']==instance['id']
        assert len(row['calls'])==2
        for call in row['calls']:
            assert call['http_status']==200 and call['response_body']['choices'][0]['finish_reason']=='stop'
        rows.append(row)
        if key=='U02':
            assert [c['normalized_sha256'] for c in row['calls']]==baseline
            targets.append(row)
assert len(set(loads))==8 and len(rows)==20 and len(targets)==8
before=read(out/'checkpoint-live/weights-before.json');after=read(out/'checkpoint-live/weights-after-recovery.json')
assert before['sha256']==after['sha256']==plan['model_fingerprint']['sha256'].lower()
def outcome(row):return 'refusal' if row['actual'] is None else 'correct' if row['actual']==row['expected'] else 'undergrade' if sum(row['actual'])<sum(row['expected']) else 'other_error'
cells={}
for cp in [32,0]:
    for history in ['A','B']:
        selected=[r for r in targets if r['checkpoints']==cp and r['history']==history]
        cells[f'{cp}-{history}']={'loads':len(selected),'outcomes':dict(collections.Counter(map(outcome,selected))),'proposal_checks':[r['candidate_checks'] for r in selected],'verifier_checks':[r['verification_checks'] for r in selected]}
def timing(values):return {'n':len(values),'median_ms':statistics.median(values),'max_ms':max(values)}
result={'data_complete':True,'process_completed_normally':False,'exit_code':1,'post_exit_read_only_audit':'checkpoint-recovery-audit.json','loads':8,'assessments':20,'model_posts':40,'u02_observations':8,'u02_cells':cells,'rest_and_sdk_configs_equal_except_checkpoint_count':True,'same_u02_payload_hashes':baseline,'weights_before_after_sha256':before['sha256'],'verifier_constant':all(r['verification_checks']==[False,True,True] for r in targets),'non_u02_outcomes':dict(collections.Counter(outcome(r) for r in rows if r['id']!='U02')),'all_retirements_proven':True,'latency_u02_by_checkpoint':{str(cp):timing([r['ms'] for r in targets if r['checkpoints']==cp]) for cp in [32,0]},'latency_by_stage':{str(cp):{stage:timing([c['ms'] for r in targets if r['checkpoints']==cp for c in r['calls'] if c['stage']==stage]) for stage in ['proposal','verification']} for cp in [32,0]},'unit_note':'One U02 per fresh load; only two replicates in each configuration/history cell. NOT student risk or new holdout. Process exited abnormally during SDK disposal; observations and per-instance retirement proofs independently audited, not rerun.'}
with (out/'checkpoint-analysis.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False))
