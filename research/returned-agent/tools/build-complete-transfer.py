"""Build complete local developer handoff; preserve source/evidence, never run runtime."""
from pathlib import Path
from datetime import datetime,timezone,timedelta
import os,json,hashlib,subprocess,zipfile,sqlite3,shutil,time
ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/transfer-full-2026-11-11'
PREV=ROOT/'outputs/sdk-isolation-live-2026-11-11'
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
def sha(p):
    h=hashlib.sha256()
    with Path(p).open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def save(p,v):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:json.dump(v,f,ensure_ascii=False,indent=2)
def put(p,data):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('xb') as f:f.write(data if isinstance(data,bytes) else data.encode())
def say(v):print(json.dumps(v,ensure_ascii=False),flush=True)
start=datetime.now(timezone.utc);since=start-timedelta(hours=12)
git=['git','-c','safe.directory='+str(ROOT/'lat-ai'),'-C',str(ROOT/'lat-ai')]
baseline=read(PREV/'backup/source-and-evidence-manifest.json');nav={'AGENTS.md','START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md'}
for n,h in baseline.items():
    if n not in nav:assert sha(ROOT/n)==h,n
names=subprocess.check_output(git+['ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
source={n:sha(ROOT/'lat-ai'/n) for n in sorted(set(filter(None,names))) if (ROOT/'lat-ai'/n).is_file()}
assert source==read(PREV/'preservation-audit.json')['after_sha256']
save(OUT/'SOURCE_209.json',source)
for n in nav:put(OUT/'navigation-before'/n,(ROOT/n).read_bytes())
banner='''## Полная передача агенту · 11.11.2026

Собраны исходники, все отчёты/тесты/логи/промежуточные варианты и контекст.
Точка входа: outputs/transfer-full-2026-11-11/00_START_HERE.txt.
Доступны инженерный AGENT-HANDOFF ZIP и полный FULL-WORKSPACE ZIP с зависимостями,
исходным архивом и активным GGUF; точный состав/исключения/SHA в INVENTORY и manifests.
SDK isolated load остаётся NOT_RUN/BLOCKED; новых model calls/commit/push нет.
Сборка архива не является новым тестом качества и не закрывает ручной пилот.

'''
for n in ['START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md']:
    p=ROOT/n;s=p.read_text(encoding='utf-8-sig');p.write_text(banner+s,encoding='utf-8')
bundle=OUT/'git/LAT-AI-ALL-REFS.bundle';bundle.parent.mkdir(exist_ok=True)
subprocess.run(git+['bundle','create',str(bundle),'--all'],check=True,capture_output=True)
r=subprocess.run(git+['bundle','verify',str(bundle)],check=True,capture_output=True);put(OUT/'git/BUNDLE_VERIFY.log',r.stdout+r.stderr)
put(OUT/'git/DIRTY.patch',subprocess.check_output(git+['diff','--binary','HEAD']))
put(OUT/'git/STATUS.txt',subprocess.check_output(git+['status','--short']))
put(OUT/'git/HEAD.txt',subprocess.check_output(git+['rev-parse','HEAD']))
put(OUT/'git/BRANCH.txt',subprocess.check_output(git+['branch','--show-current']))

# Consistent, read-only SQLite snapshots. Originals and running processes remain untouched.
snapshots={};sqlite_results=[]
for n in ['lat-ai/.runtime/i02/django.sqlite3','lat-ai/.runtime/i02/replay.sqlite3']:
    src=ROOT/n
    if not src.exists():continue
    dest=OUT/'database-snapshots'/Path(n).name;dest.parent.mkdir(exist_ok=True)
    source_db=sqlite3.connect(src.resolve().as_uri()+'?mode=ro',uri=True,timeout=10)
    target_db=sqlite3.connect(dest)
    try:source_db.backup(target_db);ok=target_db.execute('PRAGMA integrity_check').fetchall();assert ok==[('ok',)]
    finally:target_db.close();source_db.close()
    snapshots[n]=dest;sqlite_results.append({'source':n,'snapshot':dest.relative_to(OUT).as_posix(),'integrity_check':'ok','snapshot_sha256':sha(dest)})

full={};agent={};inventory=[];exclusions=[];reparse=[]
skip_exact={'lat-ai/.runtime/i02/ipc-secret.txt','lat-ai/.runtime/i02/django-secret.txt'}
for base,dirs,files in os.walk(ROOT,followlinks=False):
    base=Path(base)
    kept=[]
    for d in sorted(dirs):
        q=base/d;rel=q.relative_to(ROOT).as_posix()
        if q==OUT:continue
        if rel=='lat-ai/.git':exclusions.append({'path':rel,'reason':'Git history preserved in fresh verified bundle; original metadata stays local'});continue
        if q.is_symlink() or (q.stat(follow_symlinks=False).st_file_attributes & 0x400):reparse.append(rel);continue
        kept.append(d)
    dirs[:]=kept
    for name in sorted(files):
        q=base/name;n=q.relative_to(ROOT).as_posix()
        if n in skip_exact:exclusions.append({'path':n,'reason':'Local runtime authentication secret; generate anew on target'});continue
        if n in [x+s for x in snapshots for s in ['-wal','-shm','-journal']]:exclusions.append({'path':n,'reason':'SQLite sidecar superseded by consistent backup snapshot'});continue
        if q.is_symlink():reparse.append(n);continue
        use=snapshots.get(n,q);st=use.stat();row={'path':n,'bytes':st.st_size,'mtime_utc':datetime.fromtimestamp(st.st_mtime,timezone.utc).isoformat(),'mtime_in_last_12h':st.st_mtime>=since.timestamp(),'sqlite_snapshot':n in snapshots}
        inventory.append(row);full['workspace/'+n]=use
        # Agent package keeps ALL outputs/tools plus current sources and every AI candidate,
        # omits only bulky disposable runtime environments/original archival distribution.
        inc=n.startswith(('outputs/','tools/','work/assessment-','work/ai-receipt-','work/u02-runtime-sdk/')) or n in ['AGENTS.md','START_HERE.md','START-LAT-AI-THIS-PC.cmd','LAD-AI-handoff-FIRST_MESSAGE.txt','work/local-pc/profile.json','work/local-pc/README.md'] or (n.startswith('lat-ai/') and n[7:] in source)
        if inc:agent['workspace/'+n]=use
active=Path('E:/Horror game/LocalAI/models/unsloth/Qwen3.5-9B-GGUF/Qwen3.5-9B-Q4_K_M.gguf')
assert active.is_file();modelhash=sha(active);assert modelhash=='03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8'
full['external-assets/Qwen3.5-9B-Q4_K_M.gguf']=active
save(OUT/'MODEL.json',{'source_path':str(active),'full_archive_path':'external-assets/Qwen3.5-9B-Q4_K_M.gguf','bytes':active.stat().st_size,'sha256':modelhash,'included_in_agent_archive':False,'other_external_installations':'LM Studio installation, unrelated 4B/abliterated models and user home are not workspace content and not copied.'})
save(OUT/'INVENTORY.json',{'snapshot_started_utc':start.isoformat(),'snapshot_started_qyzylorda':start.astimezone(timezone(timedelta(hours=5))).isoformat(),'last_12h_start_utc':since.isoformat(),'scope':'All available workspace artifacts, not restricted to file dates; active external model included in FULL. No external upload.','workspace_files':inventory,'exclusions':exclusions,'reparse_entries_not_followed':reparse,'sqlite_snapshots':sqlite_results,'private_material':'Developer-only package; raw historical archives retained byte-for-byte, not newly redacted. Never distribute to blind reviewers.','snapshot_semantics':'Per-file capture, not global atomic filesystem snapshot; frozen sources/evidence verified before and after.'})
reports=[];tests=[];protocols=[]
for row in inventory:
    n=row['path'];p=Path(n)
    if n.startswith('outputs/') and p.name.lower() in ['report.txt','report.md','worklog.txt','claude_review.txt','one_page.txt','errata_datasets.txt']:reports.append(n)
    if n.startswith(('tools/','lat-ai/')) and ('test' in p.name.lower()):tests.append(n)
    if n.startswith('outputs/') and ('protocol' in p.name.lower() or p.name.lower() in ['freeze.json','summary.json','package-audit.json','postpackage-verification.json']):protocols.append(n)
save(OUT/'EVIDENCE_INDEX.json',{'reports_and_worklogs':reports,'test_sources':tests,'protocols_results_and_audits':protocols,'all_logs':'All outputs/ directories included without selecting only successful runs.'})
put(OUT/'03_RESTORE.txt','Extract into NEW empty directory. Read handoff/00_START_HERE.txt. Current source is workspace/lat-ai. Optionally clone handoff/git/LAT-AI-ALL-REFS.bundle into a separate directory and overlay workspace/lat-ai; do NOT apply DIRTY.patch over the overlay. Compare SOURCE_209.json. All old absolute paths are historical; do not mass-rewrite frozen files. Node/Python environments in FULL are copies, not guaranteed relocatable installs. Reinstall from package/lock/requirements if needed. SQLite snapshots are test-state backups, not production migration. Generate new local IPC/Django secrets. All copied locks/PID/store records are inert evidence; never resume them as a running service. Qwen GGUF in external-assets has SHA in MODEL.json. No commit/push/model calls performed during packaging.\n')
put(OUT/'WORKLOG.txt','Transfer built from all workspace material, including previous archives, candidates, failures and dependencies. Read-thread pagination exported19turns/246public messages plus operation metadata; full tool outputs remain in saved logs. Two runtime secrets excluded, SQLite backed up read-only and integrity checked. No model/process/service restart, no project edits, no commit/push. Navigation links updated. Fresh Gitbundle verified. Each ZIP entry receives SHA while written; verification rereads every entry/CRC. PACKAGE_VERIFICATION.json records completion, archive hashes are external.\n')
# Freeze all handoff docs before packaging; omit mutable build/progress/verification products.
for p in OUT.rglob('*'):
    if p.is_file() and p.suffix!='.zip' and p.name not in ['build.log','PACKAGE_VERIFICATION.json','CHECKSUMS.sha256']:
        key='handoff/'+p.relative_to(OUT).as_posix();full[key]=p;agent[key]=p
save(OUT/'PACKAGE_PLAN.json',{'agent_files':len(agent),'full_files':len(full),'full_input_bytes':sum(p.stat().st_size for p in full.values()),'free_disk_bytes':shutil.disk_usage(ROOT).free})
for target in [agent,full]:target['handoff/PACKAGE_PLAN.json']=OUT/'PACKAGE_PLAN.json'
say(read(OUT/'PACKAGE_PLAN.json'))

def make_archive(name,files):
    path=OUT/name;manifest={};changed=[];beg=time.monotonic();last=beg
    with zipfile.ZipFile(path,'x',compression=zipfile.ZIP_DEFLATED,compresslevel=1,allowZip64=True) as z:
        for index,(n,p) in enumerate(sorted(files.items()),1):
            before=p.stat();info=zipfile.ZipInfo(n);info.compress_type=zipfile.ZIP_STORED if p.suffix.lower() in {'.zip','.gguf','.safetensors','.dll','.exe','.whl','.bz2','.gz','.xz','.7z'} else zipfile.ZIP_DEFLATED
            info._compresslevel=1;h=hashlib.sha256();size=0
            with p.open('rb') as src,z.open(info,'w',force_zip64=True) as dst:
                for b in iter(lambda:src.read(4*1024*1024),b''):dst.write(b);h.update(b);size+=len(b)
            after=p.stat();manifest[n]={'sha256':h.hexdigest(),'bytes':size}
            if before.st_size!=after.st_size or before.st_mtime_ns!=after.st_mtime_ns:changed.append(n)
            if time.monotonic()-last>20:say({'archive':name,'written':index,'total':len(files),'elapsed_s':round(time.monotonic()-beg)});last=time.monotonic()
        z.writestr('ARCHIVE_MANIFEST.json',json.dumps(manifest,ensure_ascii=False,indent=2).encode())
    verified=0
    with zipfile.ZipFile(path) as z:
        assert set(z.namelist())==set(manifest)|{'ARCHIVE_MANIFEST.json'}
        for n,expected in manifest.items():
            h=hashlib.sha256();size=0
            with z.open(n) as f:
                for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b);size+=len(b)
            assert h.hexdigest()==expected['sha256'] and size==expected['bytes'],n;verified+=1
            if time.monotonic()-last>20:say({'archive':name,'verified':verified,'total':len(files)});last=time.monotonic()
    result={'name':name,'sha256':sha(path),'bytes':path.stat().st_size,'verified_data_entries':verified,'manifest_entries':1,'changed_during_capture':changed,'crc_and_sha_verified':True}
    say(result);return result
results=[make_archive('LAT-AI-AGENT-HANDOFF-2026-11-11.zip',agent),make_archive('LAT-AI-FULL-WORKSPACE-2026-11-11.zip',full)]
for n,h in baseline.items():
    if n not in nav:assert sha(ROOT/n)==h,n
assert {n:sha(ROOT/'lat-ai'/n) for n in source}==source
save(OUT/'PACKAGE_VERIFICATION.json',{'finished_utc':datetime.now(timezone.utc).isoformat(),'archives':results,'source209_unchanged':True,'previous_immutable_files_unchanged':len(baseline)-len(nav),'git_bundle_verified':True,'model_sha_verified':modelhash,'model_calls':0,'commit_push':False,'sqlite_snapshots_integrity':sqlite_results})
put(OUT/'CHECKSUMS.sha256',''.join(x['sha256']+'  '+x['name']+'\n' for x in results))
say({'complete':True,'archives':results})
