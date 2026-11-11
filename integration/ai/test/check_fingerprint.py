"""Cross-language digest check for already validated fixture inputs, NOT a validator."""
from pathlib import Path
import json,hashlib
fixtures=Path(__file__).resolve().parents[3]/'contracts'/'examples'/'fingerprint-vectors.json'
vectors=json.loads(fixtures.read_text(encoding='utf8'))['vectors']
for v in vectors:
    body=dict(v['request'])
    body.setdefault('mode','internal');body.setdefault('document_ids',[]);body.setdefault('exercise_id',None)
    for key in ('course_id','lesson_id','exercise_id'):
        if body[key] is not None:body[key]=int(body[key])
    if 'code_context' in body:
        c=dict(body['code_context']);c['revision']=int(c['revision'])
        if c['selection'] is not None:c['selection']={k:int(n) for k,n in c['selection'].items()}
        body['code_context']=c
    canonical=json.dumps(body,ensure_ascii=False,separators=(',',':'),sort_keys=True,allow_nan=False)
    assert body==v['normalized'],v['id']
    assert canonical==v['canonical_json'],v['id']
    assert hashlib.sha256(canonical.encode('utf8')).hexdigest()==v['sha256'],v['id']
print(json.dumps({'python_canonical_vectors':len(vectors),'passed':len(vectors),'stdlib_only':True}))
