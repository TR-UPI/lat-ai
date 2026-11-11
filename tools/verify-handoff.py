import hashlib, json, subprocess, sys
from pathlib import Path
root = Path(sys.argv[1]).resolve()
longroot = Path('\\\\?\\' + str(root)) if sys.platform == 'win32' else root
manifest = json.loads((root/'docs/agent-handoff/PROVENANCE.json').read_text(encoding='utf-8'))
raw = subprocess.check_output(['git','ls-files','--stage','-z'], cwd=root)
entries = {}
for line in raw.split(b'\0'):
    if not line: continue
    meta,path = line.split(b'\t',1)
    mode,oid,stage = meta.decode().split()
    assert stage == '0', path
    assert mode in ('100644','100755'), (path,mode)
    entries[path.decode('utf-8')] = oid
for row in manifest['files']:
    path = row['path']; data = (longroot/path).read_bytes()
    assert len(data) == row['bytes'] and hashlib.sha256(data).hexdigest() == row['sha256'], path
    blob = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
    assert entries.get(path) == blob, ('missing or changed staged archive',path)
for path in entries:
    parts = Path(path).parts
    assert not any(x in parts for x in ('.runtime','.venv','node_modules','private-media')), path
    assert Path(path).suffix.lower() not in ('.db','.sqlite3','.gguf','.safetensors','.zip','.7z','.exe'), path
    assert Path(path).name not in ('django-secret.txt','ipc-secret.txt','.env'), path
print(json.dumps({'tracked_files':len(entries),'provenance_files':len(manifest['files']),'staged_sha256_and_blob_match':True,'excluded_runtime_data_weights':True},indent=2))
