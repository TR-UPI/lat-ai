"""Append-only recovery and delivery amendments for the offline human audit store."""
from pathlib import Path
from datetime import datetime,timezone
from contextlib import contextmanager
import argparse,base64,importlib.util,json,uuid,re,sys

ROOT=Path(__file__).resolve().parent.parent
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'tools'/file);value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
m=module('intake_recovery_base','receive-review-cards.py')
lease=module('audit_owned_lease','audit-store-lease.py')
DEPENDENCIES=['tools/recover-audit-store.py','tools/audit-store-lease.py','tools/test-recover-audit-store.py','tools/triage-audit-recovery.py','tools/test-triage-audit-recovery.py','tools/receive-review-cards.py','outputs/manual-audit-intake-2026-11-11/intake-protocol.json']
INTAKE=ROOT/'outputs/manual-audit-intake-2026-11-11/intake-protocol.json'
now=lambda:datetime.now(timezone.utc)
binary=lambda v:lease.encoded(v)
read=m.read;digest=m.digest;sha=m.sha
def uuid4(value):return m.identity(value)
def hexid(value):
    if not isinstance(value,str) or not re.fullmatch('[a-f0-9]{64}',value):raise ValueError('invalid_sha256_id')
    return value
def path_in(root,relative):
    p=Path(relative)
    if p.is_absolute() or '..' in p.parts or '\\' in relative or ':' in relative:raise ValueError('unsafe_relative_path')
    result=(root/p).resolve()
    if not result.is_relative_to(root.resolve()):raise ValueError('outside_store')
    return result
def inventory(folder):
    folder=Path(folder)
    return {p.name:digest(p) for p in sorted(folder.iterdir()) if p.is_file() and not p.name.startswith('.')}
def inventory_sha(folder):return sha(m.canonical(inventory(folder)).encode())
def snapshot_file(path):
    data=Path(path).read_bytes()
    return {'sha256':sha(data),'bytes_base64':base64.b64encode(data).decode()}
INPUT_NAMES={'returned.json','delivery.json','ASSIGNMENT.json'}
def execution_inventory(root,aid):
    return {p.name:inventory(p) for p in sorted((root/'recovery/executions').glob('*')) if (p/'ASSIGNMENT.json').exists() and digest(p/'ASSIGNMENT.json')==aid}
def attempt_inventory(root,aid):
    return {p.name:inventory(p) for p in sorted((root/'attempts').glob('*')) if (p/'ASSIGNMENT.json').exists() and digest(p/'ASSIGNMENT.json')==aid}
def checked_plan(path):
    value=read(path);content={k:v for k,v in value.items() if k!='content_sha256'}
    if value.get('content_sha256')!=sha(binary(content)):raise ValueError('plan_content_checksum_mismatch')
    if value['request_sha256']!=sha(m.canonical(value['request']).encode()):raise ValueError('plan_request_checksum_mismatch')
    return value
def freeze(path):
    lease.publish(path,binary({'revision':'audit-recovery-v1','created_utc':now().isoformat(),'files_sha256':{n:digest(ROOT/n) for n in DEPENDENCIES},'policy':'Append-only; never overwrite original attempts, accepted baseline or blind labels. Unknown legacy locks remain blocked. Amendments are factual records with revalidation, not silent acceptance.','supported_environment':'One Windows host, fixed local NTFS, one coordinated store, single-thread CLI. No network/FAT/cross-host/cloned concurrent stores. Process-crash recovery only; power-loss directory durability not guaranteed.','supported_reader':'status/read_status and receive.effective_status; baseline accepted/receipt is historical. Exposure history is conservative and never establishes independent gold.','legacy_writer_barrier':'Released intake.lock persists; new leases atomically exchange it without an absent-file gap. Missing initialized barrier is a manual incident. Never delete it to run old tools. Direct file writes/ACL/authentication are outside the protocol.','manual_gates':'Explicit request with reason and two declared distinct identities for recovery/amendment; identities are not authenticated. Incomplete assignment or differing executions remain manual incidents; no automatic reissue.','triage':'Read-only diagnostic and unsigned drafts. Unknown extra files are listed where inspected, not a complete proof of file provenance. No auto-repair or invented human approvals.'}))
    lease.publish(str(path)+'.sha256',(digest(path)+'\n').encode())
def verify(protocol):
    if digest(protocol)!=Path(str(protocol)+'.sha256').read_text().strip():raise ValueError('recovery_protocol_changed')
    p=read(protocol)
    if set(p['files_sha256'])!=set(DEPENDENCIES):raise ValueError('recovery_dependencies_changed')
    m.verify_hashes(ROOT,p['files_sha256']);m.verify_protocol(INTAKE)

