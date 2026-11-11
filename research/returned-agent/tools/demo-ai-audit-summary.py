"""Retained end-to-end return-summary fixture, no real people or model calls."""
from pathlib import Path
import importlib.util,json,subprocess,sys,uuid,copy

ROOT=Path(__file__).resolve().parent.parent;OUT=ROOT/'outputs/ai-readiness-and-audit-summary-2026-11-11'
spec=importlib.util.spec_from_file_location('summary_demo',ROOT/'tools/summarize-audit-returns.py');s=importlib.util.module_from_spec(spec);spec.loader.exec_module(s);r=s.r
protocol=OUT/'summary-protocol.json';s.verify(protocol)
demo=OUT/'TECHNICAL_FIXTURE';demo.mkdir();source=demo/'source';(source/'reviewer').mkdir(parents=True)
def save(p,v):r.lease.publish(p,r.binary(v))
commands=[]
def cli(label,tool,args,expected=0):
    run=subprocess.run([sys.executable,str(ROOT/'tools'/tool),*map(str,args)],capture_output=True,text=True,encoding='utf-8',timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    save(demo/(label+'.json'),{'mode':'TECHNICAL_FIXTURE','returncode':run.returncode,'expected':expected,'stdout':run.stdout,'stderr':run.stderr})
    commands.append({'label':label,'returncode':run.returncode,'expected':expected});assert run.returncode==expected,(label,run.stderr);return json.loads(run.stdout)
base=r.read(ROOT/'outputs/manual-audit-intake-2026-11-11/TECHNICAL_FIXTURE/rendered/reviewer/cards.json')['cards'][0]
cards=[]
for ident in ['1'*32,'2'*32]:
    c={k:copy.deepcopy(v) for k,v in base.items() if k!='citation_readout'};c['audit_id']=ident;cards.append(c)
save(source/'reviewer/cards.json',{'phase':'POST-LABEL TECHNICAL_FIXTURE summary rehearsal only','cards':cards})
r.lease.publish(source/'reviewer/READ_FIRST.txt',b'TECHNICAL_FIXTURE, no real people.')
save(source/'PRIVATE_COORDINATOR.json',{'selection':[{'audit_id':c['audit_id'],'source_id':'fixture-'+str(n),'stratum':'fixture'} for n,c in enumerate(cards)],'protocol_sha256':'fixture'})
save(source/'MANIFEST.json',{n:r.digest(source/n) for n in ['reviewer/cards.json','reviewer/READ_FIRST.txt','PRIVATE_COORDINATOR.json']})
rendered=demo/'rendered';render=subprocess.run([str(ROOT/'work/lat-ai-runtime/node/node.exe'),str(ROOT/'tools/render-signal-review-cards.mjs'),'render',str(r.m.PRESENTATION),str(source),str(rendered)],capture_output=True,timeout=30,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0));assert render.returncode==0,render.stderr
save(demo/'renderer.json',{'mode':'TECHNICAL_FIXTURE','returncode':render.returncode,'stdout':render.stdout.decode(),'stderr':render.stderr.decode()})
store=demo/'FIXTURE_STORE';assignments=[];coordinator='99999999-9999-4999-8999-999999999999'
for n in range(1,6):
    reviewer=f'{n}'*8+'-'+f'{n}'*4+'-4'+f'{n}'*3+'-8'+f'{n}'*3+'-'+f'{n}'*12
    folder=demo/f'assignment-{n}';r.safe_prepare(s.RECOVERY,rendered,reviewer,store,folder);assignments.append(folder)
    if n>3:continue
    delivery=r.read(folder/'DELIVERY_TEMPLATE.json');delivery.update(coordinator_registry_id=coordinator,delivered_utc=r.now().isoformat().replace('+00:00','Z'),prior_exposure_confirmed_by_coordinator={'before_this_audit':'none','details':'TECHNICAL_FIXTURE only'})
    returned=r.read(folder/'reviewer/cards.json')
    for pos,c in enumerate(returned['cards']):
        criteria=['met','not_met','met'] if n!=2 else ['not_met','not_met','met']
        if pos==1 and n>=2:criteria=['uncertain']*3
        c.update(human_decision={'criteria':criteria,'citation_sufficiency':['unreadable','not_selected','sufficient'],'contradiction':'present' if n<3 else 'absent','contradiction_fragment_ids':[0,1] if n==1 else [1] if n==2 else []},human_reason='TECHNICAL_FIXTURE: scripted fields, no actual reviewer or semantic approval.',reviewer_registry_id=reviewer,reviewed_utc=r.now().isoformat().replace('+00:00','Z'),prior_exposure_declared={'before_this_audit':'none','details':'Scripted fixture','saw_verifier_readout':True})
    dp=demo/f'delivery-{n}.json';rp=demo/f'return-{n}.json';save(dp,delivery);save(rp,returned);r.safe_receive(s.RECOVERY,folder,rp,dp,store,str(uuid.uuid4()))
