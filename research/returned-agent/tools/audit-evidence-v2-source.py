from pathlib import Path
import hashlib,json,subprocess,difflib
root=Path(__file__).resolve().parents[1];source=root/'lat-ai';base=root/'outputs/assessment-evidence-v2-2026-11-11'
allowed={
 'integration/ai/core/src/assessment.mjs',
 'integration/ai/core/src/assessment-verifier.mjs',
 'integration/ai/core/src/local-model.mjs',
 'integration/ai/core/data/assessment-rubrics.json',
 'integration/ai/core/data/assessment-verifier-rubrics.json',
 'integration/ai/LOCAL_OVERRIDES.json',
 'integration/ai/test/assessment.test.mjs',
 'integration/ai/test/assessment-spans.test.mjs',
 'integration/ai/test/assessment-verification.test.mjs',
 'docs/ai/ASSESSMENT_EVIDENCE_V2.md',
}
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
before={r['path']:r['sha256'] for r in json.loads((base/'source-before.json').read_text(encoding='utf-8-sig'))}
paths=subprocess.check_output(['git','-c','safe.directory='+source.as_posix(),'-C',str(source),'ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
after={p:sha(source/p) for p in sorted(set(filter(None,paths))) if (source/p).is_file()}
changes=[{'path':p,'before':before.get(p),'after':after.get(p)} for p in sorted(before.keys()|after.keys()) if before.get(p)!=after.get(p)]
assert set(r['path'] for r in changes)<=allowed,changes
assert not any(r['after'] is None for r in changes)
frozen=json.loads((base/'candidate-h-freeze.json').read_text(encoding='utf-8-sig'))
for r in frozen['files']:assert sha(source/r['path'])==r['sha256'],r['path']
assert sha(base/'holdout32.json')==frozen['holdout_sha256']
protected=[p for p in before if p.startswith(('backend/','assets/')) or p=='index.html']
assert all(after.get(p)==before[p] for p in protected)
result={'before_files':len(before),'after_files':len(after),'changed_files':changes,'protected_backend_frontend_files':len(protected),'protected_unchanged':True,'candidate_code_matches_pre_holdout_freeze':True,'holdout_sha256_unchanged':True}
(base/'source-audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
patch=[]
for r in changes:
 p=r['path'];old=(base/'source-before'/p).read_text(encoding='utf-8').splitlines(keepends=True) if r['before'] else []
 new=(source/p).read_text(encoding='utf-8').splitlines(keepends=True)
 patch.extend(difflib.unified_diff(old,new,fromfile='before/'+p,tofile='after/'+p))
(base/'ai-changes.patch').write_text(''.join(patch),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='changed_files'},ensure_ascii=False))
print('\n'.join(r['path'] for r in changes))