def assignment_state(root,folder):
    folder=Path(folder).resolve();manifest=read(folder/'MANIFEST.json')
    if set(manifest)!={'ASSIGNMENT.json',*('reviewer/'+n for n in m.EXPOSED)}:raise ValueError('assignment_manifest_fields')
    m.verify_hashes(folder,manifest);a=read(folder/'ASSIGNMENT.json')
    if a['intake_protocol_sha256']!=digest(INTAKE) or a['intake_store_id']!=read(root/'STORE.json')['store_id']:raise ValueError('assignment_store_or_protocol_mismatch')
    if a['files_seen_sha256']!={n:manifest['reviewer/'+n] for n in m.EXPOSED}:raise ValueError('assignment_exposure_mismatch')
    if m.package_key(read(folder/'reviewer/cards.json'),a['reviewer_registry_id'])!=a['package_reviewer_key']:raise ValueError('content_key_mismatch')
    uuid4(a['assignment_id']);uuid4(a['reviewer_registry_id']);hexid(a['package_reviewer_key'])
    return a,digest(folder/'ASSIGNMENT.json')

def accepted_base(root,assignment_sha):
    marker=root/'accepted'/(hexid(assignment_sha)+'.json')
    commit=m.verified_commit(root,marker,assignment_sha);attempt=root/'attempts'/commit['attempt_id']
    return marker,commit,attempt,read(attempt/'RECEIPT.json')

def journal_status(root,aid):
    pending=[];writes={}
    for op in sorted((root/'recovery/operations').glob('*')):
        if not (op/'PLAN.json').exists():continue
        plan=checked_plan(op/'PLAN.json')
        if plan['request']['expected_assignment_sha256']!=aid:continue
        for source,record in plan['observed'].items():
            if digest(source)!=record['sha256']:raise ValueError('journal_observed_source_changed')
        if sha(m.canonical(read(op/'REQUEST.json')).encode())!=plan['request_sha256']:raise ValueError('journal_request_mismatch')
        result=read(op/'RESULT.json') if (op/'RESULT.json').exists() else None
        expected={i['path']:i['sha256'] for i in plan['writes']}
        if result and (result['plan_sha256']!=digest(op/'PLAN.json') or result['written_files']!=expected or result['result']!=plan['result']):raise ValueError('journal_result_mismatch')
        if not result:pending.append(op.name)
        for item in plan['writes']:
            target=path_in(root,item['path'])
            if result and not target.exists():raise ValueError('committed_journal_target_missing')
            if target.exists():
                if digest(target)!=item['sha256']:raise ValueError('journal_target_changed')
                writes[item['path']]=item['sha256']
    return {'pending_operation_ids':pending,'published_files':writes}

def committed_integrity(root):
    """After every lease acquisition, verify committed references before any data mutation.
    Incomplete work is retained for explicit recovery; a corrupt committed baseline blocks.
    This also applies when the Windows kernel reports an abandoned mutex.
    """
    for marker in sorted((root/'accepted').glob('*.json')):m.verified_commit(root,marker,hexid(marker.stem))
    checked=set()
    for op in sorted((root/'recovery/operations').glob('*')):
        if not (op/'PLAN.json').exists():
            if (op/'RESULT.json').exists():raise ValueError('journal_result_without_plan')
            continue
        plan=checked_plan(op/'PLAN.json');aid=plan['request']['expected_assignment_sha256']
        if aid not in checked:journal_status(root,aid);checked.add(aid)

