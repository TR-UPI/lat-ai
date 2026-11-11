from pathlib import Path
import hashlib, json, sqlite3, shutil, subprocess, sys, time

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[1]
STAGE = ROOT/'work/main-integration-stage'
EXTRA = Path('C:/Users/ASUS ROG STRIX/.codex/worktrees/lad-document-pilot/git-restore-check/.runtime/python/Lib/site-packages')

def digest_rows(conn, table, columns):
    q = lambda name: '"' + name.replace('"','""') + '"'
    rows = conn.execute('SELECT '+','.join(map(q,columns))+' FROM '+q(table)).fetchall()
    return hashlib.sha256(repr(sorted(rows,key=repr)).encode()).hexdigest(), len(rows)

results=[]
for label,source in [('source-main',ROOT/'work/lat-ai/.runtime/i02'),('active-tf11kit',ROOT/'work/tf11kit/app/.runtime/i02')]:
    target = STAGE/'.runtime'/('migration-final-'+label)
    backup = ROOT/'work/main-integration-private-backup-final'/label
    target.mkdir(parents=True,exist_ok=True)
    backup.mkdir(parents=True,exist_ok=True)
    snapshots={}
    for name in ['django.sqlite3','replay.sqlite3']:
        dst=backup/name
        assert not dst.exists(), 'Refusing to replace baseline backup'
        with sqlite3.connect((source/name).as_uri()+'?mode=ro',uri=True) as src, sqlite3.connect(dst) as copy:
            deadline=time.monotonic()+20
            def progress(status, remaining, total):
                if time.monotonic()>deadline:
                    raise TimeoutError('SQLite backup deadline; no retry or source modification')
            src.backup(copy, pages=128, progress=progress, sleep=.1)
            assert copy.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
            assert not copy.execute('PRAGMA foreign_key_check').fetchall()
        snapshots[name]=hashlib.sha256(dst.read_bytes()).hexdigest()
        if name=='django.sqlite3': shutil.copy2(dst,target/name)
    for name in ['seed.json','mapping.json','ipc-secret.txt','django-secret.txt']:
        shutil.copy2(source/name,backup/name)
        shutil.copy2(source/name,target/name)
        snapshots[name]=hashlib.sha256((source/name).read_bytes()).hexdigest()
    with sqlite3.connect(target/'django.sqlite3') as conn:
        tables={r[0]:[c[1] for c in conn.execute('PRAGMA table_info("'+r[0]+'")')] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT IN ('django_migrations','django_content_type','auth_permission')").fetchall()}
        before={table:digest_rows(conn,table,cols) for table,cols in tables.items()}
    run=subprocess.run([sys.executable,'-B','tools/pilot.py','--runtime',str(target),'--python-extra-site',str(EXTRA),'prepare'],cwd=STAGE,capture_output=True)
    (OUT/(label+'-migration.log')).write_bytes(run.stdout+run.stderr)
    assert run.returncode==0,(label,run.returncode)
    with sqlite3.connect(target/'django.sqlite3') as conn:
        after={table:digest_rows(conn,table,cols) for table,cols in tables.items()}
        assert before==after,(label,'existing data changed')
        assert conn.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
        assert not conn.execute('PRAGMA foreign_key_check').fetchall()
        new_tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'documents_study%'")]
        assert len(new_tables)==3,new_tables
    for name in ['seed.json','mapping.json','ipc-secret.txt','django-secret.txt']:
        assert hashlib.sha256((target/name).read_bytes()).hexdigest()==snapshots[name]
    results.append({'runtime':label,'backup':str(backup),'hashes':snapshots,'existing_tables_unchanged':{k:v[1] for k,v in before.items()},'new_study_tables':new_tables,'integrity':'ok','foreign_keys':'ok','seed_mapping_secrets_unchanged':True})
    (OUT/'migration-verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    print('Verified '+label,flush=True)
(OUT/'migration-verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
print(json.dumps([{'runtime':r['runtime'],'preserved_tables':len(r['existing_tables_unchanged']),'new_study_tables':r['new_study_tables'],'ok':True} for r in results]))
