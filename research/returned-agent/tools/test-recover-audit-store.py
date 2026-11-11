import importlib.util,tempfile,unittest,json,uuid,copy,os,subprocess,sys,shutil
from datetime import timedelta
from unittest.mock import patch
from pathlib import Path
spec=importlib.util.spec_from_file_location('recovery',Path(__file__).with_name('recover-audit-store.py'))
r=importlib.util.module_from_spec(spec);spec.loader.exec_module(r);m=r.m
REVIEWER='11111111-1111-4111-8111-111111111111';AUTHOR='22222222-2222-4222-8222-222222222222';TECH='33333333-3333-4333-8333-333333333333'

class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.base=Path(self.temp.name)
        self.protocol=self.base/'protocol.json';r.freeze(self.protocol)
        self.root=self.base/'store';self.assignment=self.base/'assignment'
        self.rendered=r.ROOT/'outputs/manual-audit-intake-2026-11-11/TECHNICAL_FIXTURE/rendered'
        r.safe_prepare(self.protocol,self.rendered,REVIEWER,self.root,self.assignment)
        self.a=m.read(self.assignment/'ASSIGNMENT.json');self.aid=m.digest(self.assignment/'ASSIGNMENT.json')
        self.delivery=self.base/'delivery.json';self.returned=self.base/'returned.json'
        d=m.read(self.assignment/'DELIVERY_TEMPLATE.json');d.update(coordinator_registry_id=AUTHOR,delivered_utc=r.now().isoformat().replace('+00:00','Z'),prior_exposure_confirmed_by_coordinator={'before_this_audit':'none','details':'TECHNICAL_FIXTURE only'})
        p=m.read(self.assignment/'reviewer/cards.json')
        for c in p['cards']:
            refs=c['citation_readout']['references'];c.update(human_decision={'criteria':['uncertain']*3,'citation_sufficiency':['uncertain' if f['status']=='fragment_selected' else 'not_selected' if f['status']=='no_fragment_selected' else 'unreadable' for f in refs],'contradiction':'uncertain','contradiction_fragment_ids':[]},human_reason='TECHNICAL_FIXTURE, no real human decisions.',reviewer_registry_id=REVIEWER,reviewed_utc=r.now().isoformat().replace('+00:00','Z'),prior_exposure_declared={'before_this_audit':'none','details':'Fixture','saw_verifier_readout':True})
        self.write(self.delivery,d);self.write(self.returned,p)
    def write(self,p,value):p.write_text(json.dumps(value,ensure_ascii=False),encoding='utf-8')
    def request(self,action,**extra):
        return {'operation_id':str(uuid.uuid4()),'action':action,'author_registry_id':AUTHOR,'technical_reviewer_registry_id':TECH,'reason':'TECHNICAL_FIXTURE recovery exercise','expected_store_id':self.a['intake_store_id'],'expected_assignment_sha256':self.aid,**extra}
    def execute(self,req,fault=lambda _:None):
        p=self.base/(req['operation_id']+'.json');self.write(p,req)
        return r.execute(self.protocol,self.root,self.assignment,p,fault)
    def receive(self):return r.safe_receive(self.protocol,self.assignment,self.returned,self.delivery,self.root,str(uuid.uuid4()))
    def amendment(self,**changes):
        state=r.effective(self.root,self.assignment);d=copy.deepcopy(state['current_delivery']);d.update(changes)
        return self.request('amend_delivery',expected_parent_delivery_sha256=state['current_delivery_sha256'],corrected_delivery=d)
    def test_finalize_issue_only_missing_marker_and_no_delivery_claim(self):
        path=self.root/'issued'/(self.a['package_reviewer_key']+'.json');before=path.read_bytes();path.unlink()
        req=self.request('finalize_issue');result=self.execute(req)
        self.assertTrue(result['result']['issued_restored']);self.assertFalse(result['result']['delivery_claimed'])
        self.assertEqual(m.read(path),m.decode(before));self.assertTrue(self.execute(req)['replayed'])
    def test_missing_acceptance_commit_revalidated_and_restored(self):
        receipt=self.receive();marker=self.root/'accepted'/(self.aid+'.json');marker.unlink();src=self.root/'attempts'/receipt['attempt_id'];before={p.name:p.read_bytes() for p in src.iterdir() if p.is_file()}
        req=self.request('recover_attempt',source_attempt_id=receipt['attempt_id'],expected_source_inventory_sha256=r.inventory_sha(src));res=self.execute(req)
        self.assertTrue(res['result']['restored_original_commit']);m.verified_commit(self.root,marker,self.aid)
        self.assertEqual(before,{p.name:p.read_bytes() for p in src.iterdir() if p.is_file()})
    def test_partial_receipt_preserved_in_linked_recovery(self):
        receipt=self.receive();(self.root/'accepted'/(self.aid+'.json')).unlink();src=self.root/'attempts'/receipt['attempt_id'];(src/'MANIFEST.json').unlink();(src/'RECEIPT.json').write_bytes(b'{"partial":')
        req=self.request('recover_attempt',source_attempt_id=receipt['attempt_id'],expected_source_inventory_sha256=r.inventory_sha(src));res=self.execute(req)
        self.assertTrue(res['result']['registered']);self.assertEqual((src/'RECEIPT.json').read_bytes(),b'{"partial":')
        state=r.effective(self.root,self.assignment);self.assertTrue(state['original_receipt_time_unknown']);self.assertEqual(state['status'],'requires_manual_review')
    def test_terminal_rejection_never_promoted(self):
        bad=m.read(self.returned);bad['cards'][0]['human_reason']='';self.write(self.returned,bad);receipt=self.receive();self.assertFalse(receipt['validation_passed'])
        src=self.root/'attempts'/receipt['attempt_id']
        with self.assertRaisesRegex(ValueError,'terminal_rejection'):self.execute(self.request('recover_attempt',source_attempt_id=receipt['attempt_id'],expected_source_inventory_sha256=r.inventory_sha(src)))
    def test_append_correction_preserves_baseline_and_replays(self):
        self.receive();marker=self.root/'accepted'/(self.aid+'.json');marker_bytes=marker.read_bytes();base=r.accepted_base(self.root,self.aid)[2];original=(base/'delivery.json').read_bytes()
        req=self.amendment(prior_exposure_confirmed_by_coordinator={'before_this_audit':'some','details':'Corrected factual declaration, fixture'})
        self.execute(req);self.assertTrue(self.execute(req)['replayed']);state=r.effective(self.root,self.assignment)
        self.assertEqual(state['amendment_count'],1);self.assertTrue(state['current_formal_validation_passed']);self.assertEqual(marker.read_bytes(),marker_bytes);self.assertEqual((base/'delivery.json').read_bytes(),original)
    def test_factual_time_conflict_recorded_without_silent_validity(self):
        self.receive();self.execute(self.amendment(delivered_utc='2099-01-01T00:00:00Z'));state=r.effective(self.root,self.assignment)
        self.assertFalse(state['current_formal_validation_passed']);self.assertEqual(state['status'],'requires_manual_review');self.assertEqual(state['amendment_count'],1)
    def test_wrong_recipient_and_stale_parent_blocked(self):
        self.receive();req=self.amendment(coordinator_registry_id=TECH);stale=copy.deepcopy(req);stale['operation_id']=str(uuid.uuid4());self.execute(req)
        with self.assertRaisesRegex(ValueError,'stale_amendment_parent'):self.execute(stale)
        with self.assertRaisesRegex(ValueError,'immutable_delivery_field'):self.execute(self.amendment(recipient_registry_id=TECH))
    def test_plan_resume_after_target_publication(self):
        self.receive();req=self.amendment(coordinator_registry_id=TECH)
        def fault(name):
            if name.startswith('after:delivery-amendments/'):raise RuntimeError('injected_crash')
        with self.assertRaisesRegex(RuntimeError,'injected_crash'):self.execute(req,fault)
        self.execute(req);self.assertEqual(r.effective(self.root,self.assignment)['amendment_count'],1)
    def test_plan_source_drift_stops_resume(self):
        self.receive();req=self.amendment(coordinator_registry_id=TECH)
        with self.assertRaises(RuntimeError):self.execute(req,lambda n:(_ for _ in ()).throw(RuntimeError('stop')) if n=='plan_published' else None)
        (self.assignment/'reviewer/CARDS.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'observed_source_changed'):self.execute(req)
    def test_operation_id_reuse_with_new_reason_blocked(self):
        self.receive();req=self.amendment(coordinator_registry_id=TECH);self.execute(req);req['reason']='Another reason'
        with self.assertRaisesRegex(ValueError,'operation_id_reused'):self.execute(req)
    def test_legacy_lock_untouched(self):
        lock=self.root/'intake.lock';lock.write_text(str(uuid.uuid4()));before=lock.read_bytes()
        with self.assertRaisesRegex(RuntimeError,'legacy_or_unknown'):self.execute(self.request('finalize_issue'))
        self.assertEqual(lock.read_bytes(),before)
    def test_owned_process_death_recovered_without_age_rule(self):
        result=subprocess.run([sys.executable,__file__,'crash-lease',str(self.root)],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(result.returncode,91);self.assertEqual(r.lease.lock_status(self.root)['state'],'owned_dead')
        with r.lease.owned_lease(self.root,'fixture'):self.assertEqual(r.lease.lock_status(self.root)['state'],'owned_running')
        self.assertEqual(r.lease.lock_status(self.root)['state'],'owned_idle_barrier');self.assertEqual(len(list((self.root/'recovery/leases').glob('*.death-proof.json'))),1)
    def test_safe_receive_exact_retry_is_idempotent(self):
        op=str(uuid.uuid4());a=r.safe_receive(self.protocol,self.assignment,self.returned,self.delivery,self.root,op);b=r.safe_receive(self.protocol,self.assignment,self.returned,self.delivery,self.root,op)
        self.assertEqual(a['attempt_id'],b['attempt_id']);self.assertTrue(b['repeat_of_saved_attempt']);self.assertEqual(len(list((self.root/'accepted').iterdir())),1)
    def test_chain_tampering_detected(self):
        self.receive();self.execute(self.amendment(coordinator_registry_id=TECH));p=self.root/'delivery-amendments'/self.aid/'000001.json';e=m.read(p);e['errors']=[{'fake':True}];self.write(p,e)
        with self.assertRaisesRegex(ValueError,'journal_target_changed'):r.effective(self.root,self.assignment)
    def crash_receive(self,point):
        op=str(uuid.uuid4())
        def fail(name):
            if name==point:raise RuntimeError('injected_crash')
        with self.assertRaisesRegex(RuntimeError,'injected_crash'):r.safe_receive(self.protocol,self.assignment,self.returned,self.delivery,self.root,op,fail)
        source=self.root/'recovery/executions'/op
        return self.request('recover_execution',source_execution_id=op,expected_source_inventory_sha256=r.inventory_sha(source))
    def test_execution_snapshot_recovers_before_attempt_exists(self):
        req=self.crash_receive('input_snapshots_published');self.returned.write_bytes(b'changed external input')
        result=self.execute(req);self.assertTrue(result['result']['registered']);self.assertTrue(self.execute(req)['replayed'])
        self.assertTrue(r.effective(self.root,self.assignment)['original_receipt_time_unknown'])
    def test_execution_snapshot_recovers_partial_atomic_inputs(self):
        req=self.crash_receive('attempt_input:ASSIGNMENT.json');result=self.execute(req)
        self.assertTrue(result['result']['registered']);self.assertEqual(len(list((self.root/'attempts').iterdir())),2)
    def test_execution_conflicting_attempt_bytes_blocked(self):
        req=self.crash_receive('attempt_input:ASSIGNMENT.json');src=next((self.root/'attempts').iterdir());(src/'returned.json').write_bytes(b'corrupt')
        with self.assertRaisesRegex(ValueError,'execution_attempt_input_conflict'):self.execute(req)
    def test_completed_receipt_recovery_at_every_terminal_boundary(self):
        # Separate temp fixtures ensure each boundary is independently exercised.
        for point in ['receipt_published','attempt_manifest_published','accepted_marker_published','receive_finished']:
            with self.subTest(point=point):
                case=RecoveryTests();case.setUp()
                try:
                    req=case.crash_receive(point);result=case.execute(req)
                    state=r.effective(case.root,case.assignment);self.assertEqual(state['assignment_sha256'],case.aid)
                    self.assertEqual(len(list((case.root/'accepted').iterdir())),1)
                finally:case.doCleanups()
    def test_distinct_execution_inputs_block_selection(self):
        req=self.crash_receive('input_snapshots_published');d=m.read(self.delivery);d['coordinator_registry_id']=TECH;self.write(self.delivery,d);self.crash_receive('input_snapshots_published')
        with self.assertRaisesRegex(ValueError,'multiple_distinct_execution_inputs'):self.execute(req)
    def test_execution_terminal_rejection_not_promoted(self):
        d=m.read(self.returned);d['cards'][0]['human_reason']='';self.write(self.returned,d)
        req=self.crash_receive('attempt_manifest_published')
        with self.assertRaisesRegex(ValueError,'terminal_rejection'):self.execute(req)
    def test_exposure_downgrade_does_not_erase_history(self):
        self.receive();self.execute(self.amendment(prior_exposure_confirmed_by_coordinator={'before_this_audit':'unknown','details':'Uncertain, fixture'}))
        self.execute(self.amendment(prior_exposure_confirmed_by_coordinator={'before_this_audit':'none','details':'Later correction, fixture'}))
        state=r.effective(self.root,self.assignment);self.assertEqual(state['conservative_prior_exposure'],'unknown');self.assertTrue(state['exposure_history_requires_review'])
    def test_reader_does_not_present_old_marker_as_current_validity(self):
        op=str(uuid.uuid4());r.safe_receive(self.protocol,self.assignment,self.returned,self.delivery,self.root,op)
        self.execute(self.amendment(delivered_utc='2099-01-01T00:00:00Z'))
        result=r.safe_receive(self.protocol,self.assignment,self.returned,self.delivery,self.root,op)
        self.assertTrue(result['validation_passed']);self.assertTrue(result['receipt_is_historical']);self.assertFalse(result['effective_status']['current_formal_validation_passed'])
    def test_last_amendment_deletion_detected_by_journal(self):
        self.receive();self.execute(self.amendment(coordinator_registry_id=TECH));(self.root/'delivery-amendments'/self.aid/'000001.json').unlink()
        with self.assertRaisesRegex(ValueError,'committed_journal_target_missing'):r.effective(self.root,self.assignment)
    def test_receipt_disappearance_with_marker_blocks_reader(self):
        receipt=self.receive();(self.root/'attempts'/receipt['attempt_id']/'RECEIPT.json').unlink()
        with self.assertRaises((ValueError,OSError)):r.effective(self.root,self.assignment)
    def test_plan_checksum_tampering_blocks_resume(self):
        self.receive();req=self.amendment(coordinator_registry_id=TECH)
        with self.assertRaises(RuntimeError):self.execute(req,lambda n:(_ for _ in ()).throw(RuntimeError('stop')) if n=='plan_published' else None)
        p=self.root/'recovery/operations'/req['operation_id']/'PLAN.json';plan=m.read(p);plan['result']['amendment_sequence']=999;self.write(p,plan)
        with self.assertRaisesRegex(ValueError,'plan_content_checksum_mismatch'):self.execute(req)
    def test_adopted_module_restored_after_exception(self):
        oldsave=m.save;oldreserve=m.store_reservation
        with self.assertRaises(RuntimeError):
            with r.adopted_reservation(self.root):raise RuntimeError('injected')
        self.assertIs(m.save,oldsave);self.assertIs(m.store_reservation,oldreserve)
    def test_foreign_host_does_not_remove_lock(self):
        result=subprocess.run([sys.executable,__file__,'crash-lease',str(self.root)],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.assertEqual(result.returncode,91)
        before=(self.root/'intake.lock').read_bytes()
        with patch.object(r.lease,'machine_id',return_value='foreign'):
            self.assertEqual(r.lease.lock_status(self.root)['state'],'foreign_or_unknown_host')
            with self.assertRaises(ValueError):
                with r.lease.owned_lease(self.root,'fixture'):pass
        self.assertEqual((self.root/'intake.lock').read_bytes(),before)
    def test_process_query_failure_does_not_remove_lock(self):
        result=subprocess.run([sys.executable,__file__,'crash-lease',str(self.root)],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.assertEqual(result.returncode,91)
        before=(self.root/'intake.lock').read_bytes()
        with patch.object(r.lease,'process_state',side_effect=PermissionError('denied')):
            with self.assertRaises(PermissionError):
                with r.lease.owned_lease(self.root,'fixture'):pass
        self.assertEqual((self.root/'intake.lock').read_bytes(),before)
    def test_mutex_blocks_second_process(self):
        with r.lease.owned_lease(self.root,'fixture'):
            result=subprocess.run([sys.executable,__file__,'probe-lease',str(self.root)],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.assertEqual(result.returncode,92);self.assertIn('mutex_busy',result.stdout.decode())
    def test_hard_process_exit_at_receive_boundaries(self):
        points=['input_snapshots_published','attempt_input:ASSIGNMENT.json','attempt_input:delivery.json','attempt_input:returned.json','receipt_published','attempt_manifest_published','accepted_marker_published','receive_finished']
        for point in points:
            with self.subTest(point=point):
                case=RecoveryTests();case.setUp()
                try:
                    op=str(uuid.uuid4());args=[sys.executable,__file__,'crash-receive',str(case.protocol),str(case.assignment),str(case.returned),str(case.delivery),str(case.root),op,point]
                    done=subprocess.run(args,capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.assertEqual(done.returncode,93,done.stderr.decode(errors='replace'))
                    self.assertEqual(r.lease.lock_status(case.root)['state'],'owned_dead')
                    source=case.root/'recovery/executions'/op
                    req=case.request('recover_execution',source_execution_id=op,expected_source_inventory_sha256=r.inventory_sha(source))
                    case.execute(req);self.assertTrue(case.execute(req)['replayed'])
                    state=r.read_status(case.protocol,case.root,case.assignment);self.assertEqual(state['assignment_sha256'],case.aid)
                    self.assertEqual(len(list((case.root/'accepted').iterdir())),1)
                finally:case.doCleanups()
    def test_hard_process_exit_at_recovery_boundaries(self):
        for point in ['plan_published','after_amendment','result_published']:
            with self.subTest(point=point):
                case=RecoveryTests();case.setUp()
                try:
                    case.receive();req=case.amendment(coordinator_registry_id=TECH);path=case.base/'request.json';case.write(path,req)
                    done=subprocess.run([sys.executable,__file__,'crash-recovery',str(case.protocol),str(case.root),str(case.assignment),str(path),point],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
                    self.assertEqual(done.returncode,94,done.stderr.decode(errors='replace'));case.execute(req)
                    self.assertEqual(r.read_status(case.protocol,case.root,case.assignment)['amendment_count'],1)
                finally:case.doCleanups()
    def test_pending_amendment_visible_as_manual_before_result(self):
        self.receive();req=self.amendment(coordinator_registry_id=TECH)
        def fault(n):
            if n.startswith('after:delivery-amendments/'):raise RuntimeError('stop')
        with self.assertRaises(RuntimeError):self.execute(req,fault)
        state=r.read_status(self.protocol,self.root,self.assignment);self.assertIn(req['operation_id'],state['pending_recovery_operation_ids']);self.assertEqual(state['status'],'requires_manual_review')
    def test_reader_is_read_only_and_blocked_by_live_lease(self):
        self.receive();before={p.relative_to(self.root).as_posix():m.digest(p) for p in self.root.rglob('*') if p.is_file()}
        r.read_status(self.protocol,self.root,self.assignment)
        self.assertEqual(before,{p.relative_to(self.root).as_posix():m.digest(p) for p in self.root.rglob('*') if p.is_file()})
        with r.lease.owned_lease(self.root,'fixture'):
            with self.assertRaisesRegex(RuntimeError,'read_blocked_by_lock'):r.read_status(self.protocol,self.root,self.assignment)
    def test_coordinator_corrected_to_reviewer_remains_invalid(self):
        self.receive();self.execute(self.amendment(coordinator_registry_id=REVIEWER));state=r.read_status(self.protocol,self.root,self.assignment)
        self.assertFalse(state['current_formal_validation_passed'])
    def test_filesystem_failure_has_no_copy_fallback(self):
        target=self.base/'unsupported-store'
        with patch.object(r.lease,'filesystem',side_effect=RuntimeError('unsupported')):
            with self.assertRaisesRegex(RuntimeError,'unsupported'):
                with r.lease.owned_lease(target,'fixture'):pass
        self.assertFalse((target/'STORE.json').exists())
    def test_incomplete_execution_manifest_stays_manual(self):
        for point in ['execution_input:returned.json','execution_input:delivery.json','execution_input:ASSIGNMENT.json']:
            with self.subTest(point=point):
                case=RecoveryTests();case.setUp()
                try:
                    req=case.crash_receive(point)
                    with self.assertRaises(OSError):case.execute(req)
                    self.assertFalse((case.root/'accepted'/(case.aid+'.json')).exists())
                finally:case.doCleanups()
    def test_dead_lock_retirement_resumes_after_death_proof(self):
        result=subprocess.run([sys.executable,__file__,'crash-lease',str(self.root)],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.assertEqual(result.returncode,91)
        original=r.lease.publish
        def interrupted(path,data):
            result=original(path,data)
            if str(path).endswith('.death-proof.json'):raise RuntimeError('retirement_interrupted')
            return result
        with patch.object(r.lease,'publish',side_effect=interrupted):
            with self.assertRaisesRegex(RuntimeError,'retirement_interrupted'):
                with r.lease.owned_lease(self.root,'fixture'):pass
        with r.lease.owned_lease(self.root,'fixture'):pass
        self.assertEqual(len(list((self.root/'recovery/leases').glob('*.death-proof.json'))),1)
    def test_real_abandoned_kernel_mutex_is_recorded(self):
        k=r.lease.kernel();h=k.CreateMutexW(None,False,'Global\\LAT_AI_AUDIT_'+self.a['intake_store_id'])
        self.assertTrue(h)
        try:
            result=subprocess.run([sys.executable,__file__,'crash-lease',str(self.root)],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.assertEqual(result.returncode,91)
            with r.lease.owned_lease(self.root,'fixture'):
                status=r.lease.lock_status(self.root);self.assertTrue(status['owner']['mutex_abandoned'])
        finally:k.CloseHandle(h)
    def test_committed_corruption_blocks_new_mutation(self):
        receipt=self.receive();(self.root/'attempts'/receipt['attempt_id']/'RECEIPT.json').unlink()
        with self.assertRaises((ValueError,OSError)):self.execute(self.request('finalize_issue'))
        self.assertFalse((self.root/'recovery/operations').exists())
    def test_stale_request_cannot_ignore_new_return_snapshot(self):
        req=self.crash_receive('input_snapshots_published')
        with self.assertRaises(RuntimeError):self.execute(req,lambda n:(_ for _ in ()).throw(RuntimeError('stop')) if n=='plan_published' else None)
        d=m.read(self.delivery);d['coordinator_registry_id']=TECH;self.write(self.delivery,d);self.crash_receive('input_snapshots_published')
        with self.assertRaisesRegex(ValueError,'assignment_execution_inventory_changed'):self.execute(req)
    def test_v1_v2_receive_semantics_match_on_24_input_variants(self):
        original=m.read(self.returned);delivery=m.read(self.delivery);variants=[('valid_uncertain',original,delivery)]
        for field,value in [('human_reason',''),('human_reason',False),('reviewer_registry_id',TECH),('reviewed_utc','2000-01-01T00:00:00Z'),('reviewed_utc','2099-01-01T00:00:00Z'),('human_decision',None),('student_answer','changed'),('prior_exposure_declared',None)]:
            payload=copy.deepcopy(original);payload['cards'][0][field]=value;variants.append((field+repr(value),payload,delivery))
        for field,value in [('assignment_sha256','0'*64),('recipient_registry_id',TECH),('coordinator_registry_id',REVIEWER),('delivered_utc','2099-01-01T00:00:00Z'),('delivered_utc','2000-01-01T00:00:00Z'),('files_seen_sha256',{}),('prior_exposure_confirmed_by_coordinator',None)]:
            d=copy.deepcopy(delivery);d[field]=value;variants.append((field+repr(value),original,d))
        for raw in [b'{"cards":[],"cards":[]}',b'{"cards":NaN}',b'{"cards":9007199254740992}',br'{"cards":"\uD800"}',b'null',b'[]',b'{',b'{}']:
            variants.append(('raw_'+repr(raw),raw,delivery))
        self.assertEqual(len(variants),24)
        fixed=r.now()+timedelta(minutes=1)
        for index,(name,payload,d) in enumerate(variants):
            with self.subTest(input=name):
                # TEST ONLY: two sequential isolated copies let identical assignment/input bytes
                # exercise the legacy writer and new writer. Never clone a live campaign store.
                oldroot=self.base/f'v1-{index}';newroot=self.base/f'v2-{index}'
                # Copy only the legacy baseline into disposable stores, without v2 lease state.
                ignore=lambda source,names:set(names)&{'recovery','intake.lock'} if Path(source)==self.root else set()
                shutil.copytree(self.root,oldroot,ignore=ignore);shutil.copytree(self.root,newroot,ignore=ignore)
                self.returned.write_bytes(payload if isinstance(payload,bytes) else r.binary(payload));self.write(self.delivery,d)
                with patch.object(m,'utcnow',return_value=fixed),patch.object(r,'now',return_value=fixed):
                    old=m.receive(r.INTAKE,self.assignment,self.returned,self.delivery,oldroot)
                    new=r.safe_receive(self.protocol,self.assignment,self.returned,self.delivery,newroot,str(uuid.uuid4()))
                self.assertEqual(old,{k:v for k,v in new.items() if k not in ['effective_status','receipt_is_historical']})
                self.assertEqual((oldroot/'accepted'/(self.aid+'.json')).exists(),(newroot/'accepted'/(self.aid+'.json')).exists())
    def test_idle_barrier_blocks_actual_legacy_receive(self):
        before=r.inventory(self.root);self.assertEqual(r.lease.lock_status(self.root)['state'],'owned_idle_barrier')
        with self.assertRaises(FileExistsError):m.receive(r.INTAKE,self.assignment,self.returned,self.delivery,self.root)
        self.assertEqual(r.inventory(self.root),before)
        result=self.receive();self.assertTrue(result['validation_passed']);self.assertEqual(r.lease.lock_status(self.root)['state'],'owned_idle_barrier')
    def test_terminated_process_with_retained_handle_is_not_alive(self):
        child=subprocess.Popen([sys.executable,__file__,'crash-lease',str(self.root)],stdout=subprocess.PIPE,stderr=subprocess.PIPE,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        self.addCleanup(child.stdout.close);self.addCleanup(child.stderr.close)
        self.assertEqual(child.wait(timeout=20),91)
        self.assertEqual(r.lease.process_state(child.pid)['state'],'terminated')
        self.assertEqual(r.lease.lock_status(self.root)['state'],'owned_dead')
    def test_double_hard_crash_receive_then_linked_recovery(self):
        op=str(uuid.uuid4())
        args=[sys.executable,__file__,'crash-receive',str(self.protocol),str(self.assignment),str(self.returned),str(self.delivery),str(self.root),op,'attempt_input:ASSIGNMENT.json']
        done=subprocess.run(args,capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.assertEqual(done.returncode,93)
        source=self.root/'recovery/executions'/op;req=self.request('recover_execution',source_execution_id=op,expected_source_inventory_sha256=r.inventory_sha(source));path=self.base/'double-crash.json';self.write(path,req)
        done=subprocess.run([sys.executable,__file__,'crash-recovery',str(self.protocol),str(self.root),str(self.assignment),str(path),'after_linked_input'],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.assertEqual(done.returncode,94,done.stderr.decode(errors='replace'))
        self.execute(req);state=r.read_status(self.protocol,self.root,self.assignment);self.assertTrue(state['original_receipt_time_unknown'])
        self.assertEqual(len(list((self.root/'accepted').iterdir())),1);self.assertEqual(len(list((self.root/'recovery/leases').glob('*.death-proof.json'))),2)
    def test_abandoned_read_does_not_retire_lock(self):
        self.receive();done=subprocess.run([sys.executable,__file__,'crash-lease',str(self.root)],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.assertEqual(done.returncode,91)
        before={p.relative_to(self.root).as_posix():m.digest(p) for p in self.root.rglob('*') if p.is_file()}
        state=r.read_status(self.protocol,self.root,self.assignment);self.assertEqual(state['assignment_sha256'],self.aid)
        self.assertEqual(before,{p.relative_to(self.root).as_posix():m.digest(p) for p in self.root.rglob('*') if p.is_file()})
        self.assertEqual(r.lease.lock_status(self.root)['state'],'owned_dead')
    def test_idle_barrier_blocks_actual_legacy_prepare(self):
        before=r.inventory(self.root)
        with self.assertRaises(FileExistsError):m.prepare(r.INTAKE,self.rendered,str(uuid.uuid4()),self.root,self.base/'legacy-assignment')
        self.assertEqual(r.inventory(self.root),before);self.assertFalse((self.base/'legacy-assignment').exists())
    def test_missing_initialized_barrier_is_incident_not_recreated(self):
        (self.root/'intake.lock').unlink();self.assertEqual(r.lease.lock_status(self.root)['state'],'missing_initialized_barrier')
        with self.assertRaisesRegex(RuntimeError,'missing_initialized_barrier'):self.receive()
        self.assertFalse((self.root/'intake.lock').exists())
        with self.assertRaisesRegex(RuntimeError,'missing_initialized_barrier'):r.read_status(self.protocol,self.root,self.assignment)
    def test_exchange_sharing_violation_stops_once_and_retains_stage(self):
        before=(self.root/'intake.lock').read_bytes()
        with patch.object(r.lease.os,'replace',side_effect=PermissionError('sharing_violation')) as replace:
            with self.assertRaises(PermissionError):self.receive()
            self.assertEqual(replace.call_count,1)
        self.assertEqual((self.root/'intake.lock').read_bytes(),before)
        stages=list(self.root.glob('.intake.lock.next-*'));self.assertEqual(len(stages),1)
        self.assertEqual(r.lease.exchange_stage_status(self.root,stages[0])['kind'],'owned_lease_exchange_stage_preserved')
        self.assertTrue(self.receive()['validation_passed']);self.assertTrue(stages[0].exists())
    def test_hard_crash_before_barrier_exchange_keeps_store_usable(self):
        done=subprocess.run([sys.executable,__file__,'crash-exchange',str(self.root)],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.assertEqual(done.returncode,97,done.stderr.decode(errors='replace'))
        self.assertEqual(r.lease.lock_status(self.root)['state'],'owned_idle_barrier')
        stage=next(self.root.glob('.intake.lock.next-*'));self.assertIsNotNone(r.lease.exchange_stage_status(self.root,stage))
        self.assertTrue(self.receive()['validation_passed']);self.assertTrue(stage.exists())

if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='crash-exchange':
        r.lease.os.replace=lambda *_:os._exit(97)
        with r.lease.owned_lease(sys.argv[2],'crash-before-exchange'):pass
        sys.exit(98)
    if len(sys.argv)>1 and sys.argv[1]=='crash-receive':
        point=sys.argv[8]
        r.safe_receive(*sys.argv[2:8],_fault=lambda n:os._exit(93) if n==point else None);sys.exit(95)
    if len(sys.argv)>1 and sys.argv[1]=='crash-recovery':
        point=sys.argv[6]
        r.execute(*sys.argv[2:6],_fault=lambda n:os._exit(94) if n==point or (point=='after_amendment' and n.startswith('after:delivery-amendments/')) or (point=='after_linked_input' and n.startswith('after:attempts/') and n.endswith('/ASSIGNMENT.json')) else None);sys.exit(96)
    if len(sys.argv)>1 and sys.argv[1]=='crash-lease':
        with r.lease.owned_lease(sys.argv[2],'test-process-death'):os._exit(91)
    if len(sys.argv)>1 and sys.argv[1]=='probe-lease':
        try:
            with r.lease.owned_lease(sys.argv[2],'test-contention'):pass
        except RuntimeError as e:print(e);sys.exit(92)
        sys.exit(0)
    unittest.main()
