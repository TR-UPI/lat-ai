"""Coherent read-only comparison of post-label audit returns. Never adjudicates or scores."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,importlib.util,json,sys
from collections import Counter

ROOT=Path(__file__).resolve().parent.parent
def load(name,file):
    s=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);v=importlib.util.module_from_spec(s);s.loader.exec_module(v);return v
r=load('audit_summary_recovery','recover-audit-store.py')
RECOVERY=ROOT/'outputs/audit-recovery-2026-11-11/recovery-protocol.json'
FILES=['tools/summarize-audit-returns.py','tools/test-summarize-audit-returns.py',RECOVERY.relative_to(ROOT).as_posix()]
class ExportCorruptError(ValueError):pass

def freeze(path):
    r.lease.publish(path,r.binary({'revision':'post-label-return-summary-v1','created_utc':datetime.now(timezone.utc).isoformat(),'files_sha256':{n:r.digest(ROOT/n) for n in FILES},'scope':'Coherent snapshot of explicitly indexed assignments in one store. Same original render manifest plus audit_id only; never infer case identity from text. No gold, grading, independent-human accuracy or automatic adjudication.'}))
    r.lease.publish(str(path)+'.sha256',(r.digest(path)+'\n').encode())

def verify(protocol):
    if r.digest(protocol)!=Path(str(protocol)+'.sha256').read_text().strip():raise ValueError('summary_protocol_changed')
    p=r.read(protocol)
    if set(p['files_sha256'])!=set(FILES):raise ValueError('summary_dependency_set_changed')
    r.m.verify_hashes(ROOT,p['files_sha256']);r.verify(RECOVERY)

def case_group(groups,a,card,meta,mode):
    key=r.sha(r.m.canonical([a['source_render_manifest_sha256'],card['audit_id']]).encode())
    immutable={k:v for k,v in card.items() if k not in r.m.EDITABLE}
    fingerprint=r.sha(r.m.canonical({'metadata':meta,'card':immutable}).encode())
    group=groups.setdefault(key,{'mode':mode,'group_id':key,'render_manifest_sha256':a['source_render_manifest_sha256'],'audit_id':card['audit_id'],'immutable_fingerprint':fingerprint,'task_code':card['task_code'],'criteria':card['criteria'],'student_answer':card['student_answer'],'citation_readout':card['citation_readout'],'indexed_assignments':[],'returns':[]})
    if group['immutable_fingerprint']!=fingerprint:raise ValueError('same_audit_identity_different_immutable_content')
    return group

def compare_group(group):
    group['returns'].sort(key=lambda v:v['reviewer_registry_id']);group['indexed_assignments'].sort(key=lambda v:v['reviewer_registry_id'])
    selected=[v for v in group['returns'] if v['comparison_included']];fields=[];reasons=[]
    if len(selected)<2:reasons.append('fewer_than_two_eligible_returns')
    if len(selected)!=len(group['returns']):reasons.append('some_returns_excluded_by_current_status')
    for field in ['criteria','citation_sufficiency','contradiction']:
        for index in (range(3) if field!='contradiction' else [None]):
            values=[v['human_decision'][field] if index is None else v['human_decision'][field][index] for v in selected]
            forced=field=='citation_sufficiency' and group['citation_readout']['references'][index]['status']!='fragment_selected'
            if forced:status='schema_forced_not_compared'
            elif len(values)<2:status='not_compared'
            elif all(v=='uncertain' for v in values):status='all_uncertain'
            elif 'uncertain' in values:status='contains_uncertain'
            else:status='equal' if len(set(values))==1 else 'different'
            fields.append({'field':field,'criterion_index':index,'status':status,'values':values})
            if status=='different' and 'different_'+field not in reasons:reasons.append('different_'+field)
            if status in ['all_uncertain','contains_uncertain'] and 'uncertain_human_decision' not in reasons:reasons.append('uncertain_human_decision')
    sets=[set(v['human_decision']['contradiction_fragment_ids']) for v in selected]
    if len(sets)<2:relation='not_compared'
    elif all(v['human_decision']['contradiction']=='absent' for v in selected):relation='schema_forced_empty_not_compared'
    elif all(v==sets[0] for v in sets):relation='same_set'
    elif any(a&b for n,a in enumerate(sets) for b in sets[n+1:]):relation='partial_overlap'
    else:relation='disjoint'
    if relation in ['partial_overlap','disjoint']:reasons.append('different_contradiction_fragment_ids')
    if any('unreadable' in v['human_decision']['citation_sufficiency'] for v in selected):reasons.append('unreadable_reference_requires_review')
    free=[v['status'] for v in fields if v['status']!='schema_forced_not_compared']
    overall='has_differences' if 'different' in free or relation in ['partial_overlap','disjoint'] else 'all_equal' if free and all(v=='equal' for v in free) else 'not_fully_comparable'
    excluded=Counter(reason for v in group['returns'] if not v['comparison_included'] for reason in v['exclusion_reasons'])
    group.update(eligible_return_count=len(selected),excluded_return_count=len(group['returns'])-len(selected),exclusions_by_reason=dict(sorted(excluded.items())),missing_return_count=len(group['indexed_assignments'])-len(group['returns']),field_comparisons=fields,comparison_reviewer_order=[v['reviewer_registry_id'] for v in selected],contradiction_evidence_relation=relation,definite_free_fields_status=overall,manual_review_reasons=reasons or ['semantic_confirmation_still_required'],automatic_resolution=None)
    return group

def store_snapshot(root):
    return {p.relative_to(root).as_posix():r.digest(p) for name in ['issued','accepted','delivery-amendments','recovery/operations'] for p in sorted((root/name).rglob('*')) if p.is_file()}

def summarize(protocol,store,index_path):
    verify(protocol);root=Path(store).resolve();index_raw=Path(index_path).read_bytes();index=r.m.decode(index_raw)
    r.m.keys(index,['store_id','mode','assignments'],'index');r.uuid4(index['store_id'])
    if index['mode'] not in ['TECHNICAL_FIXTURE','DECLARED_POST_LABEL_HUMAN_RETURN']:raise ValueError('explicit_summary_mode_required')
    if not isinstance(index['assignments'],list) or not index['assignments']:raise ValueError('nonempty_assignment_index_required')
    identities=set();paths=set()
    for entry in index['assignments']:
        r.m.keys(entry,['path','assignment_sha256'],'indexed_assignment');r.hexid(entry['assignment_sha256'])
        path=str(Path(entry['path']).resolve())
        if path in paths or entry['assignment_sha256'] in identities:raise ValueError('duplicate_index_assignment')
        paths.add(path);identities.add(entry['assignment_sha256'])
    canonical_index={'store_id':index['store_id'],'mode':index['mode'],'assignments':sorted([{'path':str(Path(e['path']).resolve()),'assignment_sha256':e['assignment_sha256']} for e in index['assignments']],key=lambda e:e['assignment_sha256'])}
    assignments=[];groups={};evidence={};missing=[];not_indexed=[]
    def remember(path):
        path=Path(path).resolve();evidence[str(path)]=r.digest(path)
    with r.lease.mutex(root):
        lock=r.lease.lock_status(root)
        if lock['state'] not in ['unlocked','owned_dead','owned_idle_barrier']:raise RuntimeError('summary_blocked_by_lock: '+lock['state'])
        if r.read(root/'STORE.json')['store_id']!=index['store_id']:raise ValueError('summary_store_mismatch')
        r.committed_integrity(root);remember(root/'STORE.json')
        operational_snapshot=store_snapshot(root)
        for path in sorted((root/'issued').glob('*.json')):
            issued=r.read(path);remember(path)
            if issued['intake_store_id']!=index['store_id']:raise ValueError('issued_store_mismatch')
            if issued['assignment_sha256'] not in identities:not_indexed.append({'assignment_id':issued['assignment_id'],'assignment_sha256':issued['assignment_sha256'],'content_not_read':True})
        for entry in canonical_index['assignments']:
            folder=Path(entry['path']).resolve();a,aid=r.assignment_state(root,folder)
            if aid!=entry['assignment_sha256']:raise ValueError('indexed_assignment_changed')
            for name in ['ASSIGNMENT.json','MANIFEST.json',*('reviewer/'+n for n in r.m.EXPOSED)]:remember(folder/name)
            marker=root/'accepted'/(aid+'.json')
            info={'mode':index['mode'],'assignment_sha256':aid,'assignment_id':a['assignment_id'],'reviewer_registry_id':a['reviewer_registry_id'],'render_manifest_sha256':a['source_render_manifest_sha256']}
            original=r.read(folder/'reviewer/cards.json');meta={k:v for k,v in original.items() if k!='cards'}
            if 'TECHNICAL_FIXTURE' in str(original.get('phase','')) and index['mode']!='TECHNICAL_FIXTURE':raise ValueError('fixture_cannot_be_declared_human')
            for card in original['cards']:
                group=case_group(groups,a,card,meta,index['mode'])
                if a['reviewer_registry_id'] in [v['reviewer_registry_id'] for v in group['indexed_assignments']]:raise ValueError('duplicate_reviewer_for_same_audit_case')
                group['indexed_assignments'].append({'assignment_sha256':aid,'reviewer_registry_id':a['reviewer_registry_id']})
            if not marker.exists():
                info.update(status='no_registered_return',comparison_included=False);missing.append(aid);assignments.append(info);continue
            state=r.effective(root,folder);_,commit,attempt,receipt=r.accepted_base(root,aid)
            remember(marker)
            for name in ['returned.json','delivery.json','ASSIGNMENT.json','RECEIPT.json','MANIFEST.json']:remember(attempt/name)
            for event in (root/'delivery-amendments'/aid).glob('*.json'):remember(event)
            for op in (root/'recovery/operations').glob('*'):
                if (op/'PLAN.json').exists() and r.checked_plan(op/'PLAN.json')['request']['expected_assignment_sha256']==aid:
                    for name in ['PLAN.json','REQUEST.json','RESULT.json']:
                        if (op/name).exists():remember(op/name)
            reasons=[]
            if not state['current_formal_validation_passed']:reasons.append('current_delivery_or_return_validation_errors')
            if state['pending_recovery_operation_ids']:reasons.append('pending_recovery_operation')
            if state['original_receipt_time_unknown']:reasons.append('original_receipt_time_unknown')
            if state['conservative_prior_exposure']!='none':reasons.append('prior_exposure_history_requires_review')
            included=not reasons
            info.update(status=state['status'],comparison_included=included,comparison_exclusion_reasons=reasons,effective_status=state)
            assignments.append(info)
            returned=r.read(attempt/'returned.json')
            for card in returned['cards']:
                group=case_group(groups,a,card,meta,index['mode'])
                if a['reviewer_registry_id'] in [v['reviewer_registry_id'] for v in group['returns']]:raise ValueError('duplicate_reviewer_for_same_audit_case')
                group['returns'].append({'mode':index['mode'],'assignment_sha256':aid,'reviewer_registry_id':a['reviewer_registry_id'],'comparison_included':included,'exclusion_reasons':reasons,'human_decision':card['human_decision'],'human_reason':card['human_reason'],'reviewed_utc':card['reviewed_utc'],'prior_exposure_declared':card['prior_exposure_declared']})
        # Bind the complete read snapshot, including absence of an accepted marker.
        for path,h in evidence.items():
            if r.digest(path)!=h:raise ValueError('source_changed_during_summary')
        if r.sha(Path(index_path).read_bytes())!=r.sha(index_raw):raise ValueError('index_changed_during_summary')
        for aid in missing:
            if (root/'accepted'/(aid+'.json')).exists():raise ValueError('acceptance_changed_during_summary')
        if store_snapshot(root)!=operational_snapshot:raise ValueError('operational_state_changed_during_summary')
        view=[compare_group(g) for g in sorted(groups.values(),key=lambda g:g['group_id'])]
        texts={}
        for g in view:
            key=r.sha(r.m.canonical([g['task_code'],g['criteria'],g['student_answer']]).encode());texts.setdefault(key,[]).append(g['group_id'])
        repeated=[{'text_fingerprint':k,'group_ids':v,'note':'Same text/criteria; separate records, independence not established.'} for k,v in sorted(texts.items()) if len(v)>1]
        exclusions=Counter(reason for a in assignments for reason in a.get('comparison_exclusion_reasons',[]))
        return {'revision':'post-label-return-summary-v1','mode':index['mode'],'audience':'Unblinded coordinator only; never initial blind reviewers','summary_protocol_sha256':r.digest(protocol),'tool_sha256':r.digest(Path(__file__)),'recovery_protocol_sha256':r.digest(RECOVERY),'canonical_index_sha256':r.sha(r.binary(canonical_index)),'index_snapshot':canonical_index,'store_id':index['store_id'],'lock_state_at_read':lock['state'],'operational_snapshot_sha256':operational_snapshot,'assignments':assignments,'groups':view,'same_text_separate_records':repeated,'issued_not_in_index':sorted(not_indexed,key=lambda x:x['assignment_sha256']),'counts':{'indexed_assignments':len(assignments),'issued_not_in_index':len(not_indexed),'without_registered_return':len(missing),'excluded_assignments':sum(x.get('comparison_included') is False and x['status']!='no_registered_return' for x in assignments),'exclusions_by_reason':dict(sorted(exclusions.items())),'exact_audit_case_groups':len(view)},'evidence_sha256':evidence,'absent_accepted_markers':sorted(missing),'independent_gold':False,'changes_model_scores':False,'automatic_adjudication':False,'limitations':'Post-label review only. Declared mode/UUIDs do not prove real origin or independent people. All-equal means only definite freely chosen fields, never correctness. Uncertain and schema-forced fields are not equality evidence. Same text with different identity stays separate. No accuracy/kappa. Raw index and capture time are separate from the deterministic summary.'}

def export(protocol,store,index_path,new_output):
    root=Path(store).resolve();out=Path(new_output).resolve()
    if out.is_relative_to(root):raise ValueError('summary_output_inside_store')
    raw_index=Path(index_path).read_bytes();index=r.m.decode(raw_index)
    if any(out.is_relative_to(Path(e['path']).resolve()) for e in index['assignments']):raise ValueError('summary_output_inside_assignment')
    if out.exists():raise FileExistsError(out)
    result=summarize(protocol,store,index_path)
    if Path(index_path).read_bytes()!=raw_index:raise ValueError('index_changed_during_export')
    out.mkdir(parents=True)
    r.lease.publish(out/'SUMMARY.json',r.binary(result))
    text=['LAT AI — сводка последующего ручного аудита','Только координатору. Это снимок на момент чтения, не автоматическое решение споров.',f"Выдач в явном списке: {result['counts']['indexed_assignments']}; без зарегистрированного возврата: {result['counts']['without_registered_return']}; групп карточек: {result['counts']['exact_audit_case_groups']}."]
    for group in result['groups']:
        text.append(json.dumps({'mode':result['mode'],'audit_id':group['audit_id'],'eligible_returns':group['eligible_return_count'],'excluded_returns':group['excluded_return_count'],'missing_returns':group['missing_return_count'],'free_fields':group['definite_free_fields_status'],'manual_reasons':group['manual_review_reasons']},ensure_ascii=False))
    text.append('Все исходные решения сохранены. Совпадение полей не доказывает правильность или независимость. Первичные метки и баллы не менялись.')
    r.lease.publish(out/'READOUT.txt',('\n'.join(text)+'\n').encode())
    r.lease.publish(out/'INDEX_RECEIVED.json',raw_index)
    r.lease.publish(out/'CAPTURE.json',r.binary({'mode':result['mode'],'capture_completed_utc':datetime.now(timezone.utc).isoformat(),'raw_index_sha256':r.sha(raw_index),'summary_sha256':r.digest(out/'SUMMARY.json'),'note':'Read snapshot, not a live authorization. Verify MANIFEST before use.'}))
    r.lease.publish(out/'MANIFEST.json',r.binary({n:r.digest(out/n) for n in ['SUMMARY.json','READOUT.txt','INDEX_RECEIVED.json','CAPTURE.json']}));return result['counts']

def verify_export(protocol,store,folder):
    verify(protocol);folder=Path(folder)
    try:
        manifest=r.read(folder/'MANIFEST.json')
        if set(manifest)!={'SUMMARY.json','READOUT.txt','INDEX_RECEIVED.json','CAPTURE.json'}:raise ValueError('summary_manifest_fields')
        r.m.verify_hashes(folder,manifest);capture=r.read(folder/'CAPTURE.json')
        if capture['raw_index_sha256']!=r.digest(folder/'INDEX_RECEIVED.json') or capture['summary_sha256']!=r.digest(folder/'SUMMARY.json'):raise ValueError('capture_hash_mismatch')
    except (OSError,ValueError,KeyError) as e:raise ExportCorruptError(str(e)) from e
    current=summarize(protocol,store,folder/'INDEX_RECEIVED.json')
    matches=r.binary(current)==(folder/'SUMMARY.json').read_bytes()
    return {'current_snapshot_matches':matches,'status':'matches_at_read_time' if matches else 'stale_snapshot_generate_new_export','automatic_update':False,'mode':current['mode']}

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='mode',required=True)
    f=s.add_parser('freeze');f.add_argument('new_protocol')
    e=s.add_parser('export');e.add_argument('protocol');e.add_argument('store');e.add_argument('index');e.add_argument('new_output')
    v=s.add_parser('verify-export');v.add_argument('protocol');v.add_argument('store');v.add_argument('folder');a=p.parse_args()
    result=freeze(a.new_protocol) if a.mode=='freeze' else verify_export(a.protocol,a.store,a.folder) if a.mode=='verify-export' else export(a.protocol,a.store,a.index,a.new_output)
    print(json.dumps(result,ensure_ascii=False))
    if isinstance(result,dict) and result.get('current_snapshot_matches') is False:sys.exit(3)
if __name__=='__main__':
    try:main()
    except ExportCorruptError as e:print(json.dumps({'status':'corrupt_export','reason':str(e)},ensure_ascii=False));sys.exit(4)
    except (ValueError,OSError,RuntimeError) as e:print(json.dumps({'status':'invalid_or_unavailable','reason':str(e)},ensure_ascii=False));sys.exit(2)
