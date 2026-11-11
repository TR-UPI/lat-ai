from pathlib import Path
import subprocess,json,hashlib,difflib
root=Path(__file__).resolve().parent.parent;source=root/'lat-ai';out=root/'outputs/ai-continuation-2026-11-11'
before=json.loads((out/'source-before.json').read_text())
paths=sorted(set(filter(None,subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],cwd=source).decode().split('\0'))))
after={p:hashlib.sha256((source/p).read_bytes()).hexdigest() for p in paths if (source/p).is_file()}
changes=[p for p in sorted(set(before)|set(after)) if before.get(p)!=after.get(p)]
allowed={'integration/ai/core/src/assessment-evidence-context.mjs','integration/ai/core/data/assessment-rubrics.json','integration/ai/test/assessment-evidence-context.test.mjs','docs/ai/ASSESSMENT_EVIDENCE_V3.md'}
assert set(changes)==allowed,changes
protected=[p for p in before if p.startswith(('backend/','assets/')) or p=='index.html']
assert all(before[p]==after[p] for p in protected)
patch=''
for p in changes:
 patch+=''.join(difflib.unified_diff((out/'source-before'/p).read_text(encoding='utf-8').splitlines(True),(source/p).read_text(encoding='utf-8').splitlines(True),fromfile='before/'+p,tofile='after/'+p))
(out/'ai-changes.patch').write_text(patch,encoding='utf-8')
report={'before_files':len(before),'after_files':len(after),'changed':changes,'all_other_project_files_unchanged':True,'protected_files':len(protected),'protected_unchanged':True,'after_sha256':after}
(out/'source-audit.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in report.items() if k!='after_sha256'}))
