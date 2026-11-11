"""Technical fixtures only; no real pilot claims or model inference."""
import unittest,tempfile,json,importlib.util
from pathlib import Path
from datetime import datetime,timezone,timedelta
spec=importlib.util.spec_from_file_location('signal_pilot',Path(__file__).with_name('review-signal-pilot.py'));mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
def write(p,v):p.write_text(json.dumps(v),encoding='utf-8')
def rehash(p):Path(str(p)+'.sha256').write_text(mod.sha(p))
class SignalPilotTests(unittest.TestCase):
 def fixture(self,d,origin='synthetic_smoke'):
  root=Path(d);protocol=root/'rules.json';rules=mod.freeze_rules(protocol);dataset=root/'dataset';dataset.mkdir()
  write(dataset/'freeze.json',{'data_origin':origin,'frozen_utc':(datetime.now(timezone.utc)+timedelta(seconds=10)).isoformat()})
  plan=root/'plan.json';write(plan,{'data_origin':origin,'frozen_dir':str(dataset),'source_sha256':{n:mod.sha(mod.ROOT/'lat-ai'/n) for n in ['integration/ai/core/src/assessment-verifier.mjs','integration/ai/core/data/assessment-verifier-rubrics.json']}});rehash(plan)
  return protocol,plan,dataset
 def test_synthetic_quality_run_is_blocked_before_output_creation(self):
  with tempfile.TemporaryDirectory() as d:
   rule,plan,_=self.fixture(d);out=Path(d)/'out'
   with self.assertRaisesRegex(ValueError,'real_student'):mod.export(rule,plan,[],Path(d)/'nonexistent-node',out)
   self.assertFalse(out.exists())
 def test_rule_hash_and_dependency_hash_changes_are_rejected(self):
  for change in ['bytes','dependency']:
   with tempfile.TemporaryDirectory() as d:
    rule,_,_=self.fixture(d)
    if change=='bytes':rule.write_text(rule.read_text()+' ')
    else:
     data=mod.read(rule);data['files_sha256']['tools/review-signals.mjs']='0'*64;write(rule,data);rehash(rule)
    with self.assertRaises(ValueError):mod.verify_rules(rule)
 def test_dataset_before_rule_freeze_or_without_timezone_is_rejected(self):
  for date in ['2000-01-01T00:00:00+00:00','2099-01-01T00:00:00']:
   with tempfile.TemporaryDirectory() as d:
    rule,plan,ds=self.fixture(d,'real_student');write(ds/'freeze.json',{'data_origin':'real_student','frozen_utc':date})
    with self.assertRaises(ValueError):mod.preflight(rule,plan)
 def test_current_verifier_identity_and_plan_hash_are_required(self):
  for change in ['source','bytes']:
   with tempfile.TemporaryDirectory() as d:
    rule,plan,_=self.fixture(d,'real_student')
    if change=='bytes':plan.write_text(plan.read_text()+' ')
    else:
     data=mod.read(plan);data['source_sha256']['integration/ai/core/src/assessment-verifier.mjs']='0'*64;write(plan,data);rehash(plan)
    with self.assertRaises(ValueError):mod.preflight(rule,plan)
 def test_preflight_accepts_future_declared_fixture_but_makes_no_quality_claim(self):
  with tempfile.TemporaryDirectory() as d:
   rule,plan,_=self.fixture(d,'real_student');self.assertEqual(mod.preflight(rule,plan)['data_origin'],'real_student')
   # This only exercises metadata gates. Full export still requires verified real run artifacts.
 def test_freeze_refuses_to_overwrite_existing_protocol(self):
  with tempfile.TemporaryDirectory() as d:
   rule,_,_=self.fixture(d)
   with self.assertRaises(FileExistsError):mod.freeze_rules(rule)
 def test_full_export_on_explicit_technical_fixture_preserves_model_results(self):
  # All people, labels, instance IDs and hardware below are fabricated test fixtures.
  # Artifacts stay in a temporary directory; this is not a pilot or quality estimate.
  with tempfile.TemporaryDirectory() as d:
   rule,plan,ds=self.fixture(d,'real_student');root=Path(d)
   cases=[{'id':'P1','task_key':'L1.types.1','answer':'Результат 32. Строки склеиваются.','expected':[True]*3},
          {'id':'P2','task_key':'L1.types.1','answer':'Не знаю.','expected':[False]*3},
          {'id':'P3','task_key':'L1.types.1','answer':'Строки склеиваются, результат 32.','expected':[True]*3}]
   write(ds/'primary-cases.json',cases)
   for label in ['A','B']:write(ds/f'review-{label}.frozen.json',{'reviewer_id':'fixture-'+label,'completed_without_model_results':True,'cases':[{'id':c['id'],'checks':c['expected']} for c in cases]})
   write(ds/'adjudication.frozen.json',{'cases':[]})
   for n in [1,2,3]:write(ds/f'repeat{n}.json',[{**c,'id':f'R{n}-'+c['id'],'source_id':c['id'],'repeat':n} for c in cases])
   orders=[['P1','P2','P3'],['P3','P2','P1'],['P2','P3','P1']];env={'explicit_test_fixture':True};config={'explicit_test_fixture':True}
   data=mod.read(plan);data.update(format=2,primary_series=1,series=[1,2,3],execution_orders=orders,environment=env,expected_load_config=config,load_policy='fresh_owned_instance_per_series_no_warmup',dataset_sha256={p.name:mod.sha(p) for p in ds.iterdir()});write(plan,data);rehash(plan)
   runs=[];input_hashes={}
   for n in [1,2,3]:
    folder=root/f'run{n}';folder.mkdir();runs.append(folder);instance=f'owned-test-fixture-{n}'
    for name in ['environment-before.json','environment-after.json']:write(folder/name,env)
    write(folder/'loaded-model.json',{'models':[{'loaded_instances':[{'id':instance,'config':config}]}]})
    write(folder/'provenance.json',{'series':n,'plan_sha256':mod.sha(plan),'execution_order':orders[n-1]})
    history=[];result_hashes={}
    for pos,key in enumerate(orders[n-1],1):
     c=next(c for c in cases if c['id']==key);actual=[False,True,True] if key=='P1' else [False]*3 if key=='P2' else None
     ids=[-1,1,0] if key=='P1' else [-1,-1,-1] if key=='P2' else [0,0,0]
     verifier={'answer':json.dumps({f'criterion_{i+1}':v for i,v in enumerate(ids)}),'finish_reason':'stop','stats':{'total_output_tokens':23,'reasoning_output_tokens':0}}
     row={**c,'id':f'R{n}-{key}','source_id':key,'series':n,'instance':instance,'position':pos,'fresh_before_case':pos==1,'predecessor_case_ids':orders[n-1][:pos-1],'actual':actual,'status':'refused' if actual is None else 'assessed','raw':{'verification':verifier},'result':None if actual is None else {'evidence':['','','']},'ms':1,'stages':[]}
     name=row['id']+'.json';write(folder/name,row);result_hashes[name]=mod.sha(folder/name)
     for stage in ['proposal','verification']:
      write(folder/f'R{n}-{key}-{stage}-dispatch.json',{'instance':instance,'source_id':key,'stage':stage,'predecessor_calls':list(history)})
      history.append({'source_id':key,'stage':stage})
    hashes={p.name:mod.sha(p) for p in folder.iterdir()};write(folder/'summary.json',{'format':2,'status':'complete','retirement_proven':True,'series':n,'plan_sha256':mod.sha(plan),'execution_order':orders[n-1],'result_sha256':result_hashes,'provenance_sha256':hashes})
    input_hashes.update({str(p):mod.sha(p) for p in folder.iterdir()})
   output=root/'advisory';result=mod.export(rule,plan,runs,mod.ROOT/'work/lat-ai-runtime/node/node.exe',output)
   metrics=result['metrics_counts'];self.assertEqual(metrics['unique_primary_cases'],3);self.assertEqual(metrics['primary_flagged'],1);self.assertEqual(metrics['wrong_graded_flagged'],1);self.assertEqual(metrics['correct_graded_flagged'],0);self.assertEqual(metrics['refused_flagged'],0)
   queue=mod.read(output/'review-queue.json')['cases'];self.assertEqual([c['id'] for c in queue],['P1']);self.assertIsNone(queue[0]['teacher_decision'])
   for path,digest in input_hashes.items():self.assertEqual(mod.sha(path),digest)
   for row in mod.read(output/'signal-inputs.json'):self.assertNotIn('expected',row)
if __name__=='__main__':unittest.main()
