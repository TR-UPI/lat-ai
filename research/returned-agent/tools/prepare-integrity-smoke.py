from pathlib import Path
import json,hashlib
root=Path(__file__).resolve().parent.parent;out=root/'outputs/ai-pilot-integrity-2026-11-11';folder=out/'synthetic-frozen';folder.mkdir(exist_ok=False)
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
known=read(root/'outputs/assessment-v3-2026-11-11/regression128-with-evidence.json')+read(root/'outputs/assessment-v3-2026-11-11/holdout32.json')
cases=[{**next(c for c in known if c['id']==key),'id':key} for key in ['V11','U02']]
files={name+'.frozen.json':{'synthetic_smoke_only':True,'no_human_review_claimed':True} for name in ['responses','review-A','review-B','adjudication']}
files['primary-cases.json']=cases
for n in range(1,4):files[f'repeat{n}.json']=[{**c,'id':f'R{n}-'+c['id'],'source_id':c['id'],'repeat':n} for c in cases]
hashes={}
for name,value in files.items():
 p=folder/name;p.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');hashes[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(folder/'freeze.json').write_text(json.dumps({'data_origin':'synthetic_smoke','unique_cases':len(cases),'sha256':hashes['primary-cases.json'],'files_sha256':hashes,'scope':'Known V11/U02. Plumbing/repeat smoke test only; no new holdout and no real students.'},indent=2),encoding='utf-8')
(out/'run-settings.json').write_text(json.dumps({'model_key':'qwen3.5-9b','environment_note':'Existing local RTX2050 4GB PC; local60s budget, sequential calls. No project-wide limit changes.','model_identity_note':'Existing LM Studio qwen3.5-9b model, no weights downloaded/changed; model key declaration, not independently hashed weights.'},indent=2),encoding='utf-8')
print('Frozen2 known synthetic cases,3 series; no human labels claimed.')
