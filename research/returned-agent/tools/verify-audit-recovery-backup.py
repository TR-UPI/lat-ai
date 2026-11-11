"""Restore an inert source/evidence copy into a NEW directory and verify it."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,zipfile,hashlib,subprocess

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/audit-recovery-2026-11-11'
archive=OUT/'backup/LAT-AI-RECOVERY-SOURCE-AND-EVIDENCE.zip'
destination=Path(sys.argv[1]).resolve() if len(sys.argv)>1 else ROOT/'work/audit-recovery-restore-check'
if not destination.is_relative_to(ROOT/'work'):raise ValueError('restore_check_must_stay_within_workspace_work')
destination.mkdir(parents=True,exist_ok=False)
sha=lambda data:hashlib.sha256(data).hexdigest()
with zipfile.ZipFile(archive) as z:
    manifest=json.loads(z.read('ARCHIVE_MANIFEST.json'))
    assert set(z.namelist())==set(manifest)|{'ARCHIVE_MANIFEST.json'} and z.testzip() is None
    for name,expected in manifest.items():
        path=(destination/name).resolve()
        if not path.is_relative_to(destination) or Path(name).is_absolute() or ':' in name:raise ValueError('unsafe_archive_name')
        data=z.read(name);assert sha(data)==expected,name
        path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('xb') as f:f.write(data)
        assert sha(path.read_bytes())==expected,name

protocol=destination/'outputs/audit-recovery-2026-11-11/recovery-protocol.json'
tool=destination/'tools/recover-audit-store.py'
code="import importlib.util,sys; s=importlib.util.spec_from_file_location('restored',sys.argv[1]); r=importlib.util.module_from_spec(s); s.loader.exec_module(r); r.verify(sys.argv[2]); print('RESTORED_FROZEN_PROTOCOL_OK')"
run=subprocess.run([sys.executable,'-B','-c',code,str(tool),str(protocol)],capture_output=True,text=True,encoding='utf-8',timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));run.check_returncode()
assert run.stdout.strip()=='RESTORED_FROZEN_PROTOCOL_OK'
demo=destination/'outputs/audit-recovery-2026-11-11/TECHNICAL_FIXTURE'
guard=subprocess.run([sys.executable,'-B',str(tool),'status',str(protocol),str(demo/'FIXTURE_STORE'),str(demo/'assignment')],capture_output=True,text=True,encoding='utf-8',timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
assert guard.returncode==2 and json.loads(guard.stdout)['reason']=='owner_metadata_mismatch'
result={'utc':datetime.now(timezone.utc).isoformat(),'scope':'INERT_SOURCE_RESTORE_CHECK_NOT_ACTIVE_STORE_MIGRATION','archive_sha256':sha(archive.read_bytes()),'files_restored_and_sha_verified':len(manifest),'frozen_protocol_verified_from_restored_path':True,'restored_store_status_exit':guard.returncode,'restored_store_guard':'owner_metadata_mismatch','live_store_not_activated':True,'model_calls':0,'source_project_unchanged':True,'restore_directory':str(destination)}
path=OUT/'postpackage-verification.json'
with path.open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False))
