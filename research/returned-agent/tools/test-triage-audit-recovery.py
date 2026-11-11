import importlib.util,unittest,uuid
from unittest.mock import patch
from pathlib import Path

def load(name,file):
    spec=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
t=load('triage_test_module','triage-audit-recovery.py')
fixture_module=load('triage_fixture_module','test-recover-audit-store.py')

class TriageTests(unittest.TestCase):
    def setUp(self):
        self.f=fixture_module.RecoveryTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
    def snapshot(self):return {p.relative_to(self.f.root).as_posix():t.r.digest(p) for p in self.f.root.rglob('*') if p.is_file()}
    def test_read_only_layout_report_has_no_quality_claim(self):
        before=self.snapshot();v=t.store_view(self.f.protocol,self.f.root)
        self.assertEqual(before,self.snapshot());self.assertFalse(v['independent_gold']);self.assertIn('effective_status_not_evaluated',v)
    def test_unsigned_draft_cannot_execute_and_store_unchanged(self):
        before=self.snapshot();target=self.f.base/'unsigned.json';t.draft(self.f.protocol,self.f.root,self.f.assignment,'finalize_issue',target)
        req=t.r.read(target);self.assertIsNone(req['author_registry_id']);self.assertIsNone(req['reason']);self.assertEqual(before,self.snapshot())
        with self.assertRaises(ValueError):self.f.execute(req)
        self.assertEqual(before,self.snapshot())
    def test_output_inside_store_or_assignment_rejected(self):
        for target in [self.f.root/'diagnostic',self.f.assignment/'reviewer/diagnostic']:
            with self.assertRaisesRegex(ValueError,'outside_store_and_assignment'):t.inspect_to(self.f.protocol,self.f.root,target,self.f.assignment)
            self.assertFalse(target.exists())
    def test_orphan_and_partial_execution_are_reported_without_repair(self):
        (self.f.root/'unexpected.txt').write_text('fixture');self.f.crash_receive('execution_input:returned.json');before=self.snapshot()
        view=t.store_view(self.f.protocol,self.f.root)
        self.assertEqual(before,self.snapshot());self.assertTrue(any(x['reason']=='unexpected_root_entry_preserved' for x in view['issues']));self.assertEqual(view['executions'][0]['status'],'partial_or_inconsistent_preserved')
    def test_reservation_without_assignment_is_visible(self):
        def fail(name):
            if 'issuance-reservations' in name:raise RuntimeError('fixture')
        with self.assertRaises(RuntimeError):t.r.safe_prepare(self.f.protocol,self.f.rendered,str(uuid.uuid4()),self.f.root,self.f.base/'missing-assignment',fail)
        view=t.store_view(self.f.protocol,self.f.root)
        self.assertTrue(any(not x['issued_marker_present'] for x in view['reservations']));self.assertFalse((self.f.base/'missing-assignment').exists())
    def test_busy_store_is_not_scanned(self):
        with t.r.lease.owned_lease(self.f.root,'fixture'):
            view=t.store_view(self.f.protocol,self.f.root)
            self.assertFalse(view['data_scan_performed']);self.assertEqual(view['attempts'],[])
    def test_amendment_draft_binds_current_parent_and_preserves_exposure(self):
        self.f.receive();self.f.execute(self.f.amendment(prior_exposure_confirmed_by_coordinator={'before_this_audit':'unknown','details':'fixture'}))
        path=self.f.base/'amendment-draft.json';t.draft(self.f.protocol,self.f.root,self.f.assignment,'amend_delivery',path);d=t.r.read(path)
        state=t.r.read_status(self.f.protocol,self.f.root,self.f.assignment);self.assertEqual(d['expected_parent_delivery_sha256'],state['current_delivery_sha256']);self.assertEqual(d['corrected_delivery'],state['current_delivery'])
    def test_export_complete_and_refuses_overwrite(self):
        self.f.receive();before=self.snapshot();out=self.f.base/'inspection';t.inspect_to(self.f.protocol,self.f.root,out,self.f.assignment)
        t.r.m.verify_hashes(out,t.r.read(out/'MANIFEST.json'));self.assertEqual(before,self.snapshot())
        with self.assertRaises(FileExistsError):t.inspect_to(self.f.protocol,self.f.root,out,self.f.assignment)
    def test_recovery_draft_uses_saved_inventory(self):
        req=self.f.crash_receive('input_snapshots_published');out=self.f.base/'execution-draft.json'
        t.draft(self.f.protocol,self.f.root,self.f.assignment,'recover_execution',out,req['source_execution_id'])
        d=t.r.read(out);self.assertEqual(d['expected_source_inventory_sha256'],req['expected_source_inventory_sha256'])
    def test_missing_barrier_reported_without_repair(self):
        (self.f.root/'intake.lock').unlink();v=t.store_view(self.f.protocol,self.f.root)
        self.assertEqual(v['lock']['state'],'missing_initialized_barrier');self.assertFalse(v['data_scan_performed']);self.assertFalse((self.f.root/'intake.lock').exists())
    def test_own_exchange_stage_recognized_and_preserved(self):
        with patch.object(t.r.lease.os,'replace',side_effect=PermissionError('fixture')):
            with self.assertRaises(PermissionError):t.r.safe_receive(self.f.protocol,self.f.assignment,self.f.returned,self.f.delivery,self.f.root,str(uuid.uuid4()))
        before=self.snapshot();v=t.store_view(self.f.protocol,self.f.root)
        self.assertEqual(len(v['preserved_lease_stages']),1);self.assertEqual(before,self.snapshot());self.assertFalse(any(x['reason']=='unexpected_root_entry_preserved' for x in v['issues']))
    def test_preserved_partial_source_is_linked_to_completed_recovery(self):
        req=self.f.crash_receive('receipt_published');self.f.execute(req);v=t.store_view(self.f.protocol,self.f.root,self.f.assignment)
        self.assertTrue(any(x.get('completed_by_recovery_operation')==req['operation_id'] for x in v['attempts']))
        self.assertEqual(v['executions'][0]['completed_by_recovery_operation'],req['operation_id'])
        self.assertFalse(any(x['reason']=='execution_has_snapshots_without_result' for x in v['issues']))

if __name__=='__main__':unittest.main()
