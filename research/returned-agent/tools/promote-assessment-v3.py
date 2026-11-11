from pathlib import Path
import json,hashlib,shutil,subprocess,difflib
root=Path(__file__).resolve().parents[1];base=root/'outputs/assessment-v3-2026-11-11';dest=root/'lat-ai'
before={r['path']:r['sha256'] for r in json.loads((base/'source-before.json').read_text(encoding='utf-8'))}
groups={
'work/assessment-v3d-2026-11-11':[
'integration/ai/core/src/assessment.mjs','integration/ai/core/src/assessment-evidence-context.mjs','integration/ai/core/src/local-model.mjs','integration/ai/core/data/assessment-rubrics.json','integration/ai/LOCAL_OVERRIDES.json','integration/ai/test/assessment-evidence-context.test.mjs','docs/ai/ASSESSMENT_EVIDENCE_V3.md'],
'work/ai-receipt-2026-11-11':[
'integration/ai/assessment-bridge.mjs','integration/ai/assessment-receipt.mjs','integration/ai/bridge.mjs','integration/ai/worker-http.mjs','integration/ai/test/assessment-receipt.test.mjs','integration/ai/test/receipt-crash.fixture.mjs','docs/ai/ASSESSMENT_RECEIPT.md']}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
frozen=json.loads((base/'candidate-d-freeze.json').read_text(encoding='utf-8-sig'))
for row in frozen['files']:assert sha(root/'work/assessment-v3d-2026-11-11'/row['path'])==row['sha256']
assert sha(base/'holdout32.json')==frozen['holdout_sha256']
assert (base/'holdout32/summary.json').is_file(),'Finish frozen evaluation before promotion'
for folder,paths in groups.items():
 for p in paths:
  assert p.startswith(('integration/ai/','docs/ai/'))
  if p in before:assert sha(dest/p)==before[p],f'Concurrent source change: {p}'
  else:assert not (dest/p).exists(),p
for folder,paths in groups.items():
 for p in paths:shutil.copy2(root/folder/p,dest/p)
paths=subprocess.check_output(['git','-c','safe.directory='+dest.as_posix(),'-C',str(dest),'ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
after={p:sha(dest/p) for p in sorted(set(filter(None,paths))) if (dest/p).is_file()}
changed=[p for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)]
allowed={p for paths in groups.values() for p in paths};assert set(changed)<=allowed
protected=[p for p in before if p.startswith(('backend/','assets/')) or p=='index.html'];assert all(after.get(p)==before[p] for p in protected)
patch=[]
for p in changed:
 old=(base/'source-before'/p).read_text(encoding='utf-8-sig').splitlines(keepends=True) if p in before else []
 new=(dest/p).read_text(encoding='utf-8-sig').splitlines(keepends=True)
 patch.extend(difflib.unified_diff(old,new,fromfile='before/'+p,tofile='after/'+p))
(base/'ai-changes.patch').write_text(''.join(patch),encoding='utf-8')
result=dict(before_files=len(before),after_files=len(after),changes=[{'path':p,'before':before.get(p),'after':after.get(p)} for p in changed],protected_files=len(protected),protected_unchanged=True,frozen_candidate_unchanged=True,holdout_sha256_unchanged=True)
(base/'source-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='changes'}));print('\n'.join(changed))
