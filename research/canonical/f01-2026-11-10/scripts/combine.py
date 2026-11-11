from pathlib import Path
import json,hashlib,collections,statistics
work=Path(__file__).resolve().parent
out=work.parents[1]/'outputs/f01-2026-11-10'
old=work.parents[1]/'outputs/ai-module-v5-2026-11-09'
def read(p):return json.loads(p.read_text(encoding='utf8'))
def write(p,x):p.write_text(json.dumps(x,ensure_ascii=False,indent=2),encoding='utf8')
responses={r['review_id']:r for r in read(out/'responses.json')}
mapping={r['review_id']:r for r in read(out/'map-private.json')}
ratings=[]
for i in range(1,4):
 packet=read(work/f'packet-{i}.json');rs=read(work/f'ratings-{i}.json')
 assert len(rs)==127 and {r['review_id'] for r in rs}=={r['review_id'] for r in packet}
 for r in rs:
  assert all(type(r[k]) is int and r[k] in (0,1,2) for k in 'ACUR'),r
  assert r['disclosure']=='NA' and len(r['reason'])>10
  if r['A']<2:assert r['evidence'] and r['evidence'] in responses[r['review_id']]['answer'],r
  ratings.append({**r,'reviewer':i})
assert len({r['review_id'] for r in ratings})==381
write(out/'independent-ratings.json',ratings)
joined=[{**r,**mapping[r['review_id']]} for r in ratings]
primary={r['review_id']:r for r in read(work/'primary-k-ratings.json')}
differences=[{'review_id':r['review_id'],'case_id':r['case_id'],'reviewer':r['reviewer'],'independent':{k:r[k] for k in 'ACUR'},'primary':{k:primary[r['review_id']][k] for k in 'ACUR'},'independent_reason':r['reason'],'primary_reason':primary[r['review_id']]['reason']} for r in joined if r['arm']=='K' and any(r[k]!=primary[r['review_id']][k] for k in 'ACUR')]
write(out/'k-rating-disagreements.json',differences)
prior={}
for stage in ('comparison','contrast'):
 for r in read(old/f'eval/{stage}-joined-labels.json'):prior[(r['case_id'],r['arm'],r['repeat'])]=r['composite_label']
issues=[]
for r in joined:
 historical=prior.get((r['case_id'],r['arm'],r['repeat']))
 if r['A']<2 or (historical=='critical' and r['A']!=0):
  response=responses[r['review_id']]
  issues.append({**r,'historical_semantic_label':historical,'question':response['question'],'criterion':response['criterion'],'answer':response['answer']})
write(out/'accuracy-review-queue.json',issues)
duplicates=collections.defaultdict(list)
for r in joined:duplicates[(r['case_id'],responses[r['review_id']]['answer'])].append(r)
inconsistent=[[{'review_id':r['review_id'],**{k:r[k] for k in 'ACUR'}} for r in rs] for rs in duplicates.values() if len({tuple(r[k] for k in 'ACUR') for r in rs})>1]
write(out/'duplicate-disagreements.json',inconsistent)
print(json.dumps({'ratings':len(ratings),'accuracy_queue':len(issues),'k_disagreements':len(differences),'duplicate_disagreements':len(inconsistent)}))
