import importlib.util,json,tempfile,unittest,copy
from pathlib import Path
from datetime import datetime,timezone,timedelta
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('intake',Path(__file__).with_name('receive-review-cards.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
REVIEWER='11111111-1111-4111-8111-111111111111'
COORDINATOR='22222222-2222-4222-8222-222222222222'
NOW=datetime(2030,1,1,tzinfo=timezone.utc)

class IntakeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.protocol=self.root/'protocol.json';m.freeze(self.protocol)
        rendered=self.root/'rendered';(rendered/'reviewer').mkdir(parents=True)
        payload=m.read(m.ROOT/'outputs/review-card-fragments-2026-11-11/demo-final/cards.json')
        # Deliberately synthetic mechanics package, not a claimed real pilot or human response.
        payload['phase']='POST-LABEL TECHNICAL_FIXTURE';payload['cards']=payload['cards'][:2]
        self.write(rendered/'reviewer/cards.json',payload)
        for n in ['CARDS.txt','READ_FIRST.txt']:(rendered/'reviewer'/n).write_text('TECHNICAL_FIXTURE',encoding='utf-8')
        exposed={n:m.digest(rendered/'reviewer'/n) for n in m.EXPOSED[:3]}
        self.write(rendered/'PRIVATE_DELIVERY.json',{'presentation_protocol_sha256':m.digest(m.PRESENTATION),'files_seen_sha256':exposed})
        self.write(rendered/'MANIFEST.json',{'PRIVATE_DELIVERY.json':m.digest(rendered/'PRIVATE_DELIVERY.json'),**{'reviewer/'+n:h for n,h in exposed.items()}})
        self.assignment=self.root/'assignment';self.store=self.root/'store';self.rendered=rendered
        with patch.object(m,'utcnow',return_value=NOW):m.prepare(self.protocol,rendered,REVIEWER,self.store,self.assignment)
        self.returned=self.root/'returned.json';self.delivery=self.root/'delivery.json'
        self.payload=copy.deepcopy(payload)
        for c in self.payload['cards']:
            statuses=c['citation_readout']['references']
            c.update(human_decision={'criteria':['met','uncertain','not_met'],'citation_sufficiency':['sufficient' if r['status']=='fragment_selected' else 'not_selected' if r['status']=='no_fragment_selected' else 'unreadable' for r in statuses],'contradiction':'uncertain','contradiction_fragment_ids':[]},human_reason='TECHNICAL_FIXTURE only; uncertainty intentionally exercises follow-up.',reviewer_registry_id=REVIEWER,reviewed_utc='2030-01-01T00:02:00Z',prior_exposure_declared={'before_this_audit':'none','details':'Fixture: no prior exposure','saw_verifier_readout':True})
        self.receipt=m.read(self.assignment/'DELIVERY_TEMPLATE.json')
        self.receipt.update(coordinator_registry_id=COORDINATOR,delivered_utc='2030-01-01T00:01:00Z',prior_exposure_confirmed_by_coordinator={'before_this_audit':'none','details':'TECHNICAL_FIXTURE'})
        self.flush()
    def write(self,p,v):p.write_text(json.dumps(v,ensure_ascii=False),encoding='utf-8')
    def flush(self):self.write(self.returned,self.payload);self.write(self.delivery,self.receipt)
    def receive(self):
        with patch.object(m,'utcnow',return_value=NOW+timedelta(minutes=3)):
            return m.receive(self.protocol,self.assignment,self.returned,self.delivery,self.store)
    def assertRejected(self,result):self.assertFalse(result['validation_passed']);self.assertEqual(list((self.store/'accepted').iterdir()),[])
    def test_complete_uncertain_return_accepted_without_gold_mutation_and_repeat_idempotent(self):
        before=m.digest(self.assignment/'reviewer/cards.json');r=self.receive()
        self.assertTrue(r['validation_passed']);self.assertEqual(len(r['followup']),2);self.assertFalse(r['independent_gold'])
        repeat=self.receive();self.assertTrue(repeat['repeat_of_saved_attempt']);self.assertEqual(len(list((self.store/'attempts').iterdir())),1)
        self.assertEqual(m.digest(self.assignment/'reviewer/cards.json'),before)
    def test_source_changes_and_boolean_for_integer_detected(self):
        self.payload['cards'][0]['citation_readout']['fragments'][0]['id']=False;self.flush();r=self.receive();self.assertRejected(r)
        self.assertIn('immutable_card_content_changed',[x['code'] for x in r['errors']])
    def test_missing_duplicate_reordered_and_foreign_ids_rejected(self):
        original=copy.deepcopy(self.payload)
        for kind in ['missing','duplicate','reordered','foreign']:
            self.payload=copy.deepcopy(original)
            if kind=='missing':self.payload['cards'].pop()
            elif kind=='duplicate':self.payload['cards'][1]=copy.deepcopy(self.payload['cards'][0])
            elif kind=='reordered':self.payload['cards'].reverse()
            else:self.payload['cards'][0]['audit_id']='f'*32
            self.flush();self.assertRejected(self.receive())
    def test_required_fields_identity_and_time(self):
        original=copy.deepcopy(self.payload)
        mutations=[('human_reason',' '),('reviewer_registry_id',COORDINATOR),('reviewer_registry_id',REVIEWER.upper().replace('1','А',1)),('reviewed_utc','2030-01-01T00:00:01Z'),('reviewed_utc','2030-01-02T00:00:00Z'),('reviewed_utc','2030-01-01T00:02:00+01:00'),('human_decision',None)]
        for field,value in mutations:
            self.payload=copy.deepcopy(original);self.payload['cards'][0][field]=value;self.flush();self.assertRejected(self.receive())
    def test_citation_applicability_and_contradiction_evidence(self):
        self.payload['cards'][0]['human_decision']['citation_sufficiency'][2]='sufficient';self.flush();self.assertRejected(self.receive())
        self.payload['cards'][0]['human_decision']['citation_sufficiency'][2]='not_selected'
        self.payload['cards'][0]['human_decision']['contradiction']='present';self.flush();self.assertRejected(self.receive())
        self.payload['cards'][0]['human_decision']['contradiction_fragment_ids']=[0];self.flush();self.assertTrue(self.receive()['validation_passed'])
    def test_delivery_hash_identity_and_exposure(self):
        self.receipt['files_seen_sha256']['FILLING_GUIDE.txt']='0'*64;self.flush();self.assertRejected(self.receive())
    def test_exposure_disagreement_and_unknown_preserved_as_followup(self):
        self.payload['cards'][0]['prior_exposure_declared']['before_this_audit']='unknown';self.flush();r=self.receive()
        self.assertTrue(r['validation_passed']);self.assertIn('exposure_declaration_disagreement',r['followup'][0]['reasons']);self.assertIn('unknown_prior_exposure',r['followup'][0]['reasons'])
    def test_duplicate_json_keys_and_nonfinite_preserved_but_rejected(self):
        for data in [b'{"cards":[],"cards":[]}',b'{"cards":NaN}']:
            self.returned.write_bytes(data);r=self.receive();self.assertRejected(r)
            self.assertEqual((self.store/'attempts'/r['attempt_id']/'returned.json').read_bytes(),data)
    def test_no_silent_replacement_of_accepted_assignment(self):
        self.assertTrue(self.receive()['validation_passed']);self.payload['cards'][0]['human_reason']='Corrected fixture';self.flush();r=self.receive()
        self.assertFalse(r['validation_passed']);self.assertEqual(r['errors'][0]['code'],'assignment_already_accepted_no_automatic_replacement');self.assertEqual(len(list((self.store/'accepted').iterdir())),1)
    def test_lock_not_stolen_and_assignment_tamper_stops_before_store(self):
        (self.store/'intake.lock').write_text('foreign')
        with self.assertRaises(FileExistsError):self.receive()
        self.assertEqual((self.store/'intake.lock').read_text(),'foreign')
        (self.assignment/'reviewer/CARDS.txt').write_text('changed')
        with self.assertRaisesRegex(ValueError,'artifact_changed'):self.receive()
    def test_partial_commit_fails_closed(self):
        r=self.receive();accepted=next((self.store/'accepted').iterdir());accepted.unlink()
        with self.assertRaisesRegex(ValueError,'incomplete_or_conflicting_commit'):self.receive()
        self.assertTrue((self.store/'attempts'/r['attempt_id']/'RECEIPT.json').exists())
    def test_marker_and_saved_receipt_integrity(self):
        self.receive();accepted=next((self.store/'accepted').iterdir());record=m.read(accepted);record['receipt_sha256']='0'*64;self.write(accepted,record)
        with self.assertRaisesRegex(ValueError,'accepted_marker_receipt_mismatch'):self.receive()
    def test_typed_float_and_extreme_json_values(self):
        self.payload['cards'][0]['citation_readout']['fragments'][0]['id']=0.0;self.flush();self.assertRejected(self.receive())
        for data in [b'{"cards":9007199254740992}',b'{"cards":1e999}',br'{"cards":"\uD800"}']:
            self.returned.write_bytes(data);self.assertRejected(self.receive())
    def test_human_met_with_no_selected_citation_and_conflicting_judgments_are_preserved(self):
        d=self.payload['cards'][0]['human_decision'];d['criteria']=['not_met','met','met'];self.flush();r=self.receive()
        self.assertTrue(r['validation_passed']);self.assertIn('disagreement_with_displayed_verifier',r['followup'][0]['reasons']);self.assertIn('human_combination_requires_explanation',r['followup'][0]['reasons'])
    def test_repeat_issue_same_content_reviewer_blocked_without_overwrite(self):
        with self.assertRaisesRegex(ValueError,'already_reserved_or_issued'):
            m.prepare(self.protocol,self.rendered,REVIEWER,self.store,self.root/'second-assignment')
        self.assertFalse((self.root/'second-assignment').exists())
        p=copy.deepcopy(self.payload);p['cards'].reverse()
        for c in p['cards']:c['audit_id']='f'*32
        self.assertEqual(m.package_key(p,REVIEWER),m.package_key(self.payload,REVIEWER))
    def test_assignment_cannot_be_imported_into_another_registry(self):
        with self.assertRaisesRegex(ValueError,'wrong_intake_store'):
            m.receive(self.protocol,self.assignment,self.returned,self.delivery,self.root/'other-store')

if __name__=='__main__':unittest.main()
