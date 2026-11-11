"""Post-label human audit only; deterministic sampling, no inference or scoring writes."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, importlib.util, json

ROOT = Path(__file__).resolve().parent.parent
FILES = ['tools/prepare-signal-review-audit.py', 'tools/test-signal-review-audit.py']
PUBLIC_FIELDS = {'audit_id', 'task_code', 'criteria', 'student_answer', 'verifier_output',
                 'human_decision', 'human_reason', 'reviewer_registry_id', 'reviewed_utc',
                 'prior_exposure_declared'}
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()

def save(p, value):
    with Path(p).open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)

def load_signal_module():
    spec = importlib.util.spec_from_file_location('signal_pilot', ROOT/'tools/review-signal-pilot.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

def rank(seed, purpose, identity):
    return hashlib.sha256(json.dumps([seed, purpose, identity], ensure_ascii=False).encode()).hexdigest()

def select(primary, seed, control_count):
    if type(control_count) is not int or control_count < 1:
        raise ValueError('Positive integer control count required')
    if not isinstance(seed, str) or not seed:
        raise ValueError('Predeclared seed required')
    ids = [r['id'] for r in primary]
    if any(not isinstance(i, str) or not i for i in ids) or len(set(ids)) != len(ids):
        raise ValueError('Unique nonempty identities required')
    strata = {}
    for r in primary:
        status, flag = r['status'], r['manual_review_suggested']
        if status == 'no_signal_found' and flag is False: group = 'control'
        elif status == 'signals_found' and flag is True: group = 'flagged'
        elif status == 'technical_error' and flag is True: group = 'technical'
        elif status == 'unsupported_task' and flag is None: group = 'unsupported'
        else: raise ValueError('Inconsistent signal status')
        strata[r['id']] = group
    controls = sorted((i for i in ids if strata[i] == 'control'), key=lambda i: rank(seed, 'sample', i))[:control_count]
    selected = [i for i in ids if strata[i] != 'control'] + controls
    selected.sort(key=lambda i: rank(seed, 'display', i))
    return selected, strata

def public_cards(selected, inputs, rubrics, seed):
    cards = []
    for identity in selected:
        row = inputs[identity]
        rubric = rubrics.get(row['task_key'])
        if rubric is None:
            # Unsupported tasks must be resolved by coordinator before human exposure.
            raise ValueError('Missing task/rubric for human review: '+row['task_key'])
        verification = row['verification']
        raw = verification.get('answer') if isinstance(verification, dict) else None
        cards.append({'audit_id': rank(seed, 'opaque', identity)[:32],
                      'task_code': rubric['code'], 'criteria': rubric['criteria'],
                      'student_answer': row['student_answer'], 'verifier_output': raw,
                      'human_decision': None, 'human_reason': None, 'reviewer_registry_id': None,
                      'reviewed_utc': None, 'prior_exposure_declared': None})
    assert all(set(c) == PUBLIC_FIELDS for c in cards)
    return cards

def freeze(protocol, rules, seed, control_count):
    load_signal_module().verify_rules(rules)
    select([], seed, control_count)
    value = {'revision': 'post-label-audit-v1', 'created_utc': datetime.now(timezone.utc).isoformat(),
             'signal_protocol_sha256': sha(rules), 'seed': seed, 'control_count': control_count,
             'files_sha256': {n: sha(ROOT/n) for n in FILES},
             'policy': 'Primary series only. All flagged/technical/unsupported plus up to control_count no-signal cases. Mixed deterministic display order. Post-label only; never initial blind annotation. No scoring/gate changes; selected sample is not prevalence estimate.'}
    save(protocol, value)
    Path(str(protocol)+'.sha256').write_text(sha(protocol)+'\n', encoding='ascii')

def export(protocol, rules, plan_path, signal_dir, output):
    helper = load_signal_module()
    plan = helper.preflight(rules, plan_path)
    if sha(protocol) != Path(str(protocol)+'.sha256').read_text().strip():
        raise ValueError('Audit protocol changed')
    policy = read(protocol)
    if policy['signal_protocol_sha256'] != sha(rules) or set(policy['files_sha256']) != set(FILES):
        raise ValueError('Audit dependency mismatch')
    for name, digest in policy['files_sha256'].items():
        if sha(ROOT/name) != digest: raise ValueError('Audit tool changed: '+name)
    frozen = read(Path(plan['frozen_dir'])/'freeze.json')
    frozen_dir = Path(plan['frozen_dir'])
    for name, digest in plan['dataset_sha256'].items():
        if Path(name).name != name or sha(frozen_dir/name) != digest:
            raise ValueError('Dataset differs from model plan')
    if frozen.get('model_results_seen_during_labeling') is not False:
        raise ValueError('Prior blind labeling must be declared')
    for name, digest in frozen['files_sha256'].items():
        if Path(name).name != name or sha(frozen_dir/name) != digest:
            raise ValueError('Frozen human data changed')
    if helper.timestamp(policy['created_utc']) >= helper.timestamp(frozen['frozen_utc']):
        raise ValueError('Audit selection must be frozen before real data')
    source = Path(signal_dir)
    manifest = read(source/'MANIFEST.json')
    if not {'signal-inputs.json', 'signals.json', 'signal-analysis.json', 'review-queue.json', 'batch.log'} <= set(manifest):
        raise ValueError('Incomplete signal export')
    for name, digest in manifest.items():
        if Path(name).name != name or sha(source/name) != digest: raise ValueError('Signal export changed')
    analysis = read(source/'signal-analysis.json')
    if analysis['model_plan_sha256'] != sha(plan_path) or analysis['rule_protocol_sha256'] != sha(rules):
        raise ValueError('Signal provenance mismatch')
    payload = read(source/'signals.json')
    if payload['input_sha256'] != sha(source/'signal-inputs.json'): raise ValueError('Signal inputs mismatch')
    rows = payload['rows']; inputs = read(source/'signal-inputs.json')
    keys = [(r['series'], r['id']) for r in rows]
    input_keys = [(r['series'], r['id']) for r in inputs]
    primary = [r for r in rows if r['series'] == 1]
    cases = {c['id']: c for c in read(frozen_dir/'primary-cases.json')}
    if {r['id'] for r in primary} != set(cases): raise ValueError('Pilot case identities differ')
    for row in inputs:
        case = cases.get(row['id'])
        if case is None or row['student_answer'] != case['answer'] or row['task_key'] != case['task_key']:
            raise ValueError('Pilot answer/task differs')
    required = {(n, r['id']) for r in primary for n in (1, 2, 3)}
    if len(keys) != len(set(keys)) or len(input_keys) != len(set(input_keys)) or set(keys) != required or set(input_keys) != required or not primary:
        raise ValueError('Three complete unique series required')
    if any(r.get('advisory_only') is not True or r.get('changes_score') is not False or r.get('changes_gate') is not False for r in rows):
        raise ValueError('Advisory-only signals required')
    selected, strata = select(primary, policy['seed'], policy['control_count'])
    cards = public_cards(selected, {r['id']: r for r in inputs if r['series'] == 1},
                         read(ROOT/'lat-ai/integration/ai/core/data/assessment-verifier-rubrics.json')['tasks'], policy['seed'])
    out = Path(output); out.mkdir(parents=True, exist_ok=False)
    review = out/'reviewer'; review.mkdir()
    save(review/'cards.json', {'phase': 'POST-LABEL model-output audit; NOT initial blind rating', 'cards': cards})
    (review/'READ_FIRST.txt').write_text('Review only after the two independent blind labels and adjudication are frozen. Model output is deliberately visible. Hidden selection status does not make this a blind assessment of student quality. No signal is not evidence of correctness. Record prior exposure, registry ID, UTC time, decision and reason. Do not assign or publish student grades.\n', encoding='utf-8')
    save(out/'PRIVATE_COORDINATOR.json', {'protocol_sha256': sha(protocol), 'signal_export_manifest_sha256': sha(source/'MANIFEST.json'),
         'selection': [{'audit_id': c['audit_id'], 'source_id': i, 'stratum': strata[i]} for i,c in zip(selected, cards)],
         'population_by_stratum': {s: sum(v == s for v in strata.values()) for s in ('control','flagged','technical','unsupported')},
         'exposure_receipt': {'recipient_registry_id': None, 'delivered_utc': None, 'files_seen_sha256': {p.name:sha(p) for p in review.iterdir()}}})
    save(out/'MANIFEST.json', {p.relative_to(out).as_posix(): sha(p) for p in out.rglob('*') if p.is_file()})
    return {'selected':len(cards), 'controls':sum(strata[i]=='control' for i in selected), 'quality_claim':False}

if __name__ == '__main__':
    parser = argparse.ArgumentParser(); commands = parser.add_subparsers(dest='mode', required=True)
    f = commands.add_parser('freeze'); f.add_argument('protocol'); f.add_argument('rules'); f.add_argument('seed'); f.add_argument('control_count', type=int)
    e = commands.add_parser('export'); e.add_argument('protocol'); e.add_argument('rules'); e.add_argument('plan'); e.add_argument('signal_directory'); e.add_argument('new_output')
    args = parser.parse_args()
    result = freeze(args.protocol,args.rules,args.seed,args.control_count) if args.mode=='freeze' else export(args.protocol,args.rules,args.plan,args.signal_directory,args.new_output)
    print(json.dumps(result,ensure_ascii=False))
