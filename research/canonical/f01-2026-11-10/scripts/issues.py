from pathlib import Path
import json,sys
out=Path(__file__).resolve().parents[2]/'outputs/f01-2026-11-10'
mode=sys.argv[1]
if mode=='accuracy':
 rows=json.loads((out/'accuracy-review-queue.json').read_text(encoding='utf8'))
 for i,r in list(enumerate(rows))[int(sys.argv[2]):int(sys.argv[3])]:
  answer=r['answer'].split('Пояснение модели (смысл автоматически не проверен):\n')[-1]
  print(f"{i}. {r['case_id']} {r['arm']}{r['repeat']} {r['review_id']} {r['A']}{r['C']}{r['U']}{r['R']} old={r['historical_semantic_label']}\nQ {r['question']}\nANSWER {answer}\nREASON {r['reason']}\n")
else:
 for r in json.loads((out/'k-rating-disagreements.json').read_text(encoding='utf8')):print(json.dumps(r,ensure_ascii=False))
