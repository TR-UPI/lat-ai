"""Build this computer's disposable runtime copy; never edit project sources."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
from datetime import datetime

root = Path(__file__).resolve().parents[1]
source = root / 'lat-ai'
config_path = root / 'work/local-pc/profile.json'
config = json.loads(config_path.read_text(encoding='utf-8-sig'))
if config['machine'].casefold() != socket.gethostname().casefold():
    raise SystemExit('This profile belongs to another computer; use the original profile.')
budget, minimum = config['model_budget_ms'], config['minimum_generation_ms']
transport, browser = config['worker_timeout_seconds'], config['browser_timeout_ms']
assert all(type(x) is int for x in [budget,minimum,transport,browser])
assert 8000 <= budget <= 180000 and 4000 <= minimum < budget
assert budget + 5000 <= transport * 1000 and transport * 1000 + 5000 <= browser <= 210000
dest = root / 'work/local-pc/builds' / datetime.now().strftime('%Y%m%d-%H%M%S-%f')
dest.mkdir(parents=True,exist_ok=False)
paths = subprocess.check_output(['git','-c','safe.directory='+source.as_posix(),'-C',str(source),'ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
manifest = []
for name in sorted(set(filter(None, paths))):
    src = source / name
    if not src.is_file():
        continue
    assert src.resolve().is_relative_to(source.resolve())
    target = dest / name
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(src,target)
    manifest.append({'path':name,'source_sha256':hashlib.sha256(src.read_bytes()).hexdigest()})

def replace(path, before, after):
    file = dest / path
    text = file.read_text(encoding='utf-8')
    if text.count(before) != 1:
        raise RuntimeError('Source changed; review local override: ' + path)
    file.write_text(text.replace(before,after),encoding='utf-8')

replace('integration/ai/core/src/tutor.mjs', 'modelBudgetMs<=8000', f'modelBudgetMs<={budget}')
replace('integration/ai/lifecycle.mjs', 'const tutorOptions={log,modelBudgetMs:7900};', f'const tutorOptions={{log,modelBudgetMs:{budget},minimumGenerationMs:{minimum}}};')
replace('integration/ai/lifecycle.mjs', '// Leave 100 ms of the 8 s module budget for timer delivery and response work.', '// THIS COMPUTER ONLY: generated timeout profile; original defaults stay unchanged.')
replace('backend/tutor/transport.py', 'opener.open(request,timeout=9)', f'opener.open(request,timeout={transport})')
replace('assets/data.js', "{method:'POST',body,timeoutMs:10000}", f"{{method:'POST',body,timeoutMs:{browser}}}")
replace('assets/data.js', "{ method: 'POST', body: { exercise: id, answer: text } }", f"{{ method: 'POST', body: {{ exercise: id, answer: text }}, timeoutMs: {browser} }}")
# requestTimeout controls inbound request transfer, not response generation. Keep it 10 s.
overrides_path = dest / 'integration/ai/LOCAL_OVERRIDES.json'
overrides = json.loads(overrides_path.read_text(encoding='utf-8'))
for row in overrides:
    if row['path'] == 'src/tutor.mjs':
        row['sha256'] = hashlib.sha256((dest/'integration/ai/core/src/tutor.mjs').read_bytes()).hexdigest()
        row['reason'] += '; generated runtime profile for this computer only'
overrides_path.write_text(json.dumps(overrides,indent=2)+'\n',encoding='utf-8')
# Embedded Python ignores PYTHONPATH and script directories; select this backend explicitly.
(dest/'run-local-django.py').write_text("import sys,runpy\nfrom pathlib import Path\np=Path(__file__).resolve().parent/'backend'\nsys.path.insert(0,str(p))\nrunpy.run_path(str(p/'manage.py'),run_name='__main__')\n",encoding='utf-8')
deps=source/'integration/ai/node_modules'
if deps.is_dir():
    shutil.copytree(deps,dest/'integration/ai/node_modules')
for row in manifest:
    row['runtime_sha256']=hashlib.sha256((dest/row['path']).read_bytes()).hexdigest()
    row['locally_modified']=row['runtime_sha256']!=row['source_sha256']
result={'machine':config['machine'],'source':str(source),'build':str(dest),'config':config,'files':manifest}
(dest/'LOCAL_PROFILE.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'build':str(dest),'source_files':len(manifest),'changed_files':[x['path'] for x in manifest if x['locally_modified']]}))
