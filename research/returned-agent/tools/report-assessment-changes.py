"""Audit only this work against the saved dirty-tree snapshot, without secrets."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess

root = Path(__file__).resolve().parents[1]
source = root / 'lat-ai'
report = root / 'outputs/assessment-fix-2026-11-11'
before = report / 'source-before'
paths = subprocess.check_output(['git', '-c', f'safe.directory={source.as_posix()}', '-C', str(source), 'ls-files', '--cached', '--others', '--exclude-standard'], encoding='utf-8').splitlines()
changes, patch = [], []
for name in sorted(set(paths)):
    old, new = before / name, source / name
    old_bytes = old.read_bytes() if old.is_file() else None
    new_bytes = new.read_bytes() if new.is_file() else None
    if old_bytes == new_bytes:
        continue
    changes.append({'path': name, 'before_sha256': hashlib.sha256(old_bytes).hexdigest() if old_bytes is not None else None, 'after_sha256': hashlib.sha256(new_bytes).hexdigest() if new_bytes is not None else None})
    try:
        patch.extend(difflib.unified_diff((old_bytes or b'').decode('utf-8').splitlines(keepends=True), (new_bytes or b'').decode('utf-8').splitlines(keepends=True), fromfile='before/'+name, tofile='after/'+name))
    except UnicodeDecodeError:
        patch.append(f'Binary change: {name}\n')
(report / 'source-changes.json').write_text(json.dumps(changes, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
(report / 'this-work.patch').write_text(''.join(patch), encoding='utf-8', newline='\n')
print(json.dumps({'changed_or_added_files': len(changes), 'paths': [x['path'] for x in changes]}, ensure_ascii=False))
