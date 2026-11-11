import importlib.util, pathlib, unittest, tempfile, json
from unittest.mock import patch
spec=importlib.util.spec_from_file_location('audit',pathlib.Path(__file__).with_name('prepare-signal-review-audit.py'))
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
def row(i,status='no_signal_found',flag=False):return {'id':i,'status':status,'manual_review_suggested':flag}
class SelectionTests(unittest.TestCase):
    def test_controls_and_all_other_strata(self):
        rows=[row(str(i)) for i in range(40)]+[row('F','signals_found',True),row('T','technical_error',True),row('U','unsupported_task',None)]
        selected,strata=m.select(rows,'frozen-seed',20)
        self.assertEqual(len(selected),23);self.assertTrue({'F','T','U'}<=set(selected))
        self.assertEqual((selected,strata),m.select(list(reversed(rows)),'frozen-seed',20))
    def test_small_control_population_all_included(self):
        self.assertEqual(set(m.select([row('a'),row('b')],'seed',20)[0]),{'a','b'})
    def test_duplicates_and_bad_status_rejected(self):
        for rows in ([row('a'),row('a')],[row('a','no_signal_found',True)],[row('a','new_status')]):
            with self.assertRaises(ValueError):m.select(rows,'seed',20)
    def test_invalid_sampling_parameters(self):
        for count in (0,-1,1.5,True):
            with self.assertRaises(ValueError):m.select([],'seed',count)
        with self.assertRaises(ValueError):m.select([], '',20)
    def test_public_allowlist_excludes_labels_and_selection(self):
        source={'a':{'task_key':'task','student_answer':'Answer','verification':{'answer':'model text'},'expected':[True]*3,'category':'trap','group':'origin','series':1}}
        cards=m.public_cards(['a'],source,{'task':{'code':'print(1)','criteria':['c1','c2','c3']}},'seed')
        self.assertEqual(set(cards[0]),m.PUBLIC_FIELDS);self.assertNotEqual(cards[0]['audit_id'],'a')
        self.assertTrue(all(cards[0][k] is None for k in ['human_decision','reviewer_registry_id','prior_exposure_declared']))
    def test_missing_rubric_blocks_exposure(self):
        with self.assertRaises(ValueError):m.public_cards(['a'],{'a':{'task_key':'new'}},{},'seed')
    def test_known_author_data_rejected_by_real_preflight(self):
        with self.assertRaisesRegex(ValueError,'real_student'):
            m.export(m.ROOT/'not-needed.json',m.ROOT/'outputs/review-signals-prototype-2026-11-11/signal-protocol.json',m.ROOT/'outputs/u02-runtime-controls-2026-11-11/known128-plan.json','not-needed','not-created')
    def test_export_integrity_and_no_overwrite(self):
        # Synthetic mechanics fixture only. Real-data preflight separately tested above.
        with tempfile.TemporaryDirectory() as temp:
            root=pathlib.Path(temp); data=root/'data'; data.mkdir(); signals=root/'signals';signals.mkdir()
            write=lambda p,v:p.write_text(json.dumps(v),encoding='utf-8')
            rules=root/'rules.json';write(rules,{})
            plan=root/'plan.json'
            write(data/'primary-cases.json',[{'id':'a','answer':'text','task_key':'task'}])
            write(data/'freeze.json',{'frozen_utc':'2030-01-01T00:00:00+00:00','model_results_seen_during_labeling':False,'files_sha256':{'primary-cases.json':m.sha(data/'primary-cases.json')}})
            write(plan,{'frozen_dir':str(data),'dataset_sha256':{p.name:m.sha(p) for p in data.iterdir()}})
            rubric=root/'lat-ai/integration/ai/core/data/assessment-verifier-rubrics.json';rubric.parent.mkdir(parents=True);write(rubric,{'tasks':{'task':{'code':'code','criteria':['c1','c2','c3']}}})
            for name in m.FILES:
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes((m.ROOT/name).read_bytes())
            protocol=root/'protocol.json';write(protocol,{'created_utc':'2026-11-11T00:00:00+00:00','signal_protocol_sha256':m.sha(rules),'seed':'seed','control_count':20,'files_sha256':{n:m.sha(root/n) for n in m.FILES}})
            pathlib.Path(str(protocol)+'.sha256').write_text(m.sha(protocol))
            inputs=[{'series':n,'id':'a','student_answer':'text','task_key':'task','verification':{'answer':'model'}} for n in (1,2,3)]
            write(signals/'signal-inputs.json',inputs)
            write(signals/'signals.json',{'input_sha256':m.sha(signals/'signal-inputs.json'),'rows':[{**row('a'),'series':n,'advisory_only':True,'changes_score':False,'changes_gate':False} for n in (1,2,3)]})
            write(signals/'signal-analysis.json',{'model_plan_sha256':m.sha(plan),'rule_protocol_sha256':m.sha(rules)})
            write(signals/'review-queue.json',{});(signals/'batch.log').write_text('fixture')
            write(signals/'MANIFEST.json',{p.name:m.sha(p) for p in signals.iterdir()})
            helper=m.load_signal_module()
            with patch.object(m,'ROOT',root),patch.object(m,'load_signal_module',return_value=helper),patch.object(helper,'preflight',return_value=m.read(plan)):
                result=m.export(protocol,rules,plan,signals,root/'out')
                self.assertEqual(result,{'selected':1,'controls':1,'quality_claim':False})
                self.assertEqual(set(m.read(root/'out/reviewer/cards.json')['cards'][0]),m.PUBLIC_FIELDS)
                with self.assertRaises(FileExistsError):m.export(protocol,rules,plan,signals,root/'out')
                (signals/'batch.log').write_text('changed')
                with self.assertRaisesRegex(ValueError,'export changed'):m.export(protocol,rules,plan,signals,root/'out2')
                self.assertFalse((root/'out2').exists())
if __name__=='__main__':unittest.main()