def effective(root,folder):
    root=Path(root).resolve();folder=Path(folder).resolve();a,aid=assignment_state(root,folder)
    marker,commit,attempt,receipt=accepted_base(root,aid)
    journal=journal_status(root,aid)
    original=read(attempt/'delivery.json');current=original;parent=None;events=[]
    exposure_history=[original['prior_exposure_confirmed_by_coordinator']['before_this_audit']]
    exposure_history.extend(c['prior_exposure_declared']['before_this_audit'] for c in read(attempt/'returned.json')['cards'])
    chain=root/'delivery-amendments'/aid
    files=sorted(chain.glob('*.json')) if chain.exists() else []
    for number,p in enumerate(files,1):
        if p.name!=f'{number:06d}.json':raise ValueError('amendment_sequence_gap')
        event=read(p)
        if journal['published_files'].get(p.relative_to(root).as_posix())!=digest(p):raise ValueError('amendment_missing_from_journal')
        if event['sequence']!=number or event['assignment_sha256']!=aid or event['accepted_marker_sha256']!=digest(marker) or event['parent_event_sha256']!=parent or event['prior_delivery_sha256']!=sha(binary(current)):raise ValueError('amendment_chain_mismatch')
        corrected=event['corrected_delivery'];immutable=['assignment_sha256','recipient_registry_id','files_seen_sha256']
        if any(m.canonical(corrected[k])!=m.canonical(original[k]) for k in immutable):raise ValueError('immutable_delivery_amended')
        validate_delivery_shape(corrected)
        at=datetime.fromisoformat(receipt['received_utc'].replace('Z','+00:00'))
        errors,followup=m.validate(read(folder/'reviewer/cards.json'),read(attempt/'returned.json'),a,corrected,at)
        uuid4(event['operation_id']);uuid4(event['author_registry_id']);uuid4(event['technical_reviewer_registry_id']);m.text(event['reason'],'amendment_reason')
        if event['author_registry_id']==event['technical_reviewer_registry_id']:raise ValueError('amendment_reviewer_identity_mismatch')
        if event['errors']!=errors or event['followup']!=followup or event['current_formal_validation_passed'] is not (not errors):raise ValueError('amendment_validation_mismatch')
        exposure_history.append(corrected['prior_exposure_confirmed_by_coordinator']['before_this_audit'])
        current=corrected;parent=digest(p);events.append({'sequence':number,'event_sha256':parent,'operation_id':event['operation_id']})
    at=datetime.fromisoformat(receipt['received_utc'].replace('Z','+00:00'))
    errors,followup=m.validate(read(folder/'reviewer/cards.json'),read(attempt/'returned.json'),a,current,at)
    conservative='some' if 'some' in exposure_history else 'unknown' if 'unknown' in exposure_history else 'none'
    manual=bool(errors or followup or receipt.get('original_receipt_time_unknown') or conservative!='none' or journal['pending_operation_ids'])
    return {'assignment_sha256':aid,'original_accepted_marker_sha256':digest(marker),'original_attempt_id':commit['attempt_id'],'original_delivery_sha256':digest(attempt/'delivery.json'),'current_delivery_sha256':sha(binary(current)),'current_delivery':current,'amendment_count':len(events),'latest_event_sha256':parent,'events':events,'current_formal_validation_passed':not errors,'status':'requires_manual_review' if manual else 'formally_consistent_post_label_only','errors':errors,'followup':followup,'conservative_prior_exposure':conservative,'exposure_history_requires_review':conservative!='none','pending_recovery_operation_ids':journal['pending_operation_ids'],'original_receipt_time_unknown':receipt.get('original_receipt_time_unknown',False),'independent_gold':False,'changes_model_scores':False}

def validate_delivery_shape(d):
    m.keys(d,['assignment_sha256','recipient_registry_id','coordinator_registry_id','delivered_utc','files_seen_sha256','prior_exposure_confirmed_by_coordinator'],'corrected_delivery')
    hexid(d['assignment_sha256']);uuid4(d['recipient_registry_id']);uuid4(d['coordinator_registry_id']);m.timestamp(d['delivered_utc'])
    e=d['prior_exposure_confirmed_by_coordinator'];m.keys(e,['before_this_audit','details'],'coordinator_exposure')
    if e['before_this_audit'] not in ['none','some','unknown']:raise ValueError('coordinator_exposure_status')
    m.text(e['details'],'coordinator_exposure_details')

def inspect(root,folder):
    root=Path(root).resolve();folder=Path(folder).resolve();a,aid=assignment_state(root,folder)
    result={'store_id':a['intake_store_id'],'assignment_sha256':aid,'package_reviewer_key':a['package_reviewer_key'],'lock':lease.lock_status(root),'issued_exists':(root/'issued'/(a['package_reviewer_key']+'.json')).exists(),'accepted_exists':(root/'accepted'/(aid+'.json')).exists(),'attempts':[]}
    for p in sorted((root/'attempts').glob('*')) if (root/'attempts').exists() else []:
        if p.is_dir() and re.fullmatch('[a-f0-9]{64}',p.name):
            snap=p/'ASSIGNMENT.json'
            if snap.exists() and digest(snap)==aid:
                try:status=m.saved_attempt(p)['status']
                except (OSError,ValueError,KeyError):status='incomplete_or_inconsistent'
                result['attempts'].append({'attempt_id':p.name,'inventory_sha256':inventory_sha(p),'status':status})
    result['executions']=[{'execution_id':key,'inventory_sha256':sha(m.canonical(value).encode())} for key,value in execution_inventory(root,aid).items()]
    result['journal']=journal_status(root,aid)
    if result['accepted_exists']:result['effective']=effective(root,folder)
    return result

