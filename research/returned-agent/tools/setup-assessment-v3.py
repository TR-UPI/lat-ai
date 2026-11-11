from pathlib import Path
import json,hashlib,subprocess,shutil
from datetime import datetime,timezone
root=Path(__file__).resolve().parents[1];src=root/'lat-ai';out=root/'outputs/assessment-v3-2026-11-11'
out.mkdir(exist_ok=False)
paths=subprocess.check_output(['git','-c','safe.directory='+src.as_posix(),'-C',str(src),'ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
manifest=[]
for p in sorted(set(filter(None,paths))):
 f=src/p
 if not f.is_file():continue
 dst=out/'source-before'/p;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(f,dst)
 manifest.append({'path':p,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()})
(out/'source-before.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
old=root/'outputs/assessment-evidence-v2-2026-11-11'
cases=json.loads((old/'regression96.json').read_text(encoding='utf-8'))+json.loads((old/'holdout32.json').read_text(encoding='utf-8'))
(out/'regression128.json').write_text(json.dumps(cases,ensure_ascii=False,indent=2),encoding='utf-8')
ids={'N05','U15','U02','U26','H18','L1.types.1-6','N08','N18','N21','U29','U32','U48','U22','U46','H14','H30'}
(out/'probe16.json').write_text(json.dumps([c for c in cases if c['id'] in ids],ensure_ascii=False,indent=2),encoding='utf-8')
(out/'WORKLOG.txt').write_text('LAT AI v3 — '+datetime.now(timezone.utc).isoformat()+'\n01. Snapshot202 source files; current instructions/roadmap read. Sequence: atomic evidence + paraphrases; stability; fresh frozen holdout; read-only AI receipt recovery; teacher/manual gate. Existing backend/frontend dirty tree preserved.\n',encoding='utf-8')
print(json.dumps({'source_files':len(manifest),'regression':len(cases),'out':str(out)}))
