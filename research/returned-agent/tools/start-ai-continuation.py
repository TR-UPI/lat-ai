from pathlib import Path
import subprocess,hashlib,json,shutil
root=Path(__file__).resolve().parent.parent
out=root/'outputs/ai-continuation-2026-11-11'
out.mkdir(exist_ok=False)
source=root/'lat-ai'
names=subprocess.check_output(['git','ls-files','-c','-o','--exclude-standard','-z'],cwd=source).decode().split('\0')
manifest={}
for name in sorted(set(filter(None,names))):
 p=source/name
 if p.is_file():
  target=out/'source-before'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
  manifest[name]=hashlib.sha256(p.read_bytes()).hexdigest()
(out/'source-before.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
(out/'WORKLOG.txt').write_text('2026-11-11: User requested AI continuation and separate human-review ZIP. Read active instructions and v3 evidence. Historical f01-review/frozen-inputs path absent; canonical context found in f01-2026-11-10/frozen-inputs. No archive mutations.\n',encoding='utf-8')
fixtures={'positive':['x := 2','x: 2','x = 2','x равен 2'],'negative':['x == 2','x != 2','x <= 2','x = 20','x = 2.5','x := 2.5','x = 2e3','x = 2_000'],'scope':'Deterministic development fixtures, NOT a new model holdout. Only citation completion; decisions unchanged.'}
data=json.dumps(fixtures,ensure_ascii=False,indent=2).encode('utf-8');(out/'syntax-fixtures.json').write_bytes(data)
(out/'syntax-fixtures.sha256').write_text(hashlib.sha256(data).hexdigest(),encoding='ascii')
print(json.dumps({'snapshot_files':len(manifest),'report':str(out)}))