def amend(folder,updates,label):
    a,aid=r.assignment_state(store,folder);state=r.effective(store,folder);corrected=copy.deepcopy(state['current_delivery']);corrected.update(updates)
    req={'operation_id':str(uuid.uuid4()),'action':'amend_delivery','author_registry_id':'77777777-7777-4777-8777-777777777777','technical_reviewer_registry_id':'88888888-8888-4888-8888-888888888888','reason':'TECHNICAL_FIXTURE only, not an actual human approval.','expected_store_id':a['intake_store_id'],'expected_assignment_sha256':aid,'expected_parent_delivery_sha256':state['current_delivery_sha256'],'corrected_delivery':corrected};p=demo/(label+'-request.json');save(p,req);r.execute(s.RECOVERY,store,folder,p)
amend(assignments[2],{'prior_exposure_confirmed_by_coordinator':{'before_this_audit':'unknown','details':'fixture uncertainty'}},'exposure-unknown')
amend(assignments[2],{'prior_exposure_confirmed_by_coordinator':{'before_this_audit':'none','details':'fixture later correction'}},'exposure-none')
index={'store_id':r.read(store/'STORE.json')['store_id'],'mode':'TECHNICAL_FIXTURE','assignments':[{'path':str(p),'assignment_sha256':r.digest(p/'ASSIGNMENT.json')} for p in assignments[:4]]};save(demo/'INDEX.json',index)
def snapshot():return {p.relative_to(store).as_posix():r.digest(p) for p in store.rglob('*') if p.is_file()}
before=snapshot();cli('01_export','summarize-audit-returns.py',['export',protocol,store,demo/'INDEX.json',demo/'SUMMARY_BEFORE'])
cli('02_verify','summarize-audit-returns.py',['verify-export',protocol,store,demo/'SUMMARY_BEFORE']);assert snapshot()==before
index['assignments'].reverse();save(demo/'INDEX_REVERSED.json',index)
cli('03_export_reversed','summarize-audit-returns.py',['export',protocol,store,demo/'INDEX_REVERSED.json',demo/'SUMMARY_REVERSED'])
assert (demo/'SUMMARY_BEFORE/SUMMARY.json').read_bytes()==(demo/'SUMMARY_REVERSED/SUMMARY.json').read_bytes();assert snapshot()==before
first=r.read(demo/'SUMMARY_BEFORE/SUMMARY.json');assert first['counts']['issued_not_in_index']==1 and first['counts']['without_registered_return']==1 and first['counts']['excluded_assignments']==1 and len(first['groups'])==2
assert all(g['eligible_return_count']==2 and g['excluded_return_count']==1 and g['missing_return_count']==1 for g in first['groups'])
old=r.digest(demo/'SUMMARY_BEFORE/SUMMARY.json');amend(assignments[0],{'delivered_utc':'2099-01-01T00:00:00Z'},'future-date')
before=snapshot();stale=cli('04_verify_stale','summarize-audit-returns.py',['verify-export',protocol,store,demo/'SUMMARY_BEFORE'],3);assert stale['current_snapshot_matches'] is False
cli('05_export_current','summarize-audit-returns.py',['export',protocol,store,demo/'INDEX.json',demo/'SUMMARY_AFTER'])
cli('06_verify_current','summarize-audit-returns.py',['verify-export',protocol,store,demo/'SUMMARY_AFTER']);assert snapshot()==before and r.digest(demo/'SUMMARY_BEFORE/SUMMARY.json')==old
last=r.read(demo/'SUMMARY_AFTER/SUMMARY.json');assert last['counts']['excluded_assignments']==2
result={'mode':'TECHNICAL_FIXTURE','actual_human_returns':0,'model_calls':0,'issued_fixture_assignments':5,'indexed_fixture_assignments':4,'unindexed_issuance_visible':True,'missing_return_visible':True,'distinct_ids_identical_text_not_merged':True,'unknown_exposure_not_erased':True,'index_permutation_summary_byte_identical':True,'later_amendment_detected_as_stale':True,'old_export_preserved':True,'summary_commands_store_read_only':True,'commands':commands,'renderer_exit':0,'before_counts':first['counts'],'after_counts':last['counts']}
save(demo/'DEMO_RESULT.json',result);print(json.dumps(result,ensure_ascii=False))
