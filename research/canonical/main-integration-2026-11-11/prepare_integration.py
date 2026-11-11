from pathlib import Path
import hashlib, json, zipfile, subprocess, sqlite3, os

ROOT = Path(__file__).resolve().parents[2]
OUT = Path(__file__).resolve().parent
MAIN = ROOT / 'work/lat-ai'
INCOMING = Path('C:/Users/ASUS ROG STRIX/Documents/Codex/lat-return-1111/workspace/lat-ai')
PILOT = Path('C:/Users/ASUS ROG STRIX/.codex/worktrees/lad-document-pilot/git-restore-check')
ZIP = Path('C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-10/lad-ai-c-users-asus-rog-3/outputs/LAD-AI-document-pilot-2026-11-11.zip')
STAGE = ROOT / 'work/main-integration-stage'

def sha(data): return hashlib.sha256(data).hexdigest()
def save(name, value): (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')

old = {x['path']: x['sha256'] for x in json.loads((ROOT/'work/handoff-2026-11-11/SOURCE_SNAPSHOT.json').read_text(encoding='utf-8'))['files']}
drift = [p for p,h in old.items() if not (MAIN/p).exists() or sha((MAIN/p).read_bytes()) != h]
save('preflight.json', {'old191_count':len(old), 'main_drift_from_191':drift})
assert not drift, ('Local drift requires merge', drift)
assert sha(ZIP.read_bytes()) == '996c6e3c1052949b756b755930eb6821c8ba6aa8ef62b0a75550ef71d6d6f76f'
with zipfile.ZipFile(ZIP) as z:
    manifest = json.loads(z.read('LAD-AI-Document-Pilot/MANIFEST.json'))
    files = manifest['files']
    assert len(files) == 244 and z.testzip() is None
    changed, added = [], []
    for entry in files:
        p = entry['path']
        assert not Path(p).is_absolute() and '..' not in Path(p).parts
        data = z.read('LAD-AI-Document-Pilot/' + p)
        assert sha(data) == entry['sha256']
        assert sha((PILOT/p).read_bytes()) == entry['sha256'], ('Pilot changed after packaging',p)
        target = STAGE/p
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists(): assert target.read_bytes() == data, ('Stage differs',p)
        else: target.write_bytes(data)
        if p in old:
            if old[p] != entry['sha256']: changed.append(p)
        else:
            assert not (MAIN/p).exists() or (MAIN/p).read_bytes()==data, ('Untracked collision',p)
            added.append(p)
    save('promotion-manifest.json', {'main':str(MAIN),'stage':str(STAGE),'files':files,'changed':changed,'added':added,'removed':sorted(set(old)-{x['path'] for x in files})})

# Backup all tracked/untracked source according to git, keeping ignored runtime separate.
names = subprocess.check_output(['git','-C',str(MAIN),'ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
names = sorted(set(n for n in names if n and (MAIN/n).is_file()))
backup = OUT/'main-source-before.zip'
if not backup.exists():
    with zipfile.ZipFile(backup,'x',compression=zipfile.ZIP_DEFLATED) as z:
        for name in names: z.write(MAIN/name,name)
with zipfile.ZipFile(backup) as z:
    assert z.testzip() is None
    for name in names: assert z.read(name)==(MAIN/name).read_bytes(),name
for name,args in [('git-status-before.txt',['status','--short']),('git-diff-before.patch',['diff','--binary']),('git-staged-before.patch',['diff','--cached','--binary'])]:
    (OUT/name).write_bytes(subprocess.check_output(['git','-C',str(MAIN),*args]))
save('backup-verification.json', {'source_files':len(names),'zip_sha256':sha(backup.read_bytes()),'all_entries_equal':True})
print(json.dumps({'source_backup_files':len(names),'candidate':len(files),'changed':len(changed),'added':len(added),'main191_unchanged':True,'pilot244_matches_archive':True}))
