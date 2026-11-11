from pathlib import Path
import hashlib,json,subprocess,zipfile,sys,os
root=Path(__file__).resolve().parents[1];source=root/'lat-ai';base=root/'outputs/assessment-v3-2026-11-11'
name=sys.argv[1] if len(sys.argv)>1 else 'backup-before-promotion'
assert name in {'backup-before-promotion','backup-final','backup-final-reviewed'}
out=base/name;out.mkdir(exist_ok=False)
git=['git','-c','safe.directory='+source.as_posix(),'-C',str(source)]
bundle=out/'repository.bundle'
subprocess.run(git+['bundle','create',str(bundle),'--all'],check=True,capture_output=True)
verify=subprocess.run(git+['bundle','verify',str(bundle)],check=True,capture_output=True)
(out/'bundle-verify.log').write_bytes(verify.stdout+verify.stderr)
(out/'dirty.patch').write_bytes(subprocess.check_output(git+['diff','--binary','HEAD']))
(out/'git-status.txt').write_bytes(subprocess.check_output(git+['status','--short']))
paths=subprocess.check_output(git+['ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
manifest=[];archive=out/'LAT-AI-worktree.zip'
with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
 for name in sorted(set(filter(None,paths))):
  f=source/name
  if not f.is_file():continue
  data=f.read_bytes();entry='project/'+name;z.writestr(entry,data);manifest.append({'entry':entry,'sha256':hashlib.sha256(data).hexdigest()})
 for name in ['AGENTS.md','START_HERE.md','outputs/STATUS.md','outputs/AI_ROADMAP.md','work/local-pc/profile.json']:
  data=(root/name).read_bytes();entry='workspace/'+name;z.writestr(entry,data);manifest.append({'entry':entry,'sha256':hashlib.sha256(data).hexdigest()})
 for name in ['repository.bundle','dirty.patch','git-status.txt','bundle-verify.log']:
  data=(out/name).read_bytes();z.writestr(name,data);manifest.append({'entry':name,'sha256':hashlib.sha256(data).hexdigest()})
 if out.name.startswith('backup-final'):
  snapshots=[(root/'tools','workspace/tools'),(base,'workspace/outputs/assessment-v3-2026-11-11')]
  snapshots += [(root/'work'/folder,'experiments/'+folder) for folder in ['assessment-v3a-2026-11-11','assessment-v3b-2026-11-11','assessment-v3c-2026-11-11','assessment-v3d-2026-11-11','ai-receipt-2026-11-11']]
  for folder,prefix in snapshots:
   for current,dirs,files in os.walk(folder):
    dirs[:]=[d for d in dirs if d not in {'node_modules','__pycache__','.git','.runtime','test-runtime'} and not d.startswith('backup-')]
    for filename in files:
     f=Path(current)/filename
     if f.suffix in {'.sqlite3','.db','.lock','.pyc'} or filename=='ipc-secret.txt':continue
     assert f.resolve().is_relative_to(folder.resolve())
     entry=prefix+'/'+f.relative_to(folder).as_posix();data=f.read_bytes();z.writestr(entry,data);manifest.append({'entry':entry,'sha256':hashlib.sha256(data).hexdigest()})
 z.writestr('MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2))
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 for row in manifest:assert hashlib.sha256(z.read(row['entry'])).hexdigest()==row['sha256']
result={'archive':str(archive),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'verified_entries':len(manifest),'project_files':sum(r['entry'].startswith('project/') for r in manifest),'git_bundle_verified':True,'note':'Bundle preserves committed history; ZIP preserves every tracked/untracked nonignored working file including dirty changes. Runtime secrets/DB/node_modules are excluded by git inventory. No commit or push.'}
(out/'VERIFICATION.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
(out/'RESTORE.txt').write_text('Restore into a NEW directory: clone repository.bundle there, then overlay project/ from LAT-AI-worktree.zip to recover the exact dirty worktree. Do not apply dirty.patch on top of the overlaid snapshot. workspace/ contains context, not model binaries or secrets. Verify MANIFEST SHA before use. Never overwrite the current working directory blindly.\n',encoding='utf-8')
print(json.dumps(result,ensure_ascii=False))