def read_status(protocol,root,folder,details=False):
    """Supported coherent read. It never creates or retires a lease or store file."""
    verify(protocol);root=Path(root).resolve();folder=Path(folder).resolve()
    with lease.mutex(root):
        lock=lease.lock_status(root)
        if lock['state'] not in ['unlocked','owned_dead','owned_idle_barrier']:raise RuntimeError('read_blocked_by_lock: '+lock['state'])
        return inspect(root,folder) if details else effective(root,folder)

def request_schema(req):
    base={'operation_id','action','author_registry_id','technical_reviewer_registry_id','reason','expected_store_id','expected_assignment_sha256'}
    extra={'finalize_issue':set(),'recover_attempt':{'source_attempt_id','expected_source_inventory_sha256'},'recover_execution':{'source_execution_id','expected_source_inventory_sha256'},'amend_delivery':{'expected_parent_delivery_sha256','corrected_delivery'}}
    if req.get('action') not in extra:raise ValueError('unsupported_recovery_action')
    m.keys(req,base|extra[req['action']],'request');uuid4(req['operation_id']);uuid4(req['author_registry_id']);uuid4(req['technical_reviewer_registry_id'])
    if req['author_registry_id']==req['technical_reviewer_registry_id']:raise ValueError('two_distinct_recorded_reviewers_required')
    m.text(req['reason'],'reason');uuid4(req['expected_store_id']);hexid(req['expected_assignment_sha256'])

