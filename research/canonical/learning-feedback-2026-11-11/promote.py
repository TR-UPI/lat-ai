"""Reviewable allowlist promotion; never changes runtime or user databases."""
from pathlib import Path
import hashlib,json,sys,zipfile,shutil
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
MAIN=ROOT/'work/lat-ai'
STAGE=ROOT/'work/learning-feedback-stage/LAD-AI-Document-Pilot'
FILES='''assets/app.js
assets/styles.css
tests/document-pilot-frontend.test.cjs
backend/documents/study_schema.py
backend/documents/study_views.py
backend/documents/test_feedback.py
integration/ai/study-schema.mjs
integration/ai/core/src/local-model.mjs
integration/ai/core/src/tutor.mjs
integration/ai/LOCAL_OVERRIDES.json
integration/ai/test/study.test.mjs
integration/ai/test/study-feedback.test.mjs
README-MAIN.txt'''.splitlines()
sha=lambda b:hashlib.sha256(b).hexdigest()
with zipfile.ZipFile(OUT/'before-source.zip') as z:
    names=z.namelist()
    originals={}
    for rel in FILES:
        matches=[n for n in names if n==rel or n.endswith('/'+rel)]
        assert len(matches)<=1,(rel,matches)
        originals[rel]=z.read(matches[0]) if matches else None
changes=[]
for rel in FILES:
    target=MAIN/rel; source=STAGE/rel
    assert source.is_file(),rel
    before=originals[rel]
    assert (target.read_bytes() if target.exists() else None)==before,'Main changed since snapshot: '+rel
    after=source.read_bytes()
    if before!=after: changes.append(dict(path=rel,before_sha256=sha(before) if before else None,after_sha256=sha(after)))
(OUT/'promotion-plan.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
if '--apply' in sys.argv:
    assert not (OUT/'promotion-applied.json').exists(),'Already applied'
    for item in changes:
        target=MAIN/item['path'];target.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(STAGE/item['path'],target)
        assert sha(target.read_bytes())==item['after_sha256']
    (OUT/'promotion-applied.json').write_text(json.dumps(changes,indent=2),encoding='utf-8')
print(json.dumps({'changed':len(changes),'applied':'--apply' in sys.argv,'runtime_changed':False}))
