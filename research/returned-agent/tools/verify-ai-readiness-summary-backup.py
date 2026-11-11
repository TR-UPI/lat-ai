"""Restore into a NEW inert directory; run only offline integrity readers."""
from pathlib import Path
from datetime import datetime,timezone
import sys,json,zipfile,hashlib,subprocess
ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/ai-readiness-and-audit-summary-2026-11-11'
archive=OUT/'backup/LAT-AI-READINESS-SOURCE-AND-EVIDENCE.zip'
destination=ROOT/'work/ai-readiness-summary-restore-check'
destination.mkdir(parents=True,exist_ok=False)
sha=lambda data:hashlib.sha256(data).hexdigest()
with zipfile.ZipFile(archive) as z:
    manifest=json.loads(z.read('ARCHIVE_MANIFEST.json'))
    assert set(z.namelist())==set(manifest)|{'ARCHIVE_MANIFEST.json'} and z.testzip() is None
    for name,h in manifest.items():
        p=(destination/name).resolve()
        if not p.is_relative_to(destination.resolve()) or Path(name).is_absolute() or ':' in name:raise ValueError('unsafe_archive_name')
        data=z.read(name);assert sha(data)==h,name
        p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('xb') as f:f.write(data)
        assert sha(p.read_bytes())==h,name
stage=destination/'outputs/ai-readiness-and-audit-summary-2026-11-11'
code="import importlib.util,sys; s=importlib.util.spec_from_file_location('restored',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); m.verify(sys.argv[2]); print('RESTORED_SUMMARY_PROTOCOL_OK')"
flags=getattr(subprocess,'CREATE_NO_WINDOW',0)
run=subprocess.run([sys.executable,'-B','-c',code,str(destination/'tools/summarize-audit-returns.py'),str(stage/'summary-protocol.json')],capture_output=True,text=True,encoding='utf-8',timeout=30,creationflags=flags)
run.check_returncode();assert run.stdout.strip()=='RESTORED_SUMMARY_PROTOCOL_OK'
check=subprocess.run([sys.executable,'-B',str(destination/'tools/check-ai-readiness.py'),'check',str(stage/'readiness-protocol.json'),str(destination/'RESTORED_READINESS.json')],capture_output=True,text=True,encoding='utf-8',timeout=60,creationflags=flags)
check.check_returncode();assert json.loads(check.stdout)['technical_integrity_passed'] is True
result={'utc':datetime.now(timezone.utc).isoformat(),'scope':'INERT_SOURCE_RESTORE_CHECK_NOT_LIVE_STORE_MIGRATION','archive_sha256':sha(archive.read_bytes()),'files_restored_and_sha_verified':len(manifest),'summary_protocol_verified_from_restored_path':True,'full_offline_preflight_passed_from_restored_path':True,'prior_archive_included_for_preflight':True,'live_store_not_activated':True,'model_calls':0,'network_calls':0,'restore_directory':str(destination)}
with (OUT/'postpackage-verification.json').open('x',encoding='utf-8') as f:json.dump(result,f,ensure_ascii=False,indent=2)
print(json.dumps(result,ensure_ascii=False))
