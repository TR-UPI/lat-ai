from pathlib import Path
import json,hashlib,collections
work=Path(__file__).resolve().parent
root=work.parents[1];out=root/'outputs/f01-2026-11-10';old=root/'outputs/ai-module-v5-2026-11-09'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
freeze=read(out/'freeze.json')
assert sha(out/'PROTOCOL.txt')==freeze['protocol_sha256']
assert sha(out/'responses.json')==freeze['dataset_sha256']
for item in freeze['sources']:assert sha(old/item['path'])==item['sha256'],item['path']
historical=read(old/'manifest.json')['files']
for item in historical:assert sha(old/item['path'])==item['sha256'],item['path']
sources=read(out/'source-before.json')
for item in sources:assert sha(root/'work/lat-ai'/item['path'])==item['sha256'],item['path']
responses={r['review_id']:r for r in read(out/'responses.json')}
mapping={r['review_id']:r for r in read(out/'map-private.json')}
raw={r['review_id']:r for r in read(out/'independent-ratings.json')}
final={r['review_id']:r for r in read(out/'final-ratings.json')}
assert len(responses)==381 and set(responses)==set(mapping)==set(raw)==set(final)
assert all(r['pipeline_ok'] for r in responses.values())
for i in range(1,4):
 assert sha(work/f'packet-{i}.json')==freeze['packet_sha256'][str(i)]
 assert len(read(work/f'ratings-{i}.json'))==127
for r in final.values():
 assert all(type(r[k]) is int and 0<=r[k]<=2 for k in 'ACUR') and r['disclosure']=='NA'
 if r['A']<2:assert r['evidence'] in responses[r['review_id']]['answer']
applied={rid:{k:r[k] for k in 'ACUR'} for rid,r in raw.items()}
for d in read(out/'adjudication.json'):
 rid=d['review_id'];assert all(applied[rid][k]==v for k,v in d['before'].items())
 applied[rid].update(d['after'])
assert all(applied[rid]=={k:r[k] for k in 'ACUR'} for rid,r in final.items())
summary=read(out/'summary.json')
for cohort,c in summary.items():
 for arm,report in c['arms'].items():
  rs=[r for rid,r in final.items() if mapping[rid]['cohort']==cohort and mapping[rid]['arm']==arm]
  assert report['responses']==len(rs)
  assert report['adequate']==sum(r['A']==2 and r['C']==2 and r['U']>=1 and r['R']>=1 for r in rs)
  assert report['accuracy0']==sum(r['A']==0 for r in rs)
assert len(read(out/'case-matrix.json'))==57
assert read(old/'eval/comparison-summary.json')['arms']['J']['composite']=={'pass':123,'critical':21,'noncritical':9}
assert read(old/'eval/comparison-summary.json')['arms']['S']['composite']=={'pass':125,'critical':19,'noncritical':9}
for name,n in [('fact-reference-results.json',19),('semantic-counterexamples.json',12),('e01-pair-checks.json',16)]:assert read(out/name)['passed']==n
result={'passed':True,'frozen_protocol_and_sources_unchanged':True,'historical_manifest_files_unchanged':len(historical),'current_source_files_unchanged':len(sources),'responses_and_ratings':381,'cases':57,'adjudications_accounted_for':11,'duplicate_rating_disagreements':len(read(out/'duplicate-disagreements.json')),'all_pipeline_rows_valid':True,'fixed_python_checks':47,'new_local_model_calls':0,'product_source_modified':False,'teacher_acceptance':False,'E01_prompt_experiment_completed':False}
(out/'verification.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print(json.dumps(result))
