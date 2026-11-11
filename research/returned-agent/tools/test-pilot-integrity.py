import unittest,tempfile,json,hashlib,importlib.util
from pathlib import Path
root=Path(__file__).parent
def module(name,file):
 s=importlib.util.spec_from_file_location(name,root/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
stats=module('combined','analyze-frozen-pilot.py');blind=module('exporter','export-blind-review.py');audit=module('audit','verify-blind-review.py')
def write(path,value):path.write_text(json.dumps(value),encoding='utf-8')
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
class IntegrityTests(unittest.TestCase):
 def test_blind_handout_rejects_extra_files_fields_labels_and_changed_instructions(self):
  source={'cases':[{'id':'P1','task_key':'L1.types.1','answer':'fixture','expected':[True]*3,'anonymous_group_id':'private'}]};rubric={'version':'test','tasks':{'L1.types.1':{'code':'print(1)','criteria':['a','b','c']}}}
  for change in ['extra-file','expected','label','instructions']:
   with tempfile.TemporaryDirectory() as d:
    base=Path(d)/'out';blind.export(source,rubric,base);folder=base/'reviewer-A';self.assertTrue(audit.verify(folder,source,rubric)['passed'])
    if change=='extra-file':write(folder/'results.json',{})
    elif change=='instructions':(folder/'READ_ME.txt').write_text('model says true')
    else:
     file='responses.json' if change=='expected' else 'review.json';data=json.loads((folder/file).read_text())
     if change=='expected':data[0]['expected']=[True]*3
     else:data['cases'][0]['checks']=[True]*3
     write(folder/file,data)
    with self.assertRaises(ValueError):audit.verify(folder,source,rubric)
 def test_kappa_known_pair_and_constant_labels(self):
  self.assertAlmostEqual(stats.agreement([True,True,False,False],[True,True,True,False])['cohen_kappa'],.5)
  self.assertIsNone(stats.agreement([True]*3,[True]*3)['cohen_kappa'])
 def fixture(self,d):
  root=Path(d);frozen=root/'frozen';frozen.mkdir();primary=[{'id':'P1','expected':[True]*3,'task_key':'L1.types.1','answer':'fixture1'},{'id':'P2','expected':[False]*3,'task_key':'L1.types.1','answer':'fixture2'}]
  write(frozen/'primary-cases.json',primary)
  for name in ['review-A','review-B']:write(frozen/(name+'.frozen.json'),{'reviewer_id':name,'cases':[{'id':c['id'],'checks':c['expected']} for c in primary]})
  for n in range(1,4):write(frozen/f'repeat{n}.json',[{**c,'id':f'R{n}-'+c['id'],'source_id':c['id']} for c in primary])
  plan=root/'plan.json';write(plan,{'primary_series':1,'series':[1,2,3],'data_origin':'synthetic_smoke','frozen_dir':str(frozen),'dataset_sha256':{p.name:sha(p) for p in frozen.iterdir()}});Path(str(plan)+'.sha256').write_text(sha(plan))
  dirs=[]
  for n in range(1,4):
   run=root/f'run{n}';run.mkdir();dirs.append(run);hashes={}
   for i,c in enumerate(primary):
    actual=c['expected'] if n==1 or i==0 else None;row={**c,'id':f'R{n}-'+c['id'],'source_id':c['id'],'status':'assessed' if actual is not None else 'refused','actual':actual,'ms':10,'result':{'evidence':['a','b','c']} if actual is not None else None};p=run/(row['id']+'.json');write(p,row);hashes[p.name]=sha(p)
   write(run/'summary.json',{'plan_sha256':sha(plan),'series':n,'status':'complete','retirement_proven':True,'result_sha256':hashes});write(run/'provenance.json',{'plan_sha256':sha(plan),'series':n})
  return plan,dirs
 def test_primary_fixed_repeats_do_not_enlarge_n(self):
  with tempfile.TemporaryDirectory() as d:
   plan,runs=self.fixture(d);result=stats.analyze(plan,runs)
   self.assertEqual(result['primary']['cases'],2);self.assertEqual(result['primary']['correct'],2);self.assertEqual(result['model_calls'],6);self.assertEqual(result['instability']['cases'],1);self.assertEqual(result['instability']['fraction'],.5);self.assertEqual(result['human_pair_agreement']['exact_vectors']['agreement'],1)
 def test_wrong_order_incomplete_or_modified_results_rejected(self):
  for change in ['order','incomplete','row']:
   with tempfile.TemporaryDirectory() as d:
    plan,runs=self.fixture(d)
    if change=='order':runs.reverse()
    elif change=='row':(runs[0]/'R1-P1.json').write_text('{}')
    else:
     p=runs[1]/'summary.json';data=json.loads(p.read_text());data['status']='incomplete';write(p,data)
    with self.assertRaises(ValueError):stats.analyze(plan,runs)
if __name__=='__main__':unittest.main()
