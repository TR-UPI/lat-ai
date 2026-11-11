from pathlib import Path
import json, hashlib, shutil, zipfile
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
MAIN=ROOT/'work/lat-ai'
STAGE=ROOT/'work/main-integration-stage'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
manifest=json.loads((OUT/'promotion-manifest.json').read_text())
with zipfile.ZipFile(OUT/'main-source-before.zip') as backup:
    for name in backup.namelist():
        assert (MAIN/name).read_bytes() in (backup.read(name),(STAGE/name).read_bytes()),('Main changed during verification',name)
files=[row['path'] for row in manifest['files']]+['START_MAIN.cmd','tools/start-main.ps1','README-MAIN.txt','docs/ai/INTEGRATED_WORK.txt']
for name in files:
    target=MAIN/name
    if name not in [r['path'] for r in manifest['files']] and target.exists(): assert sha(target)==sha(STAGE/name),('Extra collision',name)
    target.parent.mkdir(parents=True,exist_ok=True)
    shutil.copy2(STAGE/name,target)
    assert sha(target)==sha(STAGE/name)
# Use existing dependencies; do not replace or remove user runtime/database files.
for path in (STAGE/'integration/ai/node_modules').rglob('*'):
    if path.is_file():
        if path.name=='.package-lock.json': continue  # npm's installation metadata is not a dependency payload.
        target=MAIN/path.relative_to(STAGE)
        if target.exists(): assert sha(path)==sha(target),('Dependency mismatch',str(path))
        else: target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,target)
config={'runtime':str(ROOT/'work/tf11kit/app/.runtime/i02'),
        'python':str(ROOT/'work/tester-release/LAD AI Windows/runtime/python/python.exe'),
        'node':'C:/Program Files/nodejs/node.exe',
        'python_extra_site':str(MAIN/'.runtime/document-parsers')}
cfg=MAIN/'.runtime/main-local.json'
assert not cfg.exists(),'Do not replace local deployment config'
cfg.write_text(json.dumps(config,indent=2),encoding='utf-8')
entries=[{'path':name,'sha256':sha(MAIN/name)} for name in files]
(OUT/'promoted-source.json').write_text(json.dumps({'files':entries,'total':len(entries),'source_only':True,'runtime_selected':config['runtime'],'deleted_files':0},indent=2),encoding='utf-8')
print(json.dumps({'promoted_files':len(entries),'deleted_files':0,'old_runtime_unchanged':True,'selected_existing_runtime':config['runtime']}))
