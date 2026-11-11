"""Take a private consistent SQLite backup and compare logical table contents."""
from pathlib import Path
import sqlite3,json,hashlib,sys
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[1]
RUNTIME=ROOT/'work/tf11kit/app/.runtime/i02'
PRIVATE=ROOT/'work/learning-feedback-private-backup'
db=sqlite3.connect((RUNTIME/'django.sqlite3').as_uri()+'?mode=ro',uri=True)
result={}
for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    quoted='"'+name.replace('"','""')+'"'
    rows=sorted(repr(row) for row in db.execute('SELECT * FROM '+quoted))
    result[name]={'rows':len(rows),'sha256':hashlib.sha256('\n'.join(rows).encode()).hexdigest()}
if sys.argv[1]=='before':
    PRIVATE.mkdir(exist_ok=False)
    with sqlite3.connect(PRIVATE/'django.sqlite3') as destination:db.backup(destination)
    (OUT/'database-before.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
else:
    before=json.loads((OUT/'database-before.json').read_text())
    assert before==result,'Database changed; inspect before/after before claiming preservation'
    (OUT/'database-preserved.json').write_text(json.dumps({'all_tables_unchanged':True,'tables':len(result),'row_counts':{k:v['rows'] for k,v in result.items()}},indent=2),encoding='utf-8')
print(json.dumps({'tables':len(result),'mode':sys.argv[1]}))
db.close()
