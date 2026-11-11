from pathlib import Path
import json,hashlib,datetime,shutil
work=Path(__file__).resolve().parent
root=work.parents[1]
old=root/'outputs/ai-module-v5-2026-11-09'
out=root/'outputs/f01-2026-11-10'
out.mkdir(exist_ok=True)
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf8')
assert not (out/'freeze.json').exists()
sources=['eval/fact-snapshots.json','eval/comparison-cases.json','eval/contrast-cases.json','logs/comparison.jsonl','logs/contrast.jsonl','eval/comparison-joined-labels.json','eval/contrast-joined-labels.json','eval/rubric.txt','src/fact-ledger.mjs']
baseline=[{'path':p,'sha256':sha(old/p)} for p in sources]
assert all(sha(old/f['path'])==f['sha256'] for f in read(old/'manifest.json')['files'])
snapshots={s['case_id']:s for s in read(old/'eval/fact-snapshots.json')}
main=read(old/'eval/comparison-cases.json');contrast=read(old/'eval/contrast-cases.json')
assert len(main)==51 and len(contrast)==6 and len(snapshots)==57
cases={c['id']:c for c in main+contrast}
dataset=[];mapping=[]
def add(arm,case,repeat,text,path):
 rid='F'+hashlib.sha256(f'f01/{arm}/{case}/{repeat}'.encode()).hexdigest()[:15]
 c=cases[case]
 dataset.append({'review_id':rid,'case_id':case,'question':c['message'],'criterion':c['criterion'],'answer':text,'pipeline_ok':path in ('model','deterministic'),'requested_role':'explain'})
 mapping.append({'review_id':rid,'case_id':case,'arm':arm,'repeat':repeat,'cohort':'comparison' if case in {c['id'] for c in main} else 'contrast'})
for cid,s in snapshots.items():
 add('K',cid,1,'Факты и границы применимости:\n'+'\n'.join(f['text'] for f in s['ledger']['facts']),'deterministic')
for stage in ('comparison','contrast'):
 rows=[json.loads(line) for line in (old/f'logs/{stage}.jsonl').read_text(encoding='utf8').splitlines() if line.strip()]
 assert len(rows)==(306 if stage=='comparison' else 18)
 for r in rows:
  result=r['pipeline'].get('result',{})
  if r['arm']=='J':text=result.get('text','')
  else:
   assert [f['text'] for f in result['facts']]==[f['text'] for f in snapshots[r['case_id']]['ledger']['facts']]
   text='Факты и границы применимости:\n'+'\n'.join(f['text'] for f in result['facts'])+'\nПояснение модели (смысл автоматически не проверен):\n'+result['explanation']['text']
  add(r['arm'],r['case_id'],r['repeat'],text,r['pipeline']['path'])
assert len(dataset)==381 and len({r['review_id'] for r in dataset})==381
case_order=sorted(cases,key=lambda cid:hashlib.sha256(('f01cases/'+cid).encode()).hexdigest())
# 17 main + 2 contrast each, balanced by source cohort, no mode-specific grader.
groups=[set() for _ in range(3)]
for cohort in (main,contrast):
 ordered=sorted((c['id'] for c in cohort),key=lambda cid:hashlib.sha256(('f01split/'+cid).encode()).hexdigest())
 for i,cid in enumerate(ordered):groups[i%3].add(cid)
for i,group in enumerate(groups,1):
 subset=sorted((r for r in dataset if r['case_id'] in group),key=lambda r:r['review_id'])
 write(work/f'packet-{i}.json',subset)
assert sum(len(g) for g in groups)==57
write(out/'responses.json',dataset);write(out/'map-private.json',mapping)
shutil.copy2(work/'PROTOCOL.txt',out/'PROTOCOL.txt')
tracked=[]
for p in sorted((root/'work/lat-ai').rglob('*')):
 if p.is_file() and not any(x in {'.git','.runtime','__pycache__','node_modules'} for x in p.parts):tracked.append({'path':p.relative_to(root/'work/lat-ai').as_posix(),'sha256':sha(p)})
write(out/'source-before.json',tracked)
write(out/'freeze.json',{'created_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'protocol_sha256':sha(out/'PROTOCOL.txt'),'sources':baseline,'historical_manifest_files_verified':len(read(old/'manifest.json')['files']),'response_count':len(dataset),'dataset_sha256':sha(out/'responses.json'),'packet_sha256':{str(i):sha(work/f'packet-{i}.json') for i in range(1,4)},'new_inference_calls':0,'masking':'partial; format visible'})
print(json.dumps({'responses':len(dataset),'groups':[len(g) for g in groups],'packet_rows':[len(read(work/f'packet-{i}.json')) for i in range(1,4)],'source_files':len(tracked)}))
