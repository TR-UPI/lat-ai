"""Read-only post-process audit; never unloads models or removes locks."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,urllib.request
ROOT=Path(__file__).resolve().parent.parent
BASE=ROOT/'outputs/u02-runtime-controls-2026-11-11'
OUT=ROOT/'outputs/sdk-fix-and-history-scan-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
assert read(BASE/'known128-run-summary.json')['complete']
plan=read(BASE/'known128-plan.json');instances=[];locks=[]
for n in [1,2,3]:
    folder=BASE/f'known128-live-{n}';s=read(folder/'summary.json')
    assert s['status']=='complete' and s['retirement_proven']
    first=read(folder/f'R{n}-{plan["execution_orders"][n-1][0]}.json');instances.append(first['instance'])
    lock=folder/'model.lock';locks.append({'series':n,'exists':lock.exists(),'sha256':hashlib.sha256(lock.read_bytes()).hexdigest() if lock.exists() else None,'action':'preserved; no deletion'})
assert len(set(instances))==3
with urllib.request.urlopen('http://127.0.0.1:1234/api/v1/models',timeout=5) as response:
    body=response.read();status=response.status
assert status==200
metadata=json.loads(body);loaded=[i['id'] for m in metadata['models'] for i in m.get('loaded_instances',[])]
with (OUT/'scan-models-after.json').open('xb') as f:f.write(body)
result={'utc':datetime.now(timezone.utc).isoformat(),'http_status':status,'metadata_sha256':hashlib.sha256(body).hexdigest(),'scan_instances':instances,'all_scan_instances_absent':all(i not in loaded for i in instances),'loaded_instance_ids':loaded,'locks':locks,'model_or_lock_mutations':False}
with (OUT/'scan-retirement-audit.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False));assert result['all_scan_instances_absent']
