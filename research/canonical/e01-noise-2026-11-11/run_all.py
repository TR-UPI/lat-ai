"""Offline verification/reproduction: Python3.10+, Node22+; no model calls."""
from pathlib import Path
import argparse,hashlib,json,subprocess
p=argparse.ArgumentParser(description=__doc__);p.add_argument('--verify-only',action='store_true');a=p.parse_args();root=Path(__file__).resolve().parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
manifest=json.loads((root/'MANIFEST.json').read_text(encoding='utf8'))
def verify():
 for m in manifest:
  f=(root/m['path']).resolve()
  if not f.is_relative_to(root) or f.stat().st_size!=m['bytes'] or sha(f)!=m['sha256']:raise ValueError('Artifact mismatch: '+m['path'])
 freeze=json.loads((root/'freeze.json').read_text())
 for name,key in [('inputs.json','inputs_sha256'),('PLAN.txt','plan_sha256')]:
  if sha(root/name)!=freeze[key]:raise ValueError('Frozen input mismatch')
verify()
if not a.verify_only:
 subprocess.run(['node','--test','presentation.test.mjs','render.test.mjs'],cwd=root,check=True)
 subprocess.run(['node','build.mjs'],cwd=root,check=True,capture_output=True)
 verify() # The comparison and HTML must reproduce byte-for-byte.
print(json.dumps({'passed':True,'manifest_files':len(manifest),'frozen_cases':81,'tests_run':not a.verify_only,'browser_checked':False,'model_calls':0}))
