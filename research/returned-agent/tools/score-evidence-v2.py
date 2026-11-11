from pathlib import Path
import json,sys,statistics
root=Path(__file__).resolve().parents[1];base=root/'outputs/assessment-evidence-v2-2026-11-11'
suite=Path(sys.argv[1]);run=Path(sys.argv[2]);dest=Path(sys.argv[3])
cases=json.loads(suite.read_text(encoding='utf-8'))
oracle={c['id']:c['required_fragments'] for c in json.loads((base/'regression-evidence-oracle.json').read_text(encoding='utf-8'))['cases']}
rows=[]
for c in cases:
 x=json.loads((run/(c['id']+'.json')).read_text(encoding='utf-8')); anchors=c.get('evidence_anchors',oracle.get(c['id']))
 assert anchors is not None and x['expected']==c['expected']
 evidence=(x.get('result') or {}).get('evidence',[None]*3);actual=x['actual'];support=[]
 for i in range(3):
  if actual is None:support.append(False)
  elif not actual[i]:support.append(evidence[i]=='')
  else:support.append(c['expected'][i] and isinstance(evidence[i],str) and evidence[i] in c['answer'] and all(a in evidence[i] for a in anchors[i]))
 rows.append({'id':c['id'],'expected':c['expected'],'actual':actual,'checks_match':x['match'],'evidence_ok':support,'joint_pass':x['match'] and all(support),'evidence':evidence,'ms':x['ms'],'error':x.get('error'),'quote_ratios':[len(evidence[i])/len(c['answer']) for i in range(3) if actual is not None and actual[i] and isinstance(evidence[i],str)]})
lat=sorted(r['ms'] for r in rows if r['ms'] is not None);positive=sum(sum(r['actual']) for r in rows if r['actual'] is not None)
summary={'cases':len(rows),'checks_match':sum(r['checks_match'] for r in rows),'joint_checks_and_evidence':sum(r['joint_pass'] for r in rows),'unavailable':sum(r['actual'] is None for r in rows),'positive_criteria':positive,'unsupported_positive_quotes':sum(sum(not r['evidence_ok'][i] for i,a in enumerate(r['actual']) if a) for r in rows if r['actual'] is not None),'false_credit':sum(sum(a and not e for a,e in zip(r['actual'],r['expected'])) for r in rows if r['actual'] is not None),'missed_credit':sum(sum(e and not a for a,e in zip(r['actual'],r['expected'])) for r in rows if r['actual'] is not None),'grade_failures':[r['id'] for r in rows if not r['checks_match']],'evidence_failures':[r['id'] for r in rows if r['checks_match'] and not r['joint_pass']],'latency_ms':{'median':statistics.median(lat) if lat else None,'max':max(lat) if lat else None},'mean_quote_fraction':statistics.mean([q for r in rows for q in r['quote_ratios']]) if positive else None,'limitation':'Frozen text-coverage oracle plus author labels, not independent teacher validation. Quote length is measured; overly broad quotes may pass coverage.'}
dest.write_text(json.dumps({'summary':summary,'cases':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(summary,ensure_ascii=False))
