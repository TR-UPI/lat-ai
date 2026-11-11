"""Record this workspace migration; preserve the extracted handoff as evidence."""
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
ARCHIVE = ROOT / 'LAD-AI-handoff-2026-11-11'
REPORT = ROOT / 'outputs/handoff-intake-2026-11-11'
SOURCE = ROOT / 'lat-ai'

def sha(path):
    return hashlib.file_digest(path.open('rb'), 'sha256').hexdigest()

def git(*args):
    return subprocess.check_output(['git', '-C', str(SOURCE), *args], encoding='utf-8').strip()

snapshot = ARCHIVE / 'project/work/lat-ai'
rows = []
for path in sorted(snapshot.rglob('*')):
    if path.is_file():
        relative = path.relative_to(snapshot)
        destination = SOURCE / relative
        digest = sha(path)
        rows.append({'path': relative.as_posix(), 'sha256': digest,
                     'matches': destination.is_file() and sha(destination) == digest})
assert all(row['matches'] for row in rows), 'Source snapshot mismatch'
assert git('rev-parse', 'HEAD') == 'b4fd6370d31dab24c924d7d78cc4dfffa478e30c'
previous_status = (ARCHIVE / 'git-history/git-status.txt').read_text(encoding='utf-8').strip()
current_status = git('status', '--short')
assert previous_status == current_status, 'Dirty tree differs from handoff'
(REPORT / 'source-verification.json').write_text(json.dumps({
    'verified_at_utc': datetime.now().astimezone().isoformat(),
    'source': str(SOURCE), 'head': git('rev-parse', 'HEAD'),
    'branch': git('branch', '--show-current'), 'files': len(rows),
    'all_match': True, 'dirty_status_matches_handoff': True, 'entries': rows,
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
(REPORT / 'git-status.txt').write_text(current_status + '\n', encoding='utf-8')

manifest = json.loads((ARCHIVE / 'MANIFEST.json').read_text(encoding='utf-8'))
groups = Counter('/'.join(row['path'].split('/')[:2]) for row in manifest['files'])
(REPORT / 'archive-index.json').write_text(json.dumps({
    'files': len(manifest['files']), 'groups': dict(sorted(groups.items())),
    'full_manifest': str(ARCHIVE / 'MANIFEST.json'),
}, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

old_root = 'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-08/shag-model-selection'
old_legacy = 'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-05/new-chat/outputs/shag-platform'
old_chat = 'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-10/lad-ai-c-users-asus-rog-3/outputs'
replacements = [
    (old_root + '/work/lat-ai', SOURCE.as_posix()),
    (old_root + '/outputs/AI_ROADMAP.md', (ROOT / 'outputs/AI_ROADMAP.md').as_posix()),
    (old_legacy + '/STATUS.md', (ROOT / 'outputs/STATUS.md').as_posix()),
    (old_chat, (ARCHIVE / 'deliverables').as_posix()),
    (old_root, (ARCHIVE / 'project').as_posix()),
    (old_legacy, (ARCHIVE / 'legacy/shag-platform').as_posix()),
]
common = '''> Перенос на этот ПК — 11.11.2026. Это активный документ LAT AI.
> Исходники: `E:/Startup Tau/lat-ai`; roadmap: `E:/Startup Tau/outputs/AI_ROADMAP.md`;
> единственный журнал: `E:/Startup Tau/outputs/STATUS.md`.
> Оригиналы в `LAD-AI-handoff-2026-11-11` сохранены как архивные снимки.
> Абсолютные пути старого ПК в этой рабочей копии перенаправлены; исторические
> относительные `work/` и `outputs/` ниже относятся к `LAD-AI-handoff-2026-11-11/project/`.
> Дедлайн показа 13 ноября и заморозка 11 ноября 18:00 — сохранённый план предыдущего
> этапа, не новое поручение. Текущий запрос — подготовка к дальнейшей работе.

'''
intake = '''## Приём передачи на новом компьютере · 11.11.2026

- Подготовка завершена. ZIP: 3 784 файла сверены по размерам, SHA-256 и CRC.
- Восстановлены Git bundle, HEAD `b4fd6370d31dab24c924d7d78cc4dfffa478e30c`, ветка
  `codex/i02-api-contract`; все 191 файла исходного снимка побайтово совпали,
  исходный dirty status сохранён. Коммит и отправка изменений не выполнялись.
- Из полного комплекта извлечены отдельные Python 3.12.14 и Node 24.11.1.
  В runtime адаптирован только путь backend в `python312._pth`; зависимости npm
  восстановлены по lockfile с отключёнными install scripts.
- Здесь заново прошли 52/52 Node integration, 19/19 Django, 335/335 baseline core,
  3 схемы, 2 request/6 response fixtures и 20 upstream hashes с local overrides.
  Логи: [проверки](<E:/Startup Tau/outputs/handoff-intake-2026-11-11/checks/results.json>).
- Живой Qwen, HTTP end-to-end, браузер и установка UPDATE на этом ПК не проверялись.
  LM Studio CLI обнаружен; импорт/доступность модели не подтверждены.
- Исходники приложения не изменены. Ошибка if/else и Django crash recovery открыты;
  T01/S02/D01/D02 не закрыты. Ничего не публиковалось и никому не отправлялось.
- Точка входа и карта продолжения: [START_HERE](<E:/Startup Tau/START_HERE.md>).

'''
for source_path, filename in [
    (ARCHIVE / 'project/outputs/AI_ROADMAP.md', 'AI_ROADMAP.md'),
    (ARCHIVE / 'legacy/shag-platform/STATUS.md', 'STATUS.md'),
]:
    target = ROOT / 'outputs' / filename
    if target.exists():
        raise SystemExit('Refusing to replace active document: ' + str(target))
    content = source_path.read_text(encoding='utf-8')
    for before, after in replacements:
        content = content.replace(before, after)
    target.write_text(common + intake + content, encoding='utf-8')
print(json.dumps({'source_files_verified': len(rows), 'dirty_tree_preserved': True,
                  'active_documents_created': 2}, ensure_ascii=False))