def compile_plan(protocol,root,folder,req):
    request_schema(req);a,aid=assignment_state(root,folder)
    if aid!=req['expected_assignment_sha256'] or a['intake_store_id']!=req['expected_store_id']:raise ValueError('request_target_mismatch')
    observed={};writes=[];inventories={};executions=None;attempts=None
    def observe(p):
        p=Path(p).resolve();record=snapshot_file(p);observed[str(p)]=record;return m.decode(base64.b64decode(record['bytes_base64']))
    def add(path,data):
        relative=Path(path).relative_to(root).as_posix();path_in(root,relative)
        writes.append({'path':relative,'bytes_base64':base64.b64encode(data).decode(),'sha256':sha(data)})
    observe(folder/'MANIFEST.json');observe(folder/'ASSIGNMENT.json');observe(root/'STORE.json')
    for n in m.EXPOSED:observe_path=folder/'reviewer'/n;observed[str(observe_path.resolve())]=snapshot_file(observe_path)
    action=req['action'];result={}
    if action=='finalize_issue':
        reservation=observe(root/'issuance-reservations'/(a['package_reviewer_key']+'.json'))
        if reservation['assignment_id']!=a['assignment_id'] or reservation['package_reviewer_key']!=a['package_reviewer_key'] or Path(reservation['new_assignment_path']).resolve()!=folder.resolve():raise ValueError('reservation_assignment_mismatch')
        issued={'assignment_id':a['assignment_id'],'assignment_sha256':aid,'intake_store_id':a['intake_store_id']}
        target=root/'issued'/(a['package_reviewer_key']+'.json')
        if target.exists():
            if m.canonical(observe(target))!=m.canonical(issued):raise ValueError('issued_record_conflict')
        else:add(target,binary(issued))
        result={'action':action,'issued_restored':not target.exists(),'assignment_sha256':aid,'delivery_claimed':False}
    elif action in ['recover_attempt','recover_execution']:
        if action=='recover_execution':
            uuid4(req['source_execution_id']);source=root/'recovery/executions'/req['source_execution_id']
            if inventory_sha(source)!=hexid(req['expected_source_inventory_sha256']):raise ValueError('source_execution_inventory_changed')
            manifest=read(source/'MANIFEST.json')
            if set(manifest)!=INPUT_NAMES:raise ValueError('execution_manifest_fields')
            m.verify_hashes(source,manifest)
            inputs={n:(source/n).read_bytes() for n in INPUT_NAMES}
            sid=sha((aid+sha(inputs['returned.json'])+sha(inputs['delivery.json'])).encode());src=root/'attempts'/sid
        else:
            sid=hexid(req['source_attempt_id']);src=root/'attempts'/sid;source=src
            if inventory_sha(src)!=hexid(req['expected_source_inventory_sha256']):raise ValueError('source_attempt_inventory_changed')
            inputs={n:(src/n).read_bytes() for n in INPUT_NAMES}
        for p in source.iterdir():
            if p.is_file() and not p.name.startswith('.'):observed[str(p.resolve())]=snapshot_file(p)
        if src!=source and src.exists():
            for p in src.iterdir():
                if p.is_file() and not p.name.startswith('.'):observed[str(p.resolve())]=snapshot_file(p)
            # Execution snapshots must not silently override conflicting attempt inputs.
            for n in INPUT_NAMES:
                if (src/n).exists() and (src/n).read_bytes()!=inputs[n]:raise ValueError('execution_attempt_input_conflict')
        inventories[str(src.resolve())]=inventory(src) if src.exists() else None
        if source!=src:inventories[str(source.resolve())]=inventory(source)
        # A recovery request cannot choose between different saved returns for one assignment.
        for other in sorted((root/'recovery/executions').glob('*')):
            if not (other/'ASSIGNMENT.json').exists() or digest(other/'ASSIGNMENT.json')!=aid:continue
            manifest=read(other/'MANIFEST.json')
            if set(manifest)!=INPUT_NAMES:raise ValueError('execution_manifest_fields')
            m.verify_hashes(other,manifest)
            inventories[str(other.resolve())]=inventory(other)
            if any((other/n).read_bytes()!=inputs[n] for n in INPUT_NAMES):raise ValueError('multiple_distinct_execution_inputs_manual_review_required')
        executions=execution_inventory(root,aid)
        attempts=attempt_inventory(root,aid)
        for other_id in attempts:
            other=root/'attempts'/other_id
            if other==src:continue
            if any(not (other/n).exists() or (other/n).read_bytes()!=inputs[n] for n in INPUT_NAMES):raise ValueError('multiple_distinct_attempt_inputs_manual_review_required')
        if sha(inputs['ASSIGNMENT.json'])!=aid or sha((aid+sha(inputs['returned.json'])+sha(inputs['delivery.json'])).encode())!=sid:raise ValueError('attempt_input_identity_mismatch')
        issued=observe(root/'issued'/(a['package_reviewer_key']+'.json'))
        if issued['assignment_sha256']!=aid or issued['assignment_id']!=a['assignment_id'] or issued['intake_store_id']!=a['intake_store_id']:raise ValueError('issued_record_conflict')
        target=root/'accepted'/(aid+'.json')
        if target.exists():
            commit=m.verified_commit(root,target,aid)
            if commit['attempt_id']!=sid:raise ValueError('another_attempt_already_registered')
            observe(target);result={'action':action,'already_registered':True,'assignment_sha256':aid}
        else:
            try:old=m.saved_attempt(src)
            except (OSError,ValueError,KeyError):old=None
            if old is not None:
                if old['validation_passed'] is not True:raise ValueError('terminal_rejection_not_promoted')
                at=datetime.fromisoformat(old['received_utc'].replace('Z','+00:00'))
                errors,followup=m.validate(read(folder/'reviewer/cards.json'),m.decode(inputs['returned.json']),a,m.decode(inputs['delivery.json']),at)
                if old['attempt_id']!=sid or old['assignment_sha256']!=aid or errors or old['errors']!=errors or old['followup']!=followup:raise ValueError('original_validation_not_reproducible')
                add(target,binary({'assignment_sha256':aid,'attempt_id':sid,'receipt_sha256':digest(src/'RECEIPT.json')}))
                result={'action':action,'restored_original_commit':True,'assignment_sha256':aid,'attempt_id':sid}
            else:
                # Do not repair partial original JSON in place. Preserve it and create a linked validation.
                if (src/'RECEIPT.json').exists():
                    try:prior=read(src/'RECEIPT.json')
                    except ValueError:prior=None
                    if isinstance(prior,dict) and prior.get('validation_passed') is False:raise ValueError('terminal_rejection_not_promoted')
                rid=sha(('recovery:'+req['operation_id']+':'+sid).encode());dest=root/'attempts'/rid
                at=now();errors=[];followup=[]
                try:
                    d=m.decode(inputs['delivery.json'])
                    if d.get('assignment_sha256')!=aid:raise ValueError('delivery_assignment_mismatch')
                    errors,followup=m.validate(read(folder/'reviewer/cards.json'),m.decode(inputs['returned.json']),a,d,at)
                except (ValueError,TypeError,AttributeError) as e:errors=[{'location':'input','code':str(e)}]
                receipt={'attempt_id':rid,'assignment_sha256':aid,'received_utc':at.isoformat(),'validation_passed':not errors,'status':'validated_post_label_only' if not errors else 'rejected','errors':errors,'followup':followup,'cards_in_assignment':len(a['audit_ids']),'independent_gold':False,'changes_model_scores':False,'recovered_from_attempt':sid,'recovered_from_execution':req.get('source_execution_id'),'recovery_operation_id':req['operation_id'],'original_receipt_time_unknown':True,'limitations':'New formal validation at recovery time, not proof of original receipt time or independent human quality.'}
                content={**inputs,'RECEIPT.json':binary(receipt)}
                for n,data in content.items():add(dest/n,data)
                add(dest/'MANIFEST.json',binary({n:sha(data) for n,data in content.items()}))
                if not errors:add(target,binary({'assignment_sha256':aid,'attempt_id':rid,'receipt_sha256':sha(content['RECEIPT.json'])}))
                result={'action':action,'linked_attempt_created':rid,'registered':not errors,'errors':errors,'original_preserved':True,'must_query_effective_status_not_retry_legacy_partial_attempt':True}
    else:
        state=effective(root,folder)
        if state['pending_recovery_operation_ids']:raise ValueError('pending_recovery_requires_finish_before_new_amendment')
        if state['current_delivery_sha256']!=hexid(req['expected_parent_delivery_sha256']):raise ValueError('stale_amendment_parent')
        corrected=req['corrected_delivery'];validate_delivery_shape(corrected)
        for k in ['assignment_sha256','recipient_registry_id','files_seen_sha256']:
            if m.canonical(corrected[k])!=m.canonical(state['current_delivery'][k]):raise ValueError('immutable_delivery_field: '+k)
        if m.canonical(corrected)==m.canonical(state['current_delivery']):raise ValueError('empty_amendment')
        marker,commit,attempt,receipt=accepted_base(root,aid);observe(marker)
        for n in ['returned.json','delivery.json','ASSIGNMENT.json','RECEIPT.json','MANIFEST.json']:observe(attempt/n)
        chain=root/'delivery-amendments'/aid
        for p in sorted(chain.glob('*.json')) if chain.exists() else []:observe(p)
        at=datetime.fromisoformat(receipt['received_utc'].replace('Z','+00:00'))
        errors,followup=m.validate(read(folder/'reviewer/cards.json'),read(attempt/'returned.json'),a,corrected,at)
        number=state['amendment_count']+1
        event={'sequence':number,'operation_id':req['operation_id'],'recorded_utc':now().isoformat(),'assignment_sha256':aid,'accepted_marker_sha256':digest(marker),'parent_event_sha256':state['latest_event_sha256'],'prior_delivery_sha256':state['current_delivery_sha256'],'corrected_delivery':corrected,'author_registry_id':req['author_registry_id'],'technical_reviewer_registry_id':req['technical_reviewer_registry_id'],'reason':req['reason'],'errors':errors,'followup':followup,'current_formal_validation_passed':not errors,'original_accepted_record_unchanged':True,'independent_gold':False}
        add(chain/f'{number:06d}.json',binary(event))
        result={'action':action,'amendment_sequence':number,'current_formal_validation_passed':not errors,'requires_manual_review':bool(errors or followup or state['original_receipt_time_unknown'] or state['conservative_prior_exposure']!='none' or corrected['prior_exposure_confirmed_by_coordinator']['before_this_audit']!='none'),'original_records_unchanged':True}
    plan={'revision':'audit-recovery-v1','prepared_utc':now().isoformat(),'protocol_sha256':digest(protocol),'request':req,'request_sha256':sha(m.canonical(req).encode()),'assignment_path':str(folder.resolve()),'observed':observed,'source_inventories':inventories,'assignment_executions':executions,'assignment_attempts':attempts,'writes':writes,'result':result}
    return {**plan,'content_sha256':sha(binary(plan))}

