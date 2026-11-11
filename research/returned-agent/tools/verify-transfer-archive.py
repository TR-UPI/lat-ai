"""Read-only verification of transfer ZIP; never extracts or executes contents."""
import sys,json,hashlib,zipfile
from pathlib import Path
p=Path(sys.argv[1]);h=hashlib.sha256()
with zipfile.ZipFile(p) as z:
    mf=json.loads(z.read('ARCHIVE_MANIFEST.json'));assert len(z.namelist())==len(set(z.namelist()))
    assert set(z.namelist())==set(mf)|{'ARCHIVE_MANIFEST.json'}
    for index,(name,entry) in enumerate(mf.items(),1):
        assert not name.startswith(('/','\\')) and '..' not in Path(name).parts and ':' not in name,name
        d=hashlib.sha256();size=0
        with z.open(name) as f:
            for b in iter(lambda:f.read(4*1024*1024),b''):d.update(b);size+=len(b)
        assert d.hexdigest()==entry['sha256'] and size==entry['bytes'],name
        if index%10000==0:print('verified',index,flush=True)
with p.open('rb') as f:
    for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
print(json.dumps({'file':str(p),'data_entries_verified':len(mf),'sha256':h.hexdigest(),'crc_and_sha_ok':True}))
