from pathlib import Path
import json,hashlib,zipfile,subprocess,sys
root=Path(__file__).resolve().parent.parent;out=root/'outputs/ai-pilot-integrity-2026-11-11';extract=out/'extracted-package-check';extract.mkdir(exist_ok=False)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
for item in read(out/'packages-verification.json'):
 archive=Path(item['path']);assert hashlib.sha256(archive.read_bytes()).hexdigest()==item['sha256']
 with zipfile.ZipFile(archive) as z:
  assert z.testzip() is None
  for name in z.namelist():assert (extract/name).resolve().is_relative_to(extract.resolve())
  z.extractall(extract)
for folder in extract.iterdir():
 manifest=read(folder/'MANIFEST.json')
 for name,entry in manifest.items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==entry['sha256']
engineer=extract/'ENGINEER-TOOLS'
commands=[('pilot',[sys.executable,str(engineer/'test-shadow-pilot.py')]),('integrity',[sys.executable,str(engineer/'test-pilot-integrity.py')]),('runner',[str(root/'work/lat-ai-runtime/node/node.exe'),'--test',str(engineer/'test-frozen-assessment-run.mjs')])]
results={}
for name,command in commands:
 result=subprocess.run(command,capture_output=True,text=True,encoding='utf-8',errors='replace');(out/f'package-{name}-tests.log').write_text(result.stdout+result.stderr,encoding='utf-8');results[name]=result.returncode
assert all(code==0 for code in results.values()),results
before=read(root/'outputs/ai-continuation-2026-11-11/source-audit.json')['after_sha256']
names=subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],cwd=root/'lat-ai').decode().split('\0')
after={name:hashlib.sha256((root/'lat-ai'/name).read_bytes()).hexdigest() for name in sorted(set(filter(None,names))) if (root/'lat-ai'/name).is_file()}
changed=[name for name in sorted(set(before)|set(after)) if before.get(name)!=after.get(name)]
assert set(changed)=={'docs/ai/ASSESSMENT_EVIDENCE_V3.md','docs/ai/TEAM_OWNERSHIP_AND_RECOVERY.md'},changed
protected=[p for p in before if p.startswith(('backend/','assets/')) or p=='index.html'];assert all(before[p]==after[p] for p in protected)
report={'before_files':len(before),'after_files':len(after),'changed':changed,'executable_ai_source_unchanged':True,'protected_files':len(protected),'protected_unchanged':True,'after_sha256':after,'extracted_test_exit_codes':results}
(out/'source-and-package-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='after_sha256'}))
