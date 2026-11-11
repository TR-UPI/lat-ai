import importlib.util,tempfile,unittest
from pathlib import Path
s=importlib.util.spec_from_file_location('readiness',Path(__file__).with_name('check-ai-readiness.py'));m=importlib.util.module_from_spec(s);s.loader.exec_module(m)

class ReadinessTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name);(self.root/'model-source.txt').write_text('frozen');self.manifest={'model-source.txt':m.sha(self.root/'model-source.txt')}
    def test_unchanged_and_drift_are_distinct(self):
        self.assertTrue(m.verify_pinned(self.root,self.manifest)['passed']);(self.root/'model-source.txt').write_text('changed');v=m.verify_pinned(self.root,self.manifest);self.assertFalse(v['passed']);self.assertEqual(v['errors'][0]['reason'],'sha256_changed')
    def test_missing_is_not_a_success(self):
        (self.root/'model-source.txt').unlink();self.assertEqual(m.verify_pinned(self.root,self.manifest)['errors'][0]['reason'],'missing')
    def test_manifest_cannot_escape_root(self):
        for name in ['../outside','C:/outside','folder\\outside']:
            with self.assertRaises(ValueError):m.verify_pinned(self.root,{name:'0'*64})
    def test_exclusion_cannot_hide_source_drift(self):
        with self.assertRaisesRegex(ValueError,'only_navigation'):m.verify_pinned(self.root,self.manifest,{'model-source.txt'})
    def test_mutable_navigation_is_explicitly_ignored_only(self):
        v=m.verify_pinned(self.root,{**self.manifest,'START_HERE.md':'0'*64},m.NAV);self.assertTrue(v['passed']);self.assertEqual(v['files_checked'],1)

if __name__=='__main__':unittest.main()