def execute(protocol,store,assignment,request_path,_fault=lambda _:None):
    verify(protocol);root=Path(store).resolve();folder=Path(assignment).resolve();raw=Path(request_path).read_bytes();req=m.decode(raw);request_schema(req)
    with lease.owned_lease(root,digest(protocol)):
        committed_integrity(root)
        operation=root/'recovery/operations'/req['operation_id'];operation.mkdir(parents=True,exist_ok=True)
        planfile=operation/'PLAN.json'
        if planfile.exists():
            plan=checked_plan(planfile)
            if plan['protocol_sha256']!=digest(protocol) or plan['request_sha256']!=sha(m.canonical(req).encode()) or plan['assignment_path']!=str(folder):raise ValueError('operation_id_reused_with_other_request')
        else:
            plan=compile_plan(protocol,root,folder,req);lease.publish(operation/'REQUEST.json',raw);lease.publish(planfile,binary(plan))
        _fault('plan_published')
        if plan['assignment_executions'] is not None and execution_inventory(root,req['expected_assignment_sha256'])!=plan['assignment_executions']:raise ValueError('assignment_execution_inventory_changed')
        if plan['assignment_attempts'] is not None:
            # This plan may itself have published a new linked attempt during an earlier run.
            owned={Path(i['path']).parts[1] for i in plan['writes'] if i['path'].startswith('attempts/')}
            actual={k:v for k,v in attempt_inventory(root,req['expected_assignment_sha256']).items() if k not in owned}
            if actual!=plan['assignment_attempts']:raise ValueError('assignment_attempt_inventory_changed')
        for p,expected in plan['source_inventories'].items():
            actual=inventory(p) if Path(p).exists() else None
            if actual!=expected:raise ValueError('source_inventory_changed: '+p)
        for p,record in plan['observed'].items():
            if digest(p)!=record['sha256']:raise ValueError('observed_source_changed: '+p)
        for item in plan['writes']:
            data=base64.b64decode(item['bytes_base64'],validate=True)
            if sha(data)!=item['sha256']:raise ValueError('planned_bytes_mismatch')
            target=path_in(root,item['path']);_fault('before:'+item['path']);lease.publish(target,data);_fault('after:'+item['path'])
        resultfile=operation/'RESULT.json'
        result={'operation_id':req['operation_id'],'plan_sha256':digest(planfile),'completed_utc':now().isoformat(),'result':plan['result'],'written_files':{i['path']:i['sha256'] for i in plan['writes']}}
        if resultfile.exists():
            old=read(resultfile)
            if old['plan_sha256']!=digest(planfile) or old['written_files']!=result['written_files']:raise ValueError('recovery_result_mismatch')
            return operation_result(root,folder,old,True)
        lease.publish(resultfile,binary(result));_fault('result_published');return operation_result(root,folder,result,False)

