from pathlib import Path
import json,hashlib,zipfile,subprocess,sys
root=Path(__file__).resolve().parent.parent
base=root/'outputs/ai-continuation-2026-11-11'
out=base/'package-extracted-verification';out.mkdir(exist_ok=False)
with zipfile.ZipFile(base/'LAT-AI-PILOT-AND-HUMAN-REVIEW-2026-11-11.zip') as z:
 for name in z.namelist():
  target=(out/name).resolve()
  if not target.is_relative_to(out.resolve()):raise ValueError('Unsafe ZIP path')
 z.extractall(out)
package=out/'LAT-AI-HUMAN-REVIEW'
manifest=json.loads((package/'MANIFEST.json').read_text(encoding='utf-8'))
for f in manifest['files']:
 p=package/f['path'];assert p.stat().st_size==f['bytes'];assert hashlib.sha256(p.read_bytes()).hexdigest()==f['sha256']
run=subprocess.run([sys.executable,str(package/'08_ENGINEER/tools/test-shadow-pilot.py')],capture_output=True,text=True)
(base/'package-portability-tests.log').write_text(run.stdout+run.stderr,encoding='utf-8');assert run.returncode==0
for p in (package/'03_BLIND_REVIEW_TEMPLATES').rglob('*.json'):
 review=json.loads(p.read_text(encoding='utf-8'));assert review['completed_without_model_results'] is False
 assert all(c['checks']==[None,None,None] for c in review['cases'])
assert (package/'05_TEACHER_EXPLANATIONS_T01/frozen-inputs/eval/fact-snapshots.json').is_file()
report={'manifest_entries_verified':len(manifest['files']),'archive_files':len(manifest['files'])+1,'extracted_tools_exit_code':run.returncode,'blank_reviewer_labels':True,'teacher_context_present':True}
(base/'package-portability-verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
