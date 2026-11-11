"""Descriptive assessment metrics; repetitions never enlarge the primary sample."""
import json,math,sys,statistics
from pathlib import Path

def binomial_cdf(k,n,p):
    if p<=0:return 1.0
    if p>=1:return 1.0 if k>=n else 0.0
    logs=[math.lgamma(n+1)-math.lgamma(i+1)-math.lgamma(n-i+1)+i*math.log(p)+(n-i)*math.log1p(-p) for i in range(k+1)]
    peak=max(logs);return min(1.0,math.exp(peak)*sum(math.exp(x-peak) for x in logs))

def error_upper95(errors,graded):
    if graded==0:return None
    if errors==graded:return 1.0
    if errors==0:return 1-math.pow(.05,1/graded)
    low=errors/graded;high=1.0
    for _ in range(70):
        mid=(low+high)/2
        if binomial_cdf(errors,graded,mid)>.05:low=mid
        else:high=mid
    return (low+high)/2

def summarize(rows):
    scored=[r for r in rows if r['actual'] is not None];errors=sum(r['actual']!=r['expected'] for r in scored)
    return dict(cases=len(rows),graded=len(scored),correct=len(scored)-errors,wrong=errors,abstentions=len(rows)-len(scored),coverage=len(scored)/len(rows) if rows else None,error_rate=errors/len(scored) if scored else None,one_sided_exact95_error_upper=error_upper95(errors,len(scored)))

def analyze(cases_path,run_path):
    cases=json.loads(Path(cases_path).read_text(encoding='utf-8-sig'));rows=[]
    for c in cases:
        r=json.loads((Path(run_path)/(c['id']+'.json')).read_text(encoding='utf-8-sig'))
        assert r['expected']==c['expected']
        rows.append({**r,'category':c.get('category','unspecified'),'task_key':c['task_key'],'source_id':c.get('source_id',c['id'])})
    seen=set();first=[]
    for r in rows:
        if r['source_id'] not in seen:first.append(r);seen.add(r['source_id'])
    groups={key:[r for r in rows if r['source_id']==key] for key in seen}
    stability=[dict(id=key,repeats=len(items),outcomes=len({json.dumps(r['actual']) for r in items}),evidence_variants=len({json.dumps((r.get('result') or {}).get('evidence')) for r in items}),**summarize(items)) for key,items in sorted(groups.items())]
    ms=[r['ms'] for r in rows if r.get('ms') is not None]
    result=dict(primary_unique_first_occurrence=summarize(first),all_calls_descriptive=summarize(rows),by_category={k:summarize([r for r in first if r['category']==k]) for k in sorted({r['category'] for r in first})},by_task={k:summarize([r for r in first if r['task_key']==k]) for k in sorted({r['task_key'] for r in first})},stability=stability,latency_ms=dict(median=statistics.median(ms) if ms else None,max=max(ms) if ms else None),limitations='Exact one-sided95 binomial upper bound assumes independent representative cases and reliable labels. Synthetic/development cases do not establish population performance. Repeated responses are correlated and never enlarge primary n. Categories and datasets must not be pooled silently.')
    return result

if __name__=='__main__':
    result=analyze(sys.argv[1],sys.argv[2]);Path(sys.argv[3]).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');print(json.dumps(result['primary_unique_first_occurrence']))