def operation_result(root,folder,result,replayed):
    aid=digest(folder/'ASSIGNMENT.json')
    return {**result,'replayed':replayed,'effective_status':effective(root,folder) if (root/'accepted'/(aid+'.json')).exists() else None}

@contextmanager
def adopted_reservation(root,_fault=lambda _:None):
    original_reserve=m.store_reservation;original_save=m.save
    @contextmanager
    def reserve(path):
        if Path(path).resolve()!=root:raise ValueError('nested_store_mismatch')
        yield root
    def save(path,value):
        lease.publish(path,binary(value));_fault('v1-published:'+str(Path(path).resolve()))
    m.store_reservation=reserve;m.save=save
    try:yield
    finally:m.store_reservation=original_reserve;m.save=original_save

def safe_prepare(protocol,rendered,reviewer,store,new_assignment,_fault=lambda _:None):
    verify(protocol)
    with lease.owned_lease(store,digest(protocol)) as root:
        committed_integrity(root)
        with adopted_reservation(root,_fault):return m.prepare(INTAKE,rendered,reviewer,root,new_assignment)

def safe_receive(protocol,assignment,returned,delivery,store,operation_id,_fault=lambda _:None):
    verify(protocol);uuid4(operation_id)
    with lease.owned_lease(store,digest(protocol)) as root:
        committed_integrity(root)
        a,aid=assignment_state(root,assignment)
        out=root/'recovery/executions'/operation_id;out.mkdir(parents=True,exist_ok=True)
        files={'returned.json':Path(returned).read_bytes(),'delivery.json':Path(delivery).read_bytes(),'ASSIGNMENT.json':(Path(assignment)/'ASSIGNMENT.json').read_bytes()}
        for n,data in files.items():lease.publish(out/n,data);_fault('execution_input:'+n)
        lease.publish(out/'MANIFEST.json',binary({n:sha(data) for n,data in files.items()}));_fault('input_snapshots_published')
        if (out/'RESULT.json').exists():
            prior=read(out/'RESULT.json');saved=m.saved_attempt(root/'attempts'/prior['attempt_id'])
            if {k:v for k,v in prior.items() if k!='repeat_of_saved_attempt'}!=saved or prior['assignment_sha256']!=aid:raise ValueError('execution_result_mismatch')
            if prior['validation_passed']:
                commit=m.verified_commit(root,root/'accepted'/(aid+'.json'),aid)
                if commit['attempt_id']!=prior['attempt_id']:raise ValueError('execution_commit_mismatch')
            return with_current_status(root,assignment,{**prior,'repeat_of_saved_attempt':True})
        result=receive_snapshots(root,Path(assignment),out,a,aid,_fault)
        _fault('receive_finished');lease.publish(out/'RESULT.json',binary(result));return with_current_status(root,assignment,result)

