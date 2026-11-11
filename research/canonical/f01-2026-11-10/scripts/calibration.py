from pathlib import Path
import hashlib,json
work=Path(__file__).resolve().parent
out=work.parents[1]/'outputs/f01-2026-11-10'
rows=json.loads((out/'responses.json').read_text(encoding='utf8'))
mapping=json.loads((out/'map-private.json').read_text(encoding='utf8'))
cases=sorted({m['case_id'] for m in mapping if m['cohort']=='comparison'},key=lambda c:hashlib.sha256(('F01-calibration/'+c).encode()).hexdigest())[:4]
ids={m['review_id'] for m in mapping if m['case_id'] in cases and m['repeat']==1}
selected=sorted([r for r in rows if r['review_id'] in ids],key=lambda r:r['review_id'])
assert len(selected)==12
(work/'calibration-packet.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2),encoding='utf8')
(out/'calibration-selection.json').write_text(json.dumps({'cases':cases,'algorithm':'first 4 comparison case IDs by SHA256(F01-calibration/+case_id), K/J/S repeat1; selected before reading independent ratings','response_ids':sorted(ids)},ensure_ascii=False,indent=2),encoding='utf8')
print(cases)
