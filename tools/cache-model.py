"""Download and verify the official document-search model without changing Django.

Run with the prepared Python runtime, for example:
  .runtime/python-env/python.exe tools/cache-model.py
  .runtime/python-env/python.exe tools/cache-model.py --runtime-dir E:/LAT-runtime

The first run downloads about 493 MB using Windows curl. Existing verified files
are reused. --check-only checks the current cache and performs a real offline
embedding without downloading or writing files. No database is accessed.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

MODEL = 'intfloat/multilingual-e5-small'
COMMIT = '614241f622f53c4eeff9890bdc4f31cfecc418b3'
WEIGHTS_SHA256 = '1a55775f53449dac10a2bcbc312469fac40b96d53198c407081a831f81c98477'
# Sizes and hashes from the official Hugging Face model API at this commit.
# Git-managed files use SHA1("blob <size>\\0" + bytes); LFS files use SHA256(bytes).
FILES = (
    ('1_Pooling/config.json', 200, 'git', 'acbd4014202bf4dbc6c03229bcbeef7c4feafb58'),
    ('README.md', 497538, 'git', 'e56327af55e9742caf76bff9ba83b6904cd2003d'),
    ('config.json', 655, 'git', '60a2a84020f1d74cc53ea9e8c4e91cf4af6c2b68'),
    ('model.safetensors', 470641600, 'sha256', WEIGHTS_SHA256),
    ('modules.json', 387, 'git', 'ac2039abdf6ff023b27c919bb9675cfe378cb10f'),
    ('sentence_bert_config.json', 57, 'git', '4eca68d85ecd3034cf4174d8a4033a75344ea62d'),
    ('sentencepiece.bpe.model', 5069051, 'sha256', 'cfc8146abe2a0488e9e2a0c56de7952f7c11ab059eca145a0a727afce0db2865'),
    ('special_tokens_map.json', 167, 'git', 'e0b1d18ecd0ae4ff1d47bd297d910c0cf83e504b'),
    ('tokenizer.json', 17082730, 'sha256', '0b44a9d7b51c3c62626640cda0e2c2f70fdacdc25bbbd68038369d14ebdf4c39'),
    ('tokenizer_config.json', 443, 'git', '059214673d9d6d2ee319411e2ffec8c024b816d5'),
)


def verified(path, entry):
    _, size, kind, expected = entry
    if not path.is_file() or path.stat().st_size != size:
        return False
    digest = hashlib.sha256() if kind == 'sha256' else hashlib.sha1()
    if kind == 'git':
        digest.update(f'blob {size}\0'.encode('ascii'))
    with path.open('rb') as stream:
        while chunk := stream.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest() == expected


def check_embeddings(runtime, project):
    archive = runtime / 'archive-env' / '.venv' / 'Lib' / 'site-packages'
    if archive.is_dir():
        sys.path.insert(0, str(archive))
    sys.path.insert(0, str(project / 'backend'))
    os.environ.update({
        'HF_HOME': str(runtime / 'model-cache'),
        'HF_HUB_OFFLINE': '1',
        'TRANSFORMERS_OFFLINE': '1',
        'TOKENIZERS_PARALLELISM': 'false',
    })
    from documents.embedding_service import generate_embeddings, generate_query_embedding

    vectors = generate_embeddings([
        'Линейное уравнение: 2x + 6 = 14. Вычитаем 6 и делим на 2: x = 4.',
        'Фотосинтез происходит в хлоропластах растений под действием солнечного света.',
    ])
    query = generate_query_embedding('Как решить уравнение 2x + 6 = 14?')
    if len(vectors) != 2 or any(len(v) != 384 for v in vectors) or len(query) != 384:
        raise RuntimeError('The model did not return the required 384-dimensional embeddings.')
    for vector in [*vectors, query]:
        if not all(math.isfinite(value) for value in vector):
            raise RuntimeError('The model returned non-finite embeddings.')
        if abs(math.sqrt(sum(value * value for value in vector)) - 1.0) > 0.0001:
            raise RuntimeError('The model did not return normalized embeddings.')
    scores = [sum(a * b for a, b in zip(query, vector)) for vector in vectors]
    if scores[0] <= scores[1]:
        raise RuntimeError('The semantic retrieval check failed.')
    print(f'Offline embedding verified: 2 x 384 passages, 384 query; scores {scores}', flush=True)


def main():
    project = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime-dir', type=Path, default=project / '.runtime')
    parser.add_argument('--check-only', action='store_true')
    args = parser.parse_args()
    runtime = args.runtime_dir.resolve()
    cache = runtime / 'model-cache' / 'hub' / 'models--intfloat--multilingual-e5-small'
    snapshot = cache / 'snapshots' / COMMIT
    downloads = runtime / 'model-downloads'
    curl = shutil.which('curl.exe') or shutil.which('curl')

    def fetch(entry):
        name, size, _, _ = entry
        destination = snapshot / name
        if verified(destination, entry):
            print(f'Verified cached file: {name}', flush=True)
            return
        if args.check_only:
            raise RuntimeError(f'Missing or invalid cached file: {name}. Run without --check-only.')
        if not curl:
            raise RuntimeError('curl was not found. Use Windows 10/11 with its built-in curl.exe.')
        downloads.mkdir(parents=True, exist_ok=True)
        part = downloads / (name.replace('/', '__') + '.part')
        print(f'Download official {name}: {size:,} bytes', flush=True)
        result = subprocess.run([
            curl, '--location', '--fail', '--silent', '--show-error',
            '--connect-timeout', '15', '--max-time', '900',
            '--speed-limit', '2048', '--speed-time', '45',
            '--retry', '2', '--retry-delay', '2', '--continue-at', '-',
            '--output', str(part),
            f'https://huggingface.co/{MODEL}/resolve/{COMMIT}/{name}?download=true',
        ], check=False)
        if result.returncode:
            raise RuntimeError(f'curl failed for {name}, exit {result.returncode}. Run again to resume.')
        if not verified(part, entry):
            raise RuntimeError(f'Hash/length mismatch: {part}. This file was not added to the model cache.')
        destination.parent.mkdir(parents=True, exist_ok=True)
        part.replace(destination)
        print(f'Verified downloaded file: {name}', flush=True)

    with ThreadPoolExecutor(max_workers=3) as pool:
        list(pool.map(fetch, FILES))
    if not args.check_only:
        (cache / 'refs').mkdir(parents=True, exist_ok=True)
        (cache / 'refs' / 'main').write_text(COMMIT, encoding='ascii')
    check_embeddings(runtime, project)
    if not args.check_only:
        marker = runtime / 'model-cache' / '.lat-ai-e5-ready.json'
        temporary = marker.with_suffix('.tmp')
        temporary.write_text(json.dumps({
            'model': MODEL, 'commit': COMMIT, 'weights_sha256': WEIGHTS_SHA256,
            'embedding_shape': [2, 384], 'query_shape': [384], 'checked_offline': True,
            'verified_at_utc': datetime.now(timezone.utc).isoformat(),
        }, indent=2), encoding='utf-8')
        temporary.replace(marker)
    print(f'Model ready: {snapshot}', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as error:
        print(f'Model cache setup failed: {error}', file=sys.stderr)
        print('Use the prepared Python 3.12 runtime and run setup-runtime.ps1 first.', file=sys.stderr)
        raise SystemExit(1)