def with_current_status(root,assignment,receipt):
    marker=root/'accepted'/(receipt['assignment_sha256']+'.json')
    return {**receipt,'receipt_is_historical':True,'effective_status':effective(root,assignment) if marker.exists() else None}

def receive_snapshots(root,folder,out,a,aid,fault):
    """Use frozen v1 validation; publish every input and terminal file atomically here."""
    issued=read(root/'issued'/(a['package_reviewer_key']+'.json'))
    if issued['assignment_sha256']!=aid or issued['assignment_id']!=a['assignment_id'] or issued['intake_store_id']!=a['intake_store_id']:raise ValueError('issuance_registry_mismatch')
    inputs={n:(out/n).read_bytes() for n in INPUT_NAMES}
    sid=sha((aid+sha(inputs['returned.json'])+sha(inputs['delivery.json'])).encode())
    dest=root/'attempts'/sid;marker=root/'accepted'/(aid+'.json')
    commit=m.verified_commit(root,marker,aid) if marker.exists() else None
    if dest.exists():
        receipt=m.saved_attempt(dest)
        if receipt['validation_passed'] and (commit is None or commit['attempt_id']!=sid):raise ValueError('incomplete_or_conflicting_commit_requires_manual_review')
        return {**receipt,'repeat_of_saved_attempt':True}
    dest.mkdir(parents=True)
    for n in sorted(inputs):lease.publish(dest/n,inputs[n]);fault('attempt_input:'+n)
    at=now();errors=[];followup=[]
    if commit is not None:errors=[{'location':'package','code':'assignment_already_accepted_no_automatic_replacement'}]
    else:
        try:
            delivery=m.decode(inputs['delivery.json'])
            if delivery.get('assignment_sha256')!=aid:raise ValueError('delivery_assignment_mismatch')
            errors,followup=m.validate(read(folder/'reviewer/cards.json'),m.decode(inputs['returned.json']),a,delivery,at)
        except (ValueError,TypeError,AttributeError) as e:errors=[{'location':'input','code':str(e)}]
    receipt={'attempt_id':sid,'assignment_sha256':aid,'received_utc':at.isoformat(),'validation_passed':not errors,'status':'validated_post_label_only' if not errors else 'rejected','errors':errors,'followup':followup,'cards_in_assignment':len(a['audit_ids']),'independent_gold':False,'changes_model_scores':False,'limitations':'Formal validation only. Identity, true exposure, honest time and semantic reasoning require people. No quality rates computed.'}
    lease.publish(dest/'RECEIPT.json',binary(receipt));fault('receipt_published')
    lease.publish(dest/'MANIFEST.json',binary({n:digest(dest/n) for n in [*sorted(INPUT_NAMES),'RECEIPT.json']}));fault('attempt_manifest_published')
    if not errors:lease.publish(marker,binary({'assignment_sha256':aid,'attempt_id':sid,'receipt_sha256':digest(dest/'RECEIPT.json')}));fault('accepted_marker_published')
    return {**receipt,'repeat_of_saved_attempt':False}

def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='mode',required=True)
    f=s.add_parser('freeze');f.add_argument('new_protocol')
    for name in ['inspect','status']:
        q=s.add_parser(name);q.add_argument('protocol');q.add_argument('store');q.add_argument('assignment')
    e=s.add_parser('execute');e.add_argument('protocol');e.add_argument('store');e.add_argument('assignment');e.add_argument('request')
    a=s.add_parser('prepare');a.add_argument('protocol');a.add_argument('rendered');a.add_argument('reviewer');a.add_argument('store');a.add_argument('new_assignment')
    r=s.add_parser('receive');r.add_argument('protocol');r.add_argument('assignment');r.add_argument('returned');r.add_argument('delivery');r.add_argument('store');r.add_argument('operation_id')
    args=p.parse_args()
    if args.mode=='freeze':result=freeze(args.new_protocol)
    elif args.mode=='execute':result=execute(args.protocol,args.store,args.assignment,args.request)
    elif args.mode=='prepare':result=safe_prepare(args.protocol,args.rendered,args.reviewer,args.store,args.new_assignment)
    elif args.mode=='receive':result=safe_receive(args.protocol,args.assignment,args.returned,args.delivery,args.store,args.operation_id)
    else:
        result=read_status(args.protocol,args.store,args.assignment,details=args.mode=='inspect')
    print(json.dumps(result,ensure_ascii=False))
    return 2 if isinstance(result,dict) and result.get('validation_passed') is False else 0

if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,RuntimeError) as error:
        print(json.dumps({'status':'stopped_requires_manual_review','error_type':type(error).__name__,'reason':str(error),'automatic_retry':False},ensure_ascii=False))
        sys.exit(2)
