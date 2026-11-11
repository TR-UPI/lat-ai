"""Read-only progress, never loads a model or changes experiment artifacts."""
from pathlib import Path
import json
root=Path(__file__).resolve().parent.parent;base=root/'outputs/u02-runtime-controls-2026-11-11'
result=[]
for n in [1,2,3]:
    folder=base/f'known128-live-{n}';events=[]
    path=folder/'events.jsonl'
    if path.exists():
        for line in path.read_text(encoding='utf-8-sig').splitlines():
            try:events.append(json.loads(line))
            except json.JSONDecodeError:pass # Writer may be in the final line.
    cases=[e for e in events if e.get('event')=='case'];errors=[e for e in events if e.get('event') in ['run_error','stopped_unknown','retirement_error']]
    summary=None
    if (folder/'summary.json').exists():
        try:summary=json.loads((folder/'summary.json').read_text(encoding='utf-8-sig'))
        except json.JSONDecodeError:pass
    result.append({'series':n,'completed_cases':len(cases),'last_case':cases[-1]['id'] if cases else None,'last_event_utc':events[-1]['at'] if events else None,'status':summary['status'] if summary else 'running' if events else 'not_started','errors':errors,'retirement_proven':summary.get('retirement_proven') if summary else None})
print(json.dumps({'total_completed':sum(r['completed_cases'] for r in result),'planned':384,'series':result},ensure_ascii=False))
