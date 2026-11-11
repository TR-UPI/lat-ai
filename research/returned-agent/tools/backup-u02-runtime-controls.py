from pathlib import Path
import json,hashlib,zipfile
root=Path(__file__).resolve().parent.parent
out=root/'outputs/u02-runtime-controls-2026-11-11';backup=out/'backup'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
inventory=read(out/'source-audit.json')['after_sha256'];files={}
for name,digest in inventory.items():
    assert not name.startswith(('.git/','.runtime/'))
    p=root/'lat-ai'/name;assert sha(p)==digest;files['lat-ai/'+name]=p
for name in ['AGENTS.md','START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md']:
    files[name]=root/name
for p in (root/'tools').iterdir():
    if p.is_file():files[p.relative_to(root).as_posix()]=p
for p in out.rglob('*'):
    if p.is_file() and backup not in p.parents and p.suffix!='.zip':files[p.relative_to(root).as_posix()]=p
for name in ['package.json','package-lock.json','node_modules/@lmstudio/sdk/dist/index.mjs','node_modules/@lmstudio/sdk/dist/index.d.ts']:
    p=root/'work/u02-runtime-sdk'/name;files[p.relative_to(root).as_posix()]=p
for name in ['work/local-pc/profile.json']:
    files[name]=root/name
manifest={name:sha(p) for name,p in sorted(files.items())}
with (backup/'source-and-evidence-manifest.json').open('x',encoding='utf-8') as f:json.dump(manifest,f,indent=2)
archive=backup/'LAT-AI-RUNTIME-CONTROLS-SOURCE-AND-EVIDENCE.zip'
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
    for name,p in sorted(files.items()):z.write(p,name)
with zipfile.ZipFile(archive) as z:
    assert z.testzip() is None and set(z.namelist())==set(manifest)
    for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
audit={'source_files_unchanged':len(inventory),'backup_files':len(manifest),'backup_zip':archive.name,'backup_sha256':sha(archive),'all_backup_entries_verified':True,'git_bundle_sha256':sha(backup/'LAT-AI-GIT.bundle'),'git_bundle_verified':True,'manual_zip':read(out/'manual-package-audit.json'),'scope':'209 project source files plus root tools/docs/current evidence and pinned SDK source. No weights, runtime DB, IPC credentials or .git working metadata. Git history is in separate bundle. No commit or push.'}
with (out/'package-audit.json').open('x',encoding='utf-8') as f:json.dump(audit,f,ensure_ascii=False,indent=2)
print(json.dumps(audit,ensure_ascii=False))
