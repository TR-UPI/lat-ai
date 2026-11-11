import importlib.util,unittest,tempfile,json,math,hashlib
from pathlib import Path
root=Path(__file__).resolve().parent
def module(name,file):
 s=importlib.util.spec_from_file_location(name,root/file);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
pilot=module('pilot','prepare-shadow-pilot.py');stats=module('stats','assessment-statistics.py')
blind=module('blind','export-blind-review.py')
class PilotTests(unittest.TestCase):
 def data(self):
  # Synthetic fixture exercising validation only, never used as real pilot data.
  source={'data_origin':'real_student','privacy_reviewed_by':'fixture','cases':[{'id':'test1','task_key':'L1.types.1','answer':'synthetic fixture'}]}
  a={'reviewer_id':'a','completed_without_model_results':True,'cases':[{'id':'test1','checks':[True,False,True]}]};b={**a,'reviewer_id':'b'}
  return source,a,b
 def test_freeze_and_repetitions_keep_one_unique_case(self):
  with tempfile.TemporaryDirectory() as d:
   result=pilot.freeze(*self.data(),{'cases':[]},Path(d)/'frozen');self.assertEqual(result['unique_cases'],1)
   r=json.loads((Path(d)/'frozen/repeat3.json').read_text());self.assertEqual(r[0]['source_id'],'test1');self.assertEqual(r[0]['expected'],[True,False,True])
 def test_disagreement_blocks_without_adjudication(self):
  source,a,b=self.data();b={**b,'cases':[{'id':'test1','checks':[True,True,True]}]}
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'Unresolved'):pilot.freeze(source,a,b,{'cases':[]},Path(d)/'x')
   result=pilot.freeze(source,a,b,{'cases':[{'id':'test1','checks':[True,False,True],'reviewer_id':'teacher','reason':'explicit missing operation'}]},Path(d)/'y');self.assertEqual(result['teacher_disagreements'],['test1'])
 def test_missing_labels_same_reviewer_and_unblinded_review_rejected(self):
  for bad in ['label','same','unblind']:
   source,a,b=self.data()
   if bad=='label':b={**b,'cases':[{'id':'test1','checks':[None,True,True]}]}
   if bad=='same':b={**b,'reviewer_id':'a'}
   if bad=='unblind':b={**b,'completed_without_model_results':False}
   with tempfile.TemporaryDirectory() as d:
    with self.assertRaises(ValueError):pilot.freeze(source,a,b,{'cases':[]},Path(d)/'x')
 def test_unsupported_task_and_identifying_metadata_rejected(self):
  for change in [{'task_key':'new.task'},{'student_email':'example@invalid'}]:
   source,a,b=self.data();source['cases'][0].update(change)
   with tempfile.TemporaryDirectory() as d:
    with self.assertRaises(ValueError):pilot.freeze(source,a,b,{'cases':[]},Path(d)/'x')
 def test_exact_bound_math_and_sample_size(self):
  self.assertAlmostEqual(stats.error_upper95(0,26),1-.05**(1/26));self.assertLess(stats.error_upper95(0,149),.02);self.assertGreater(stats.error_upper95(0,148),.02)
  self.assertIsNone(stats.error_upper95(0,0));self.assertEqual(stats.error_upper95(4,4),1)
  upper=stats.error_upper95(1,100);self.assertAlmostEqual(stats.binomial_cdf(1,100,upper),.05,places=10)
 def test_agreed_but_ambiguous_rubric_requires_explicit_resolution(self):
  source,a,b=self.data();a['cases'][0]['ambiguous_rubric']=True
  with tempfile.TemporaryDirectory() as d:
   with self.assertRaisesRegex(ValueError,'Unresolved'):pilot.freeze(source,a,b,{'cases':[]},Path(d)/'blocked')
   decision={'cases':[{'id':'test1','checks':[True,False,True],'reviewer_id':'teacher','reason':'Resolved interpretation before model run'}]}
   result=pilot.freeze(source,a,b,decision,Path(d)/'accepted')
   self.assertEqual(result['rubric_ambiguities'],['test1']);self.assertEqual(result['teacher_disagreements'],[])
   self.assertEqual(len(result['files_sha256']),8)
   for name,expected in result['files_sha256'].items():self.assertEqual(hashlib.sha256((Path(d)/'accepted'/name).read_bytes()).hexdigest(),expected)
   saved=json.loads((Path(d)/'accepted/review-A.frozen.json').read_text());self.assertTrue(saved['cases'][0]['ambiguous_rubric'])
   self.assertTrue(a['cases'][0]['ambiguous_rubric'])
 def test_blind_export_removes_labels_model_results_and_group_metadata(self):
  source,_,_=self.data();source['cases'][0].update(expected=[True]*3,actual=[False]*3,category='correct',anonymous_group_id='private-group',previous_notes='model said wrong')
  rubrics={'version':'fixture','tasks':{'L1.types.1':{'code':'print(1)','criteria':['a','b','c']}}}
  with tempfile.TemporaryDirectory() as d:
   blind.export(source,rubrics,Path(d)/'blind')
   for label in ['A','B']:
    folder=Path(d)/'blind'/('reviewer-'+label);rows=json.loads((folder/'responses.json').read_text())
    self.assertEqual(set(rows[0]),{'id','task_key','answer'})
    review=json.loads((folder/'review.json').read_text());self.assertEqual(review['cases'][0]['checks'],[None]*3)
    self.assertFalse(review['completed_without_model_results'])
   with self.assertRaises(FileExistsError):blind.export(source,rubrics,Path(d)/'blind')
 def test_adjudicator_must_be_distinct_from_both_initial_reviewers(self):
  for reviewer in ['a','b',' a ','b\t','A','B']:
   source,a,b=self.data();b={**b,'cases':[{'id':'test1','checks':[True,True,True]}]}
   decision={'cases':[{'id':'test1','checks':[True,False,True],'reviewer_id':reviewer,'reason':'fixture resolution'}]}
   with tempfile.TemporaryDirectory() as d:
    target=Path(d)/'blocked'
    with self.assertRaisesRegex(ValueError,'distinct'):pilot.freeze(source,a,b,decision,target)
    self.assertFalse(target.exists())
 def test_whitespace_reviewer_ids_cannot_bypass_independence_or_required_identity(self):
  for aid,bid in [('a',' a '),('a','A'),(' ','b'),('a','\t'),(True,'b')]:
   source,a,b=self.data();a={**a,'reviewer_id':aid};b={**b,'reviewer_id':bid}
   with tempfile.TemporaryDirectory() as d:
    with self.assertRaises(ValueError):pilot.freeze(source,a,b,{'cases':[]},Path(d)/'blocked')
 def test_adjudication_requires_nonblank_reason_and_preserves_original_id(self):
  source,a,b=self.data();a['cases'][0]['ambiguous_rubric']=True
  with tempfile.TemporaryDirectory() as d:
   decision={'cases':[{'id':'test1','checks':[True,False,True],'reviewer_id':' Teacher C ','reason':'   '}]}
   with self.assertRaisesRegex(ValueError,'Unresolved'):pilot.freeze(source,a,b,decision,Path(d)/'blocked')
   decision['cases'][0]['reason']='Resolved fixture ambiguity';pilot.freeze(source,a,b,decision,Path(d)/'accepted')
   saved=json.loads((Path(d)/'accepted/adjudication.frozen.json').read_text());self.assertEqual(saved['cases'][0]['reviewer_id'],' Teacher C ')
if __name__=='__main__':unittest.main()
