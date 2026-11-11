from pathlib import Path
import json,hashlib,shutil,zipfile
work=Path(__file__).resolve().parent
root=work.parents[1]
evidence=root/'outputs/f01-2026-11-10'
userout=Path('C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-10/lad-ai-c-users-asus-rog-3/outputs')
assert json.loads((evidence/'verification.json').read_text())['passed']
assert (evidence/'FINAL_REVIEW.txt').is_file()
scripts=evidence/'scripts';scripts.mkdir(exist_ok=True)
for p in work.glob('*.py'):shutil.copy2(p,scripts/p.name)
for p in (work/'eval').glob('*.py'):
 target=scripts/'eval'/p.name;target.parent.mkdir(exist_ok=True);shutil.copy2(p,target)
frozen=json.loads((evidence/'freeze.json').read_text())
for item in frozen['sources']:
 src=root/'outputs/ai-module-v5-2026-11-09'/item['path']
 target=evidence/'frozen-inputs'/item['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(src,target)
 assert hashlib.sha256(target.read_bytes()).hexdigest()==item['sha256']
for name in ['REPORT.txt','E01_PAIRS.txt']:
 shutil.copy2(evidence/name,userout/('LAD-AI-F01-REPORT.txt' if name=='REPORT.txt' else 'LAD-AI-E01-PAIRS.txt'))
files=sorted(p for p in evidence.rglob('*') if p.is_file() and p.name not in ('MANIFEST.json','archive-verification.json'))
manifest=[{'path':p.relative_to(evidence).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
(evidence/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf8')
archive=userout/'LAD-AI-F01-E01-review-2026-11-10.zip'
assert not archive.exists()
with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED,compresslevel=7) as z:
 for p in files+[evidence/'MANIFEST.json']:z.write(p,'LAD-AI-F01/'+p.relative_to(evidence).as_posix())
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 assert len(z.namelist())==len(manifest)+1
 for m in manifest:assert hashlib.sha256(z.read('LAD-AI-F01/'+m['path'])).hexdigest()==m['sha256']
verification={'archive':archive.name,'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'entries':len(manifest)+1,'all_entry_hashes_and_crc_pass':True}
(evidence/'archive-verification.json').write_text(json.dumps(verification,indent=2),encoding='utf8')
(userout/'LAD-AI-F01-archive-verification.json').write_text(json.dumps(verification,indent=2),encoding='utf8')
print(json.dumps(verification))
