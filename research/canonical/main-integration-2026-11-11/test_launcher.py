import unittest, tempfile, shutil, subprocess, json
from pathlib import Path

SOURCE=Path(__file__).resolve().parents[2]/'work/main-integration-stage/tools/start-main.ps1'

class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        (self.root/'tools').mkdir()
        (self.root/'.runtime').mkdir()
        (self.root/'.venv/Scripts').mkdir(parents=True)
        (self.root/'.venv/Scripts/python.exe').write_bytes(b'')
        shutil.copy2(SOURCE,self.root/'tools/start-main.ps1')
    def check(self, config):
        (self.root/'.runtime/main-local.json').write_text(json.dumps(config),encoding='utf-8')
        return subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(self.root/'tools/start-main.ps1'),'-CheckOnly'],capture_output=True)
    def test_empty_object_cannot_fall_back_to_other_database(self):
        self.assertNotEqual(self.check({}).returncode,0)
    def test_null_cannot_fall_back_to_other_database(self):
        self.assertNotEqual(self.check(None).returncode,0)
    def test_blank_runtime_cannot_fall_back(self):
        self.assertNotEqual(self.check({'runtime':'','python':str(self.root/'.venv/Scripts/python.exe'),'node':shutil.which('node.exe')}).returncode,0)
    def test_array_is_not_a_config(self):
        self.assertNotEqual(self.check([]).returncode,0)
    def test_missing_existing_database_fails(self):
        self.assertNotEqual(self.check({'runtime':str(self.root/'.runtime/existing'),'python':str(self.root/'.venv/Scripts/python.exe'),'node':shutil.which('node.exe')}).returncode,0)
    def test_check_only_uses_exact_database_without_starting_python(self):
        runtime=self.root/'preserved database'
        runtime.mkdir()
        (runtime/'django.sqlite3').write_bytes(b'unchanged')
        result=self.check({'runtime':str(runtime),'python':str(self.root/'.venv/Scripts/python.exe'),'node':shutil.which('node.exe')})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual((runtime/'django.sqlite3').read_bytes(),b'unchanged')
        self.assertIn(str(runtime).encode(),result.stdout)

if __name__=='__main__': unittest.main()
