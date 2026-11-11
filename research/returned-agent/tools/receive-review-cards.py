"""Offline post-label audit intake. Never modifies primary labels, model grades or source files."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re, shutil, uuid, math, sys
from contextlib import contextmanager

ROOT=Path(__file__).resolve().parent.parent
PRESENTATION=ROOT/'outputs/review-card-fragments-2026-11-11/presentation-protocol.json'
DEPENDENCIES=['tools/receive-review-cards.py','tools/test-receive-review-cards.py','tools/render-signal-review-cards.mjs','outputs/review-card-fragments-2026-11-11/presentation-protocol.json']
EDITABLE={'human_decision','human_reason','reviewer_registry_id','reviewed_utc','prior_exposure_declared'}
EXPOSED=['cards.json','CARDS.txt','READ_FIRST.txt','FILLING_GUIDE.txt']
UUID=re.compile(r'[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z')
utcnow=lambda:datetime.now(timezone.utc)
sha=lambda data:hashlib.sha256(data).hexdigest()
digest=lambda p:sha(Path(p).read_bytes())
canonical=lambda value:json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False)

GUIDE='''LAT AI — заполнение карточек после слепой разметки
Редактируйте КОПИЮ cards.json. Менять можно только пять полей внутри каждой карточки.
Сохраните все карточки в исходном порядке. Тексты, raw, номера, цитаты и guide не менять.
human_decision — объект ровно с четырьмя полями:
  criteria: три значения "met", "not_met" или "uncertain" (критерии1,2,3).
  citation_sufficiency: три значения "sufficient", "insufficient", "uncertain",
    "not_selected" или "unreadable". Это достаточность ПОКАЗАННОЙ ссылки verifier,
    а не цитаты, которую вы сами нашли. При -1 обязательно not_selected; при
    unreadable/invalid_reference обязательно unreadable. Для выбранной ссылки
    допустимы sufficient/insufficient/uncertain. Оценка критерия независима от этого.
  contradiction: "present", "absent" или "uncertain" по всему ответу.
  contradiction_fragment_ids: уникальные целые номера из таблицы. При present
    хотя бы один; обе стороны могут находиться в одном фрагменте. При absent [];
    при uncertain можно [] или известные относящиеся к сомнению фрагменты.
human_reason — непустое объяснение до8000символов: основания решений по критериям,
цитатам и противоречиям; явно объясните каждый uncertain. Автоматически смысл не проверяется.
reviewer_registry_id — назначенный координатором канонический lowercase UUIDv4.
reviewed_utc — фактическое время YYYY-MM-DDTHH:MM:SSZ (UTC), не раньше выдачи.
prior_exposure_declared — объект:
  before_this_audit: "none", "some" или "unknown";
  details: непустое описание (для none можно «ранее не видел»);
  saw_verifier_readout: true — подтверждение просмотра текущей расшифровки.
Возвращайте именно JSON; заполненный TXT вручную переносится в JSON с проверкой человеком.
Неопределённость допустима и требует дальнейшего ручного разбора; не угадывайте ради приёма.
Результат — мнение после показа verifier, не новый независимый gold и не исправление балла.
Комбинации: met допустим при not_selected/unreadable/insufficient; человек может
найти объяснение в другом месте ответа. not_met допустим даже при sufficient,
но требует разбора (например, локальная цитата верна, весь ответ противоречив).
Все решения по критериям независимы от достаточности показанной ссылки; такие
расхождения сохраняются как вопросы человеку, не как автоматически доказанные ошибки.
unknown exposure и uncertain — допустимые ответы. Не заменяйте их догадками.
Не добавляйте имена/контакты ученика или рецензента. При ошибке исправьте отдельную копию;
принятый пакет не заменяется автоматически. Перед выдачей этого руководства нужен
координатор: назначение/согласия/обезличивание и независимость людей кодом не доказаны.
'''

def pairs(items):
    result={}
    for k,v in items:
        if k in result:raise ValueError('duplicate_json_key: '+k)
        result[k]=v
    return result
def decode(data):
    def integer(s):
        value=int(s)
        if abs(value)>9007199254740991:raise ValueError('json_integer_outside_exact_js_range')
        return value
    def floating(s):
        value=float(s)
        if not math.isfinite(value):raise ValueError('non_finite_json')
        return value
    value=json.loads(data.decode('utf-8-sig'),object_pairs_hook=pairs,parse_int=integer,parse_float=floating,parse_constant=lambda s:(_ for _ in ()).throw(ValueError('non_finite_json')))
    def strings(v):
        if isinstance(v,str):
            if any(0xD800<=ord(c)<=0xDFFF for c in v):raise ValueError('unpaired_unicode_surrogate')
        elif isinstance(v,dict):
            for k,x in v.items():strings(k);strings(x)
        elif isinstance(v,list):
            for x in v:strings(x)
    strings(value);return value
def read(p):return decode(Path(p).read_bytes())
def save(p,v):
    with Path(p).open('x',encoding='utf-8') as f:f.write(json.dumps(v,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
def keys(value,expected,label):
    if not isinstance(value,dict) or set(value)!=set(expected):raise ValueError(label+'_fields')
def identity(value):
    if not isinstance(value,str) or not UUID.fullmatch(value):raise ValueError('registry_id_must_be_canonical_uuid4')
    return value
def timestamp(value):
    if not isinstance(value,str) or not re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z',value):raise ValueError('utc_timestamp_required')
    return datetime.fromisoformat(value.replace('Z','+00:00'))
def text(value,label):
    if not isinstance(value,str) or not value.strip() or len(value)>8000:raise ValueError(label+'_nonempty_text_required')
def exposure(value):
    keys(value,['before_this_audit','details','saw_verifier_readout'],'exposure')
    if value['before_this_audit'] not in ['none','some','unknown'] or value['saw_verifier_readout'] is not True:raise ValueError('exposure_declaration_required')
    text(value['details'],'exposure_details')
def verify_hashes(folder,manifest):
    for n,h in manifest.items():
        p=Path(n)
        if p.is_absolute() or '..' in p.parts or '\\' in n or ':' in n:raise ValueError('unsafe_manifest_path')
        if digest(folder/p)!=h:raise ValueError('artifact_changed: '+n)

def freeze(path):
    save(path,{'revision':'post-label-intake-v1','created_utc':utcnow().isoformat(),'files_sha256':{n:digest(ROOT/n) for n in DEPENDENCIES},'policy':'Formal completeness and provenance only. Full assignment, one reviewer, no silent replacement. Uncertain accepted with human followup. Never replace blind reference or model scores.'})
    Path(str(path)+'.sha256').write_text(digest(path)+'\n',encoding='ascii')
def verify_protocol(path):
    if digest(path)!=Path(str(path)+'.sha256').read_text().strip():raise ValueError('intake_protocol_changed')
    p=read(path)
    if set(p['files_sha256'])!=set(DEPENDENCIES):raise ValueError('intake_dependencies_changed')
    verify_hashes(ROOT,p['files_sha256'])
    presentation=read(PRESENTATION)
    if digest(PRESENTATION)!=Path(str(PRESENTATION)+'.sha256').read_text().strip():raise ValueError('presentation_protocol_changed')
    verify_hashes(ROOT,presentation['files_sha256'])

@contextmanager
def store_reservation(store):
    root=Path(store);root.mkdir(parents=True,exist_ok=True);lock=root/'intake.lock';token=str(uuid.uuid4())
    with lock.open('x',encoding='ascii') as f:f.write(token)
    try:
        if not (root/'STORE.json').exists():save(root/'STORE.json',{'store_id':str(uuid.uuid4()),'scope':'Single coordinated intake registry; not cross-store deduplication.'})
        yield root
    finally:
        if lock.read_text(encoding='ascii')==token:lock.unlink()

def package_key(cards,reviewer):
    contents=[{k:c[k] for k in ['task_code','criteria','student_answer','verifier_output']} for c in cards['cards']]
    return sha(canonical({'reviewer':reviewer,'content':sorted(contents,key=canonical)}).encode('utf-8'))

def prepare(protocol,rendered,reviewer,store,new_assignment):
    verify_protocol(protocol);identity(reviewer)
    source=Path(rendered);manifest=read(source/'MANIFEST.json')
    expected={'PRIVATE_DELIVERY.json','reviewer/cards.json','reviewer/CARDS.txt','reviewer/READ_FIRST.txt'}
    if set(manifest)!=expected:raise ValueError('rendered_manifest_fields')
    verify_hashes(source,manifest)
    delivery=read(source/'PRIVATE_DELIVERY.json')
    if delivery['presentation_protocol_sha256']!=digest(PRESENTATION):raise ValueError('presentation_revision_mismatch')
    if delivery['files_seen_sha256']!={n:manifest['reviewer/'+n] for n in EXPOSED[:3]}:raise ValueError('rendered_exposure_mismatch')
    cards=read(source/'reviewer/cards.json');ids=[]
    for c in cards['cards']:
        if any(c[k] is not None for k in EDITABLE):raise ValueError('only_unfilled_source_cards')
        if not re.fullmatch('[a-f0-9]{32}',c['audit_id']):raise ValueError('invalid_card_id')
        ids.append(c['audit_id'])
    if not ids or len(set(ids))!=len(ids):raise ValueError('duplicate_or_empty_cards')
    with store_reservation(store) as root:
        for n in ['issued','issuance-reservations']:(root/n).mkdir(exist_ok=True)
        key=package_key(cards,reviewer)
        if (root/'issuance-reservations'/(key+'.json')).exists() or (root/'issued'/(key+'.json')).exists():raise ValueError('same_content_and_reviewer_already_reserved_or_issued_manual_review_required')
        out=Path(new_assignment)
        if out.exists():raise FileExistsError(out)
        assignment_id=str(uuid.uuid4())
        save(root/'issuance-reservations'/(key+'.json'),{'assignment_id':assignment_id,'package_reviewer_key':key,'created_utc':utcnow().isoformat(),'new_assignment_path':str(out.resolve())})
        out.mkdir(parents=True,exist_ok=False);(out/'reviewer').mkdir()
        for n in EXPOSED[:3]:shutil.copyfile(source/'reviewer'/n,out/'reviewer'/n)
        (out/'reviewer/FILLING_GUIDE.txt').write_text(GUIDE,encoding='utf-8')
        assignment={'revision':'post-label-intake-v1','assignment_id':assignment_id,'created_utc':utcnow().isoformat().replace('+00:00','Z'),'reviewer_registry_id':reviewer,'intake_store_id':read(root/'STORE.json')['store_id'],'package_reviewer_key':key,'intake_protocol_sha256':digest(protocol),'source_render_manifest_sha256':digest(source/'MANIFEST.json'),'audit_ids':ids,'files_seen_sha256':{n:digest(out/'reviewer'/n) for n in EXPOSED},'scope':'Post-label audit only; origin and independent identity not proven by hashes.'}
        save(out/'ASSIGNMENT.json',assignment)
        save(out/'DELIVERY_TEMPLATE.json',{'assignment_sha256':digest(out/'ASSIGNMENT.json'),'recipient_registry_id':reviewer,'coordinator_registry_id':None,'delivered_utc':None,'files_seen_sha256':assignment['files_seen_sha256'],'prior_exposure_confirmed_by_coordinator':None})
        save(out/'MANIFEST.json',{'ASSIGNMENT.json':digest(out/'ASSIGNMENT.json'),**{'reviewer/'+n:assignment['files_seen_sha256'][n] for n in EXPOSED}})
        save(root/'issued'/(key+'.json'),{'assignment_id':assignment_id,'assignment_sha256':digest(out/'ASSIGNMENT.json'),'intake_store_id':assignment['intake_store_id']})
        return {'assignment':str(out),'cards':len(ids),'delivery_recorded':False}

def validate(original,returned,assignment,delivery,now):
    errors=[];followup=[]
    try:
        keys(delivery,['assignment_sha256','recipient_registry_id','coordinator_registry_id','delivered_utc','files_seen_sha256','prior_exposure_confirmed_by_coordinator'],'delivery')
        if identity(delivery['recipient_registry_id'])!=assignment['reviewer_registry_id']:raise ValueError('delivery_recipient_mismatch')
        if identity(delivery['coordinator_registry_id'])==delivery['recipient_registry_id']:raise ValueError('coordinator_and_reviewer_ids_must_differ')
        if delivery['files_seen_sha256']!=assignment['files_seen_sha256']:raise ValueError('delivery_exposure_hashes_mismatch')
        delivered=timestamp(delivery['delivered_utc'])
        if not timestamp(assignment['created_utc'])<=delivered<=now:raise ValueError('delivery_time_out_of_range')
        confirmed=delivery['prior_exposure_confirmed_by_coordinator']
        keys(confirmed,['before_this_audit','details'],'coordinator_exposure')
        if confirmed['before_this_audit'] not in ['none','some','unknown']:raise ValueError('coordinator_exposure_status')
        text(confirmed['details'],'coordinator_exposure_details')
    except (KeyError,ValueError,TypeError) as e:return [{'location':'delivery','code':str(e)}],[]
    if not isinstance(returned,dict) or set(returned)!=set(original):return [{'location':'package','code':'top_level_fields_changed'}],[]
    if canonical({k:v for k,v in returned.items() if k!='cards'})!=canonical({k:v for k,v in original.items() if k!='cards'}):errors.append({'location':'package','code':'metadata_changed'})
    if not isinstance(returned['cards'],list) or [c.get('audit_id') if isinstance(c,dict) else None for c in returned['cards']]!=assignment['audit_ids']:
        return errors+[{'location':'package','code':'missing_duplicate_foreign_or_reordered_cards'}],[]
    for old,c in zip(original['cards'],returned['cards']):
        ident=old['audit_id']
        try:
            if set(c)!=set(old):raise ValueError('card_fields_changed')
            if canonical({k:v for k,v in c.items() if k not in EDITABLE})!=canonical({k:v for k,v in old.items() if k not in EDITABLE}):raise ValueError('immutable_card_content_changed')
            if identity(c['reviewer_registry_id'])!=assignment['reviewer_registry_id']:raise ValueError('reviewer_mismatch')
            reviewed=timestamp(c['reviewed_utc'])
            if not delivered<=reviewed<=now:raise ValueError('review_time_out_of_range')
            text(c['human_reason'],'human_reason');exposure(c['prior_exposure_declared'])
            decision=c['human_decision'];keys(decision,['criteria','citation_sufficiency','contradiction','contradiction_fragment_ids'],'human_decision')
            if not isinstance(decision['criteria'],list) or len(decision['criteria'])!=3 or any(v not in ['met','not_met','uncertain'] for v in decision['criteria']):raise ValueError('three_criterion_decisions_required')
            citations=decision['citation_sufficiency']
            if not isinstance(citations,list) or len(citations)!=3:raise ValueError('three_citation_decisions_required')
            for i,(value,ref) in enumerate(zip(citations,old['citation_readout']['references'])):
                allowed=['sufficient','insufficient','uncertain'] if ref['status']=='fragment_selected' else ['not_selected'] if ref['status']=='no_fragment_selected' else ['unreadable']
                if value not in allowed:raise ValueError('citation_decision_not_applicable_'+str(i+1))
            if decision['contradiction'] not in ['present','absent','uncertain']:raise ValueError('contradiction_decision_required')
            ids=decision['contradiction_fragment_ids'];n=old['citation_readout']['fragment_count']
            if not isinstance(ids,list) or any(type(i) is not int or i<0 or i>=n for i in ids) or len(set(ids))!=len(ids):raise ValueError('contradiction_fragment_ids_invalid')
            if (decision['contradiction']=='present' and not ids) or (decision['contradiction']=='absent' and ids):raise ValueError('contradiction_evidence_mismatch')
            reasons=[]
            for criterion,ref,quality in zip(decision['criteria'],old['citation_readout']['references'],citations):
                if (ref['status']=='fragment_selected' and criterion=='not_met') or (ref['status']=='no_fragment_selected' and criterion=='met'):
                    if 'disagreement_with_displayed_verifier' not in reasons:reasons.append('disagreement_with_displayed_verifier')
                if criterion=='not_met' and quality=='sufficient' and 'human_combination_requires_explanation' not in reasons:reasons.append('human_combination_requires_explanation')
            if decision['contradiction']=='present':reasons.append('contradiction_reported_by_reviewer')
            if 'uncertain' in decision['criteria']+citations+[decision['contradiction']]:reasons.append('uncertain_human_decision')
            declared=c['prior_exposure_declared']['before_this_audit'];confirmed_status=confirmed['before_this_audit']
            if declared!=confirmed_status:reasons.append('exposure_declaration_disagreement')
            if 'unknown' in [declared,confirmed_status]:reasons.append('unknown_prior_exposure')
            if 'unreadable' in citations:reasons.append('unreadable_verifier_reference')
            if reasons:followup.append({'audit_id':ident,'reasons':reasons})
        except (KeyError,ValueError,TypeError) as e:errors.append({'location':ident,'code':str(e)})
    return errors,followup

def saved_attempt(folder):
    manifest=read(folder/'MANIFEST.json')
    if set(manifest)!={'returned.json','delivery.json','ASSIGNMENT.json','RECEIPT.json'}:raise ValueError('saved_attempt_manifest_fields')
    verify_hashes(folder,manifest)
    return read(folder/'RECEIPT.json')

def verified_commit(root,marker,assignment_sha):
    value=read(marker)
    keys(value,['assignment_sha256','attempt_id','receipt_sha256'],'commit')
    if value['assignment_sha256']!=assignment_sha or not re.fullmatch('[a-f0-9]{64}',value['attempt_id']):raise ValueError('accepted_marker_identity_mismatch')
    folder=root/'attempts'/value['attempt_id'];receipt=saved_attempt(folder)
    if digest(folder/'RECEIPT.json')!=value['receipt_sha256'] or receipt['assignment_sha256']!=assignment_sha or receipt['attempt_id']!=value['attempt_id'] or receipt['validation_passed'] is not True:raise ValueError('accepted_marker_receipt_mismatch')
    return value

def receive(protocol,assignment_dir,returned_path,delivery_path,store):
    verify_protocol(protocol);base=Path(assignment_dir);manifest=read(base/'MANIFEST.json')
    if set(manifest)!={'ASSIGNMENT.json',*('reviewer/'+n for n in EXPOSED)}:raise ValueError('assignment_manifest_fields')
    verify_hashes(base,manifest);assignment=read(base/'ASSIGNMENT.json');assignment_sha=digest(base/'ASSIGNMENT.json')
    if assignment['intake_protocol_sha256']!=digest(protocol):raise ValueError('intake_revision_mismatch')
    if assignment['files_seen_sha256']!={n:manifest['reviewer/'+n] for n in EXPOSED}:raise ValueError('assignment_exposure_mismatch')
    raw_return=Path(returned_path).read_bytes();raw_delivery=Path(delivery_path).read_bytes()
    attempt_id=sha((assignment_sha+sha(raw_return)+sha(raw_delivery)).encode())
    with store_reservation(store) as root:
        if assignment['intake_store_id']!=read(root/'STORE.json')['store_id']:raise ValueError('wrong_intake_store')
        issued=read(root/'issued'/(assignment['package_reviewer_key']+'.json'))
        if issued['assignment_sha256']!=assignment_sha or issued['assignment_id']!=assignment['assignment_id']:raise ValueError('issuance_registry_mismatch')
        (root/'attempts').mkdir(exist_ok=True);(root/'accepted').mkdir(exist_ok=True)
        accepted=root/'accepted'/(assignment_sha+'.json');attempt=root/'attempts'/attempt_id
        commit=verified_commit(root,accepted,assignment_sha) if accepted.exists() else None
        if attempt.exists():
            receipt=saved_attempt(attempt)
            if receipt['validation_passed'] and (commit is None or commit['attempt_id']!=attempt_id):raise ValueError('incomplete_or_conflicting_commit_requires_manual_review')
            return {**receipt,'repeat_of_saved_attempt':True}
        attempt.mkdir();(attempt/'returned.json').write_bytes(raw_return);(attempt/'delivery.json').write_bytes(raw_delivery)
        (attempt/'ASSIGNMENT.json').write_bytes((base/'ASSIGNMENT.json').read_bytes())
        errors=[];followup=[]
        if commit is not None:errors=[{'location':'package','code':'assignment_already_accepted_no_automatic_replacement'}]
        else:
            try:
                delivery=decode(raw_delivery);returned=decode(raw_return)
                if delivery.get('assignment_sha256')!=assignment_sha:raise ValueError('delivery_assignment_mismatch')
                errors,followup=validate(read(base/'reviewer/cards.json'),returned,assignment,delivery,utcnow())
            except (ValueError,TypeError,AttributeError) as e:errors=[{'location':'input','code':str(e)}]
        receipt={'attempt_id':attempt_id,'assignment_sha256':assignment_sha,'received_utc':utcnow().isoformat(),'validation_passed':not errors,'status':'validated_post_label_only' if not errors else 'rejected','errors':errors,'followup':followup,'cards_in_assignment':len(assignment['audit_ids']),'independent_gold':False,'changes_model_scores':False,'limitations':'Formal validation only. Identity, true exposure, honest time and semantic reasoning require people. No quality rates computed.'}
        save(attempt/'RECEIPT.json',receipt)
        save(attempt/'MANIFEST.json',{n:digest(attempt/n) for n in ['returned.json','delivery.json','ASSIGNMENT.json','RECEIPT.json']})
        if not errors:save(accepted,{'assignment_sha256':assignment_sha,'attempt_id':attempt_id,'receipt_sha256':digest(attempt/'RECEIPT.json')})
        return {**receipt,'repeat_of_saved_attempt':False}

if __name__=='__main__':
    p=argparse.ArgumentParser();sub=p.add_subparsers(dest='mode',required=True)
    f=sub.add_parser('freeze');f.add_argument('new_protocol')
    a=sub.add_parser('prepare');a.add_argument('protocol');a.add_argument('rendered');a.add_argument('reviewer_uuid');a.add_argument('store');a.add_argument('new_assignment')
    r=sub.add_parser('receive');r.add_argument('protocol');r.add_argument('assignment');r.add_argument('returned');r.add_argument('delivery');r.add_argument('store')
    args=p.parse_args()
    result=freeze(args.new_protocol) if args.mode=='freeze' else prepare(args.protocol,args.rendered,args.reviewer_uuid,args.store,args.new_assignment) if args.mode=='prepare' else receive(args.protocol,args.assignment,args.returned,args.delivery,args.store)
    print(json.dumps(result,ensure_ascii=False))
    if isinstance(result,dict) and result.get('validation_passed') is False:sys.exit(2)
