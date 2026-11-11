"""Offline, read-only dependency and evidence preflight. Never declares pedagogical readiness."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,hashlib,json,sys,importlib.util

ROOT=Path(__file__).resolve().parent.parent
BASE='outputs/audit-recovery-2026-11-11'
NAV={'AGENTS.md','START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md'}
PROTOCOLS={
 'signals':'outputs/review-signals-prototype-2026-11-11/signal-protocol.json',
 'sampling':'outputs/claude-reviewed-ai-continuation-2026-11-11/audit-protocol.json',
 'presentation':'outputs/review-card-fragments-2026-11-11/presentation-protocol.json',
 'intake':'outputs/manual-audit-intake-2026-11-11/intake-protocol.json',
 'recovery':BASE+'/recovery-protocol.json',
 'return_summary':'outputs/ai-readiness-and-audit-summary-2026-11-11/summary-protocol.json'}
FILES=['tools/check-ai-readiness.py','tools/test-check-ai-readiness.py',BASE+'/backup/source-and-evidence-manifest.json',BASE+'/package-audit.json',BASE+'/postpackage-verification.json',BASE+'/source-audit.json',*PROTOCOLS.values()]
read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(path,value):
    with Path(path).open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def safe_path(root,name):
    p=Path(name)
    if p.is_absolute() or '..' in p.parts or ':' in name or '\\' in name:raise ValueError('unsafe_manifest_path')
    result=(root/p).resolve()
    if not result.is_relative_to(root.resolve()):raise ValueError('manifest_path_outside_root')
    return result
def verify_pinned(root,manifest,ignore=frozenset()):
    if set(ignore)-NAV:raise ValueError('only_navigation_may_be_excluded')
    errors=[];checked=0
    for name,expected in sorted(manifest.items()):
        if name in ignore:continue
        path=safe_path(root,name);checked+=1
        if not path.is_file():errors.append({'file':name,'reason':'missing'})
        elif sha(path)!=expected:errors.append({'file':name,'reason':'sha256_changed'})
    return {'passed':not errors,'files_checked':checked,'errors':errors}
def freeze(path):
    save(path,{'revision':'offline-ai-readiness-v1','created_utc':datetime.now(timezone.utc).isoformat(),'files_sha256':{n:sha(ROOT/n) for n in FILES},'scope':'Local code/evidence integrity only. No network/model loads, no claims of human-data or pedagogical readiness.'})
    Path(str(path)+'.sha256').write_text(sha(path)+'\n',encoding='ascii')
def run(protocol):
    if sha(protocol)!=Path(str(protocol)+'.sha256').read_text().strip():raise ValueError('readiness_protocol_changed')
    p=read(protocol)
    if set(p['files_sha256'])!=set(FILES):raise ValueError('readiness_dependencies_changed')
    own=verify_pinned(ROOT,p['files_sha256'])
    if not own['passed']:return {'technical_integrity_passed':False,'checks':{'readiness_dependencies':own},'pedagogical_readiness':'not_evaluated'}
    checks={'prior_source_and_evidence':verify_pinned(ROOT,read(ROOT/BASE/'backup/source-and-evidence-manifest.json'),NAV)}
    source=read(ROOT/BASE/'source-audit.json')['after_sha256'];checks['project_source']=verify_pinned(ROOT/'lat-ai',source)
    values={}
    for label,name in PROTOCOLS.items():
        path=ROOT/name;value=read(path);values[label]=value
        check=verify_pinned(ROOT,value['files_sha256'])
        if sha(path)!=Path(str(path)+'.sha256').read_text().strip():check['passed']=False;check['errors'].append({'file':name,'reason':'protocol_sha256_changed'})
        checks[label]=check
    link=values['sampling']['signal_protocol_sha256']==sha(ROOT/PROTOCOLS['signals'])
    checks['sampling_signal_link']={'passed':link,'errors':[] if link else [{'reason':'sampling_signal_protocol_mismatch'}]}
    package=read(ROOT/BASE/'package-audit.json');proof=read(ROOT/BASE/'postpackage-verification.json')
    archive=ROOT/BASE/package['backup']['path']
    restored=sha(archive)==package['backup']['sha256']==proof['archive_sha256'] and proof['frozen_protocol_verified_from_restored_path'] is True and proof['live_store_not_activated'] is True
    checks['prior_backup_restore_evidence']={'passed':restored,'errors':[] if restored else [{'reason':'backup_restore_evidence_mismatch'}]}
    passed=all(v['passed'] for v in checks.values())
    return {'revision':'offline-ai-readiness-v1','created_utc':datetime.now(timezone.utc).isoformat(),'technical_integrity_passed':passed,'checks':checks,'protocol_sha256':sha(protocol),'source_project_files':len(source),'human_gates':['Real anonymized student answers and declared sampling plan','Independent initial reviewers and adjudicator','Consent/access/anonymization checks by responsible people','Semantic citation/contradiction/rubric review','Decision on quality thresholds and deployment'],'runtime_gates':['SDK v2 normal live verification not established by this offline report','Forced abort/late provisioning needs verified terminal ownership/cancellation proof; do not infer it from one absent model listing'],'pedagogical_readiness':'not_evaluated_no_automatic_release','model_calls':0,'network_calls':0,'changes_scores_or_sources':False,'limitations':'Hashes detect drift relative to the recorded baseline, not authenticity. Existing fixture logs are not student evidence. Navigation is intentionally mutable and excluded from old-baseline comparison.'}
def main():
    p=argparse.ArgumentParser();s=p.add_subparsers(dest='mode',required=True)
    f=s.add_parser('freeze');f.add_argument('new_protocol');c=s.add_parser('check');c.add_argument('protocol');c.add_argument('new_report');a=p.parse_args()
    if a.mode=='freeze':freeze(a.new_protocol);return 0
    result=run(a.protocol);save(a.new_report,result);print(json.dumps({'technical_integrity_passed':result['technical_integrity_passed'],'pedagogical_readiness':result['pedagogical_readiness']},ensure_ascii=False));return 0 if result['technical_integrity_passed'] else 2
if __name__=='__main__':
    try:sys.exit(main())
    except (OSError,ValueError,KeyError) as e:print(json.dumps({'status':'stopped','reason':str(e)},ensure_ascii=False));sys.exit(2)
