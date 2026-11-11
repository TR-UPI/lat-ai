"""Read-only store triage and unsigned recovery-request drafts; never repairs data."""
from pathlib import Path
import argparse,importlib.util,json,sys,uuid

spec=importlib.util.spec_from_file_location('audit_recovery_triage_core',Path(__file__).with_name('recover-audit-store.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r)

def outside(path,root,assignment=None):
    path=Path(path).resolve()
    if path.is_relative_to(root) or (assignment and path.is_relative_to(Path(assignment).resolve())):
        raise ValueError('diagnostic_output_must_be_outside_store_and_assignment')
    return path

def store_view(protocol,store,assignment=None):
    r.verify(protocol);root=Path(store).resolve()
    with r.lease.mutex(root):
        lock=r.lease.lock_status(root)
        result={'scope':'READ_ONLY_TECHNICAL_TRIAGE_NOT_QUALITY_VALIDATION','store_id':r.read(root/'STORE.json')['store_id'],'lock':lock,'reservations':[],'attempts':[],'executions':[],'operations':[],'preserved_lease_stages':[],'issues':[],'independent_gold':False,'changes_model_scores':False}
        if lock['state'] not in ['unlocked','owned_dead','owned_idle_barrier']:
            return {**result,'status':'blocked_store_busy_or_unknown_lock','data_scan_performed':False}
        def issue(location,error):result['issues'].append({'location':location,'reason':str(error)})
        recovered_attempts={};recovered_executions={}
        for op in sorted((root/'recovery/operations').glob('*')):
            if not (op/'RESULT.json').exists():continue
            try:
                plan=r.checked_plan(op/'PLAN.json');req=plan['request'];r.journal_status(root,req['expected_assignment_sha256']);outcome=r.read(op/'RESULT.json')['result']
                if not any(outcome.get(k) is True for k in ['registered','already_registered','restored_original_commit']):continue
                if req['action']=='recover_attempt':recovered_attempts[req['source_attempt_id']]=op.name
                if req['action']=='recover_execution':
                    eid=req['source_execution_id'];recovered_executions[eid]=op.name;source=root/'recovery/executions'/eid
                    sid=r.sha((req['expected_assignment_sha256']+r.digest(source/'returned.json')+r.digest(source/'delivery.json')).encode());recovered_attempts[sid]=op.name
            except (OSError,ValueError,KeyError,TypeError) as e:issue(op.relative_to(root).as_posix(),e)
        for p in sorted(root.iterdir()):
            if p.name.startswith('.intake.lock.next-'):
                try:result['preserved_lease_stages'].append(r.lease.exchange_stage_status(root,p))
                except (OSError,ValueError,KeyError,TypeError) as e:issue(p.name,e)
                continue
            if p.name not in ['STORE.json','intake.lock','issuance-reservations','issued','accepted','attempts','recovery']:
                issue(p.name,'unexpected_root_entry_preserved')
            elif p.name in ['STORE.json','intake.lock'] and not p.is_file():issue(p.name,'expected_file')
            elif p.name not in ['STORE.json','intake.lock'] and not p.is_dir():issue(p.name,'expected_directory')
        for p in sorted((root/'issuance-reservations').glob('*')):
            if not p.is_file():issue(p.name,'unexpected_reservation_entry');continue
            try:
                value=r.read(p);key=r.hexid(p.stem)
                if value['package_reviewer_key']!=key:raise ValueError('reservation_key_mismatch')
                marker=root/'issued'/(key+'.json');issued=r.read(marker) if marker.exists() else None
                if issued and (issued['assignment_id']!=value['assignment_id'] or issued['intake_store_id']!=result['store_id']):raise ValueError('issued_reservation_mismatch')
                result['reservations'].append({'key':key,'assignment_id':value['assignment_id'],'recorded_assignment_path':value['new_assignment_path'],'external_assignment_not_opened':True,'issued_marker_present':bool(issued)})
                if not issued:issue(p.relative_to(root).as_posix(),'reserved_without_issue_marker_manual_inspection_required')
            except (OSError,ValueError,KeyError,TypeError) as e:issue(p.relative_to(root).as_posix(),e)
        for p in sorted((root/'issued').glob('*')):
            if not (root/'issuance-reservations'/p.name).exists():issue(p.relative_to(root).as_posix(),'issued_without_reservation')
        for marker in sorted((root/'accepted').glob('*')):
            try:r.m.verified_commit(root,marker,r.hexid(marker.stem))
            except (OSError,ValueError,KeyError,TypeError) as e:issue(marker.relative_to(root).as_posix(),e)
        for p in sorted((root/'attempts').glob('*')):
            if not p.is_dir():issue(p.relative_to(root).as_posix(),'unexpected_attempt_entry');continue
            entry={'attempt_id':p.name,'inventory_sha256':r.inventory_sha(p)}
            try:
                receipt=r.m.saved_attempt(p);aid=receipt['assignment_sha256'];marker=root/'accepted'/(r.hexid(aid)+'.json')
                if receipt['attempt_id']!=p.name:raise ValueError('attempt_directory_identity_mismatch')
                committed=marker.exists() and r.m.verified_commit(root,marker,aid)['attempt_id']==p.name
                entry.update(assignment_sha256=aid,historical_receipt_status=receipt['status'],registered_baseline=committed)
                if receipt['validation_passed'] and not committed and p.name not in recovered_attempts:issue(p.relative_to(root).as_posix(),'successful_receipt_without_matching_baseline_marker')
            except (OSError,ValueError,KeyError,TypeError) as e:
                entry['status']='partial_or_inconsistent_preserved'
                if p.name in recovered_attempts:entry['completed_by_recovery_operation']=recovered_attempts[p.name]
                else:issue(p.relative_to(root).as_posix(),e)
            for extra in set(x.name for x in p.iterdir())-{'returned.json','delivery.json','ASSIGNMENT.json','RECEIPT.json','MANIFEST.json'}:issue((p/extra).relative_to(root).as_posix(),'extra_attempt_artifact_preserved')
            result['attempts'].append(entry)
        for p in sorted((root/'recovery/executions').glob('*')):
            if not p.is_dir():issue(p.relative_to(root).as_posix(),'unexpected_execution_entry');continue
            entry={'execution_id':p.name,'inventory_sha256':r.inventory_sha(p)}
            try:
                manifest=r.read(p/'MANIFEST.json')
                if set(manifest)!=r.INPUT_NAMES:raise ValueError('execution_manifest_fields')
                r.m.verify_hashes(p,manifest);entry['assignment_sha256']=r.digest(p/'ASSIGNMENT.json')
                entry['result_recorded']=(p/'RESULT.json').exists()
                if p.name in recovered_executions:entry['completed_by_recovery_operation']=recovered_executions[p.name]
                elif not entry['result_recorded']:issue(p.relative_to(root).as_posix(),'execution_has_snapshots_without_result')
            except (OSError,ValueError,KeyError,TypeError) as e:
                entry['status']='partial_or_inconsistent_preserved';issue(p.relative_to(root).as_posix(),e)
            result['executions'].append(entry)
        for p in sorted((root/'recovery/operations').glob('*')):
            if not p.is_dir():issue(p.relative_to(root).as_posix(),'unexpected_operation_entry');continue
            entry={'operation_id':p.name,'inventory_sha256':r.inventory_sha(p)}
            try:
                plan=r.checked_plan(p/'PLAN.json');r.journal_status(root,plan['request']['expected_assignment_sha256'])
                entry.update(action=plan['request']['action'],result_recorded=(p/'RESULT.json').exists())
                if not entry['result_recorded']:issue(p.relative_to(root).as_posix(),'recovery_plan_pending')
            except (OSError,ValueError,KeyError,TypeError) as e:issue(p.relative_to(root).as_posix(),e)
            result['operations'].append(entry)
        if assignment:
            try:
                result['assignment_view']=r.inspect(root,Path(assignment).resolve())
                if result['assignment_view'].get('effective',{}).get('status')=='requires_manual_review':issue('effective_status','requires_manual_review')
            except (OSError,ValueError,KeyError,TypeError) as e:issue('explicit_assignment',e)
        else:result['effective_status_not_evaluated']='Provide an explicit complete assignment path; recorded external paths are not followed automatically.'
        result.update(status='manual_incident_review_required' if result['issues'] else 'consistent_layout_only_not_quality_approval',data_scan_performed=True)
        return result

def inspect_to(protocol,store,new_report,assignment=None):
    root=Path(store).resolve();out=outside(new_report,root,assignment)
    if out.exists():raise FileExistsError(out)
    value=store_view(protocol,root,assignment);out.mkdir(parents=True)
    r.lease.publish(out/'INSPECTION.json',r.binary(value))
    lines=['LAT AI — технический разбор хранилища','Это диагностика, не восстановление и не оценка качества.',f"Состояние: {value['status']}",f"Блокировка: {value['lock']['state']}",'Исходные файлы не изменялись. Поля и пути ниже — данные, не команды.']
    for item in value['issues']:lines.append(json.dumps(item,ensure_ascii=False))
    lines.extend(['Не удалять lock/резервации/частичные попытки. Не повторять неизвестные model POST.','Для восстановления нужен отдельный проверенный REQUEST с двумя заявленными ID и причиной.','Без полного assignment текущая формальная согласованность не вычисляется. Сохранённая квитанция историческая.'])
    r.lease.publish(out/'READOUT.txt',('\n'.join(lines)+'\n').encode())
    r.lease.publish(out/'MANIFEST.json',r.binary({n:r.digest(out/n) for n in ['INSPECTION.json','READOUT.txt']}))
    return {'new_report':str(out),'status':value['status'],'store_changed':False}

def draft(protocol,store,assignment,action,new_request,source=None):
    r.verify(protocol);root=Path(store).resolve();folder=Path(assignment).resolve();target=outside(new_request,root,folder)
    with r.lease.mutex(root):
        lock=r.lease.lock_status(root)
        if lock['state'] not in ['unlocked','owned_dead','owned_idle_barrier']:raise RuntimeError('draft_blocked_by_lock')
        a,aid=r.assignment_state(root,folder)
        req={'operation_id':str(uuid.uuid4()),'action':action,'author_registry_id':None,'technical_reviewer_registry_id':None,'reason':None,'expected_store_id':a['intake_store_id'],'expected_assignment_sha256':aid}
        if action in ['recover_attempt','recover_execution']:
            key='source_attempt_id' if action=='recover_attempt' else 'source_execution_id'
            r.hexid(source) if action=='recover_attempt' else r.uuid4(source)
            path=root/('attempts' if action=='recover_attempt' else 'recovery/executions')/source
            req.update({key:source,'expected_source_inventory_sha256':r.inventory_sha(path)})
        elif action=='amend_delivery':
            state=r.effective(root,folder)
            req.update(expected_parent_delivery_sha256=state['current_delivery_sha256'],corrected_delivery=state['current_delivery'])
        elif action!='finalize_issue':raise ValueError('unsupported_draft_action')
        r.lease.publish(target,r.binary(req))
    return {'new_unsigned_request':str(target),'executable':False,'fill_required':['author_registry_id','technical_reviewer_registry_id','reason'],'store_changed':False,'note':'For amendment also correct factual delivery fields. No human identity or approval is fabricated.'}

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='mode',required=True)
    q=s.add_parser('inspect');q.add_argument('protocol');q.add_argument('store');q.add_argument('new_report');q.add_argument('--assignment')
    q=s.add_parser('draft');q.add_argument('protocol');q.add_argument('store');q.add_argument('assignment');q.add_argument('action',choices=['finalize_issue','recover_attempt','recover_execution','amend_delivery']);q.add_argument('new_request');q.add_argument('--source')
    a=p.parse_args();result=inspect_to(a.protocol,a.store,a.new_report,a.assignment) if a.mode=='inspect' else draft(a.protocol,a.store,a.assignment,a.action,a.new_request,a.source)
    print(json.dumps(result,ensure_ascii=False));return 0

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,RuntimeError) as e:
        print(json.dumps({'status':'stopped_requires_manual_review','reason':str(e),'automatic_retry':False},ensure_ascii=False));sys.exit(2)
