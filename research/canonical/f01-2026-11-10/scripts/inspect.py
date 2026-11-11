from pathlib import Path
import json,sys
work=Path(__file__).resolve().parent
out=work.parents[1]/'outputs/f01-2026-11-10'
rows=json.loads((out/'responses.json').read_text(encoding='utf8'))
mapping={m['review_id']:m for m in json.loads((out/'map-private.json').read_text(encoding='utf8'))}
mode=sys.argv[1]
if mode=='K':selected=[r for r in rows if mapping[r['review_id']]['arm']=='K'][int(sys.argv[2]):int(sys.argv[3])]
elif mode=='case':selected=[r for r in rows if r['case_id'] in sys.argv[2:]]
else:raise ValueError(mode)
for r in selected:
 m=mapping[r['review_id']]
 print(f"\n{r['case_id']} {m['arm']} {m['repeat']} {r['review_id']}\nQ: {r['question']}\nCriterion: {r['criterion']}\n{r['answer']}\n")
