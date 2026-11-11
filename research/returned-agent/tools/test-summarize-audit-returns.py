import importlib.util,tempfile,unittest,uuid,copy,subprocess
from pathlib import Path

def load(name,file):
    s=importlib.util.spec_from_file_location(name,Path(__file__).with_name(file));v=importlib.util.module_from_spec(s);s.loader.exec_module(v);return v
s=load('return_summary_test','summarize-audit-returns.py');fm=load('return_summary_fixture','test-recover-audit-store.py')

class SummaryTests(unittest.TestCase):
    def setUp(self):
        self.f=fm.RecoveryTests();self.f.setUp();self.addCleanup(self.f.doCleanups)
        self.protocol=self.f.base/'summary-protocol.json';s.freeze(self.protocol)
        self.index=self.f.base/'index.json';self.entries=[];self.add_assignment(self.f.assignment)
    def add_assignment(self,path):
        self.entries.append({'path':str(path),'assignment_sha256':s.r.digest(path/'ASSIGNMENT.json')})
        self.f.write(self.index,{'store_id':self.f.a['intake_store_id'],'mode':'TECHNICAL_FIXTURE','assignments':self.entries})
    def second(self,change=None,rendered=None):
        r=s.r;reviewer=str(uuid.uuid4());folder=self.f.base/('assignment-'+reviewer)
        r.safe_prepare(self.f.protocol,rendered or self.f.rendered,reviewer,self.f.root,folder)
        d=r.read(folder/'DELIVERY_TEMPLATE.json');d.update(coordinator_registry_id=fm.AUTHOR,delivered_utc=r.now().isoformat().replace('+00:00','Z'),prior_exposure_confirmed_by_coordinator={'before_this_audit':'none','details':'TECHNICAL_FIXTURE'})
        returned=r.read(folder/'reviewer/cards.json');old=r.read(self.f.returned)['cards'][0]
        for c in returned['cards']:
            c.update({k:copy.deepcopy(old[k]) for k in r.m.EDITABLE});c['reviewer_registry_id']=reviewer;c['reviewed_utc']=r.now().isoformat().replace('+00:00','Z')
            if change:change(c)
        dp=self.f.base/(reviewer+'-delivery.json');rp=self.f.base/(reviewer+'-return.json');self.f.write(dp,d);self.f.write(rp,returned)
        r.safe_receive(self.f.protocol,folder,rp,dp,self.f.root,str(uuid.uuid4()));self.add_assignment(folder);return folder
    def build(self):return s.summarize(self.protocol,self.f.root,self.index)
    def snapshot(self):return {str(p):s.r.digest(p) for p in self.f.root.rglob('*') if p.is_file()}
    def test_missing_return_is_explicit(self):
        v=self.build();self.assertEqual(v['counts']['without_registered_return'],1);self.assertEqual(v['groups'][0]['missing_return_count'],1)
    def test_agreement_remains_manual_and_no_sources_change(self):
        self.f.receive();self.second();before=self.snapshot();v=self.build()
        self.assertEqual(before,self.snapshot());self.assertEqual(v['groups'][0]['definite_free_fields_status'],'not_fully_comparable');self.assertIn('uncertain_human_decision',v['groups'][0]['manual_review_reasons']);self.assertFalse(v['independent_gold'])
    def test_different_human_decisions_preserved(self):
        payload=s.r.read(self.f.returned);payload['cards'][0]['human_decision']['criteria']=['met','not_met','met'];self.f.write(self.f.returned,payload)
        self.f.receive();self.second(lambda c:c['human_decision'].update(criteria=['not_met','not_met','met']))
        v=self.build();g=v['groups'][0];self.assertIn('different_criteria',g['manual_review_reasons']);self.assertEqual(g['definite_free_fields_status'],'has_differences');self.assertEqual(len(g['returns']),2);self.assertIsNone(g['automatic_resolution'])
    def test_current_amendment_excludes_stale_baseline(self):
        self.f.receive();self.second();self.f.execute(self.f.amendment(delivered_utc='2099-01-01T00:00:00Z'))
        v=self.build();self.assertEqual(v['counts']['excluded_assignments'],1);self.assertEqual(v['groups'][0]['eligible_return_count'],1)
    def test_exposure_history_not_cleared_by_later_none(self):
        self.f.receive();self.second()
        self.f.execute(self.f.amendment(prior_exposure_confirmed_by_coordinator={'before_this_audit':'some','details':'fixture'}))
        self.f.execute(self.f.amendment(prior_exposure_confirmed_by_coordinator={'before_this_audit':'none','details':'fixture later'}))
        v=self.build();self.assertEqual(v['counts']['excluded_assignments'],1);self.assertEqual(v['counts']['exclusions_by_reason']['prior_exposure_history_requires_review'],1)
    def test_duplicate_assignment_index_rejected(self):
        self.entries.append(self.entries[0]);self.f.write(self.index,{'store_id':self.f.a['intake_store_id'],'mode':'TECHNICAL_FIXTURE','assignments':self.entries})
        with self.assertRaisesRegex(ValueError,'duplicate_index_assignment'):self.build()
    def test_changed_index_hash_rejected(self):
        self.entries[0]['assignment_sha256']='0'*64;self.f.write(self.index,{'store_id':self.f.a['intake_store_id'],'mode':'TECHNICAL_FIXTURE','assignments':self.entries})
        with self.assertRaisesRegex(ValueError,'indexed_assignment_changed'):self.build()
    def test_corrupt_registered_receipt_stops_whole_export(self):
        receipt=self.f.receive();(self.f.root/'attempts'/receipt['attempt_id']/'RECEIPT.json').write_text('{}')
        with self.assertRaises(ValueError):self.build()
    def test_busy_store_stops(self):
        with s.r.lease.owned_lease(self.f.root,'fixture'):
            with self.assertRaisesRegex(RuntimeError,'summary_blocked_by_lock'):self.build()
    def test_export_no_overwrite_and_no_store_writes(self):
        self.f.receive();before=self.snapshot();out=self.f.base/'summary-output';s.export(self.protocol,self.f.root,self.index,out)
        self.assertEqual(before,self.snapshot());s.r.m.verify_hashes(out,s.r.read(out/'MANIFEST.json'))
        with self.assertRaises(FileExistsError):s.export(self.protocol,self.f.root,self.index,out)
        with self.assertRaisesRegex(ValueError,'inside_store'):s.export(self.protocol,self.f.root,self.index,self.f.root/'output')
    def rendered_fixture(self,ids):
        r=s.r;base=self.f.base/('render-'+str(uuid.uuid4()));source=base/'source';(source/'reviewer').mkdir(parents=True)
        old=r.read(self.f.rendered/'reviewer/cards.json')['cards'][0];cards=[]
        for identity in ids:
            c={k:copy.deepcopy(v) for k,v in old.items() if k!='citation_readout'};c['audit_id']=identity;cards.append(c)
        self.f.write(source/'reviewer/cards.json',{'phase':'POST-LABEL TECHNICAL_FIXTURE summary tests only','cards':cards});(source/'reviewer/READ_FIRST.txt').write_text('TECHNICAL_FIXTURE only')
        self.f.write(source/'PRIVATE_COORDINATOR.json',{'selection':[{'audit_id':i,'source_id':'fixture-'+str(n),'stratum':'fixture'} for n,i in enumerate(ids)],'protocol_sha256':'technical-fixture'})
        self.f.write(source/'MANIFEST.json',{n:r.digest(source/n) for n in ['reviewer/cards.json','reviewer/READ_FIRST.txt','PRIVATE_COORDINATOR.json']})
        out=base/'rendered';done=subprocess.run([str(r.ROOT/'work/lat-ai-runtime/node/node.exe'),str(r.ROOT/'tools/render-signal-review-cards.mjs'),'render',str(r.m.PRESENTATION),str(source),str(out)],capture_output=True,timeout=20,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));self.assertEqual(done.returncode,0,done.stderr.decode(errors='replace'));return out
    def test_different_render_batches_never_merge_even_same_audit_id_and_text(self):
        self.f.receive();identity=s.r.read(self.f.returned)['cards'][0]['audit_id'];other=self.rendered_fixture([identity]);self.second(rendered=other)
        groups=self.build()['groups'];self.assertEqual(len(groups),2);self.assertEqual({g['audit_id'] for g in groups},{identity});self.assertTrue(all(g['eligible_return_count']==1 for g in groups))
    def test_identical_text_with_distinct_ids_stays_distinct(self):
        rendered=self.rendered_fixture([uuid.uuid4().hex,uuid.uuid4().hex]);self.second(rendered=rendered);self.second(rendered=rendered)
        result=self.build();groups=[g for g in result['groups'] if g['returns']];self.assertEqual(len(groups),2);self.assertEqual(len({g['student_answer'] for g in groups}),1);self.assertTrue(all(g['eligible_return_count']==2 for g in groups));self.assertTrue(result['same_text_separate_records'])
    def test_contradiction_evidence_order_is_not_false_disagreement(self):
        payload=s.r.read(self.f.returned);payload['cards'][0]['human_decision'].update(contradiction='present',contradiction_fragment_ids=[0,1]);self.f.write(self.f.returned,payload);self.f.receive()
        self.second(lambda c:c['human_decision'].update(contradiction='present',contradiction_fragment_ids=[1,0]))
        g=self.build()['groups'][0];self.assertNotIn('different_contradiction_fragment_ids',g['manual_review_reasons']);self.assertEqual(g['contradiction_evidence_relation'],'same_set')
    def test_three_reviewers_and_reordered_index_have_identical_summary(self):
        self.f.receive();self.second();self.second();first=s.r.binary(self.build())
        self.entries.reverse();self.f.write(self.index,{'store_id':self.f.a['intake_store_id'],'mode':'TECHNICAL_FIXTURE','assignments':self.entries})
        self.assertEqual(first,s.r.binary(self.build()));self.assertEqual(first,s.r.binary(self.build()))
    def test_schema_forced_fields_are_not_equality_evidence(self):
        self.f.receive();self.second();g=self.build()['groups'][0]
        fields=[x for x in g['field_comparisons'] if x['field']=='citation_sufficiency'];self.assertEqual([x['status'] for x in fields[:2]],['schema_forced_not_compared']*2)
        self.assertEqual([x['status'] for x in g['field_comparisons'] if x['field']=='criteria'],['all_uncertain']*3)
    def test_unindexed_issuance_is_listed_without_reading_assignment(self):
        r=s.r;folder=self.f.base/'unindexed';r.safe_prepare(self.f.protocol,self.f.rendered,str(uuid.uuid4()),self.f.root,folder);(folder/'MANIFEST.json').write_text('broken fixture outside explicit index')
        result=self.build();self.assertEqual(result['counts']['issued_not_in_index'],1);self.assertTrue(result['issued_not_in_index'][0]['content_not_read'])
    def test_empty_index_rejected(self):
        self.f.write(self.index,{'store_id':self.f.a['intake_store_id'],'mode':'TECHNICAL_FIXTURE','assignments':[]})
        with self.assertRaisesRegex(ValueError,'nonempty_assignment_index'):self.build()
    def test_same_identity_conflicting_immutable_payload_rejected(self):
        card=s.r.read(self.f.returned)['cards'][0];groups={};s.case_group(groups,self.f.a,card,{},'TECHNICAL_FIXTURE')
        card['student_answer']='different content'
        with self.assertRaisesRegex(ValueError,'different_immutable_content'):s.case_group(groups,self.f.a,card,{},'TECHNICAL_FIXTURE')
    def test_partial_evidence_overlap_is_explicit(self):
        payload=s.r.read(self.f.returned);payload['cards'][0]['human_decision'].update(contradiction='present',contradiction_fragment_ids=[0,1]);self.f.write(self.f.returned,payload);self.f.receive();self.second(lambda c:c['human_decision'].update(contradiction='present',contradiction_fragment_ids=[1]))
        self.assertEqual(self.build()['groups'][0]['contradiction_evidence_relation'],'partial_overlap')
    def test_fixture_cannot_be_declared_real_human_return(self):
        index=s.r.read(self.index);index['mode']='DECLARED_POST_LABEL_HUMAN_RETURN';self.f.write(self.index,index)
        with self.assertRaisesRegex(ValueError,'fixture_cannot'):self.build()
    def test_export_verification_detects_later_amendment_without_rewriting(self):
        self.f.receive();out=self.f.base/'snapshot';s.export(self.protocol,self.f.root,self.index,out);before={p.name:s.r.digest(p) for p in out.iterdir()}
        self.assertTrue(s.verify_export(self.protocol,self.f.root,out)['current_snapshot_matches'])
        self.f.execute(self.f.amendment(coordinator_registry_id=fm.TECH))
        self.assertFalse(s.verify_export(self.protocol,self.f.root,out)['current_snapshot_matches']);self.assertEqual(before,{p.name:s.r.digest(p) for p in out.iterdir()})
    def test_unregistered_receipt_not_silently_counted(self):
        self.f.receive();(self.f.root/'accepted'/(self.f.aid+'.json')).unlink()
        v=self.build();self.assertEqual(v['counts']['without_registered_return'],1);self.assertEqual(v['groups'][0]['eligible_return_count'],0)
    def test_corrupted_export_manifest_stops_reader(self):
        out=self.f.base/'export';s.export(self.protocol,self.f.root,self.index,out);(out/'SUMMARY.json').write_text('{}')
        with self.assertRaises(ValueError):s.verify_export(self.protocol,self.f.root,out)
    def test_cli_distinguishes_invalid_stale_and_corrupt(self):
        import sys
        self.f.receive();out=self.f.base/'cli-summary';s.export(self.protocol,self.f.root,self.index,out)
        def call(args):
            return subprocess.run([sys.executable,str(Path(s.__file__)),*map(str,args)],capture_output=True,text=True,encoding='utf-8',timeout=15,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        args=['verify-export',self.protocol,self.f.root,out];self.assertEqual(call(args).returncode,0)
        self.f.execute(self.f.amendment(coordinator_registry_id=fm.TECH));self.assertEqual(call(args).returncode,3)
        (out/'SUMMARY.json').write_text('{}');self.assertEqual(call(args).returncode,4)
        empty=self.f.base/'empty-index.json';self.f.write(empty,{'store_id':self.f.a['intake_store_id'],'mode':'TECHNICAL_FIXTURE','assignments':[]})
        self.assertEqual(call(['export',self.protocol,self.f.root,empty,self.f.base/'invalid-export']).returncode,2)

if __name__=='__main__':unittest.main()
