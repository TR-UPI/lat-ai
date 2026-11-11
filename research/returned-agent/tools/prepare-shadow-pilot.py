"""Freeze independently reviewed local cases; does not call a model or any backend."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,hashlib
TASKS={'L1.types.1','L1.condition.1','L2.range.1','L2.accumulator.1'}
def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def indexed(rows):
    if not isinstance(rows,list):raise ValueError('Expected a list')
    result={}
    for row in rows:
        key=row.get('id')
        if not isinstance(key,str) or not key or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.' for c in key) or key in result:raise ValueError('Invalid or duplicate case ID')
        result[key]=row
    return result
def valid_checks(row):
    value=row.get('checks')
    if not isinstance(value,list) or len(value)!=3 or any(type(x) is not bool for x in value):raise ValueError('All three checks must be explicitly labeled booleans')
    return value

def normalized_reviewer_id(value):
    if not isinstance(value,str) or not value.strip():raise ValueError('Non-empty reviewer ID required')
    # Compare identities consistently, while retaining the exact supplied snapshots.
    # This cannot prove that differently named IDs belong to different people.
    return ' '.join(value.split()).casefold()

def validate_reviewer_roles(review_a,review_b,adjudications):
    identities={normalized_reviewer_id(review_a.get('reviewer_id')),normalized_reviewer_id(review_b.get('reviewer_id'))}
    if len(identities)!=2:raise ValueError('Two distinct reviewers required')
    for row in adjudications.get('cases',[]):
        if normalized_reviewer_id(row.get('reviewer_id')) in identities:raise ValueError('Adjudicator must be distinct from both initial reviewers')
def freeze(responses,review_a,review_b,adjudications,out):
    if responses.get('data_origin')!='real_student' or not responses.get('privacy_reviewed_by'):raise ValueError('Real-data origin and completed de-identification review must be recorded')
    ids=indexed(responses.get('cases'))
    if not ids:raise ValueError('Empty pilot')
    validate_reviewer_roles(review_a,review_b,adjudications)
    for review in [review_a,review_b]:
        if review.get('completed_without_model_results') is not True:raise ValueError('Review must be completed blind to model results')
    a=indexed(review_a.get('cases'));b=indexed(review_b.get('cases'));ad=indexed(adjudications.get('cases',[]))
    if set(a)!=set(ids) or set(b)!=set(ids) or set(ad)-set(ids):raise ValueError('Review IDs must match the response set')
    cases=[];disagreements=[];ambiguities=[]
    for key,c in ids.items():
        if set(c)-{'id','task_key','answer','category','anonymous_group_id'}:raise ValueError('Unexpected response metadata; remove identifying fields')
        if c.get('task_key') not in TASKS:raise ValueError('Unsupported task; coordinate mapping separately')
        if not isinstance(c.get('answer'),str) or not c['answer'].strip() or len(c['answer'])>4000:raise ValueError('Invalid answer; do not silently truncate')
        ca,cb=valid_checks(a[key]),valid_checks(b[key]);expected=ca
        for row in [a[key],b[key]]:
            if 'ambiguous_rubric' in row and type(row['ambiguous_rubric']) is not bool:raise ValueError('Ambiguity flag must be boolean')
        ambiguous=a[key].get('ambiguous_rubric',False) or b[key].get('ambiguous_rubric',False)
        if ca!=cb:disagreements.append(key)
        if ambiguous:ambiguities.append(key)
        if ca!=cb or ambiguous:
            if key not in ad or not isinstance(ad[key].get('reason'),str) or not ad[key]['reason'].strip():raise ValueError('Unresolved teacher disagreement: '+key)
            expected=valid_checks(ad[key])
        elif key in ad:raise ValueError('Unexpected adjudication for an agreed case')
        cases.append({**c,'expected':expected,'label_source':'two_human_reviews'+('_adjudicated' if ca!=cb or ambiguous else '')})
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    data=(json.dumps(cases,ensure_ascii=False,indent=2)+'\n').encode();(out/'primary-cases.json').write_bytes(data)
    for repeat in range(1,4):
        repeated=[{**c,'id':f'R{repeat}-'+c['id'],'source_id':c['id'],'repeat':repeat} for c in cases]
        (out/f'repeat{repeat}.json').write_text(json.dumps(repeated,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    input_hashes={}
    for name,value in [('responses',responses),('review-A',review_a),('review-B',review_b),('adjudication',adjudications)]:
        encoded=(json.dumps(value,ensure_ascii=False,sort_keys=True,indent=2)+'\n').encode('utf-8')
        (out/(name+'.frozen.json')).write_bytes(encoded);input_hashes[name+'.frozen.json']=hashlib.sha256(encoded).hexdigest()
    for name in ['primary-cases.json','repeat1.json','repeat2.json','repeat3.json']:
        input_hashes[name]=hashlib.sha256((out/name).read_bytes()).hexdigest()
    manifest=dict(frozen_utc=datetime.now(timezone.utc).isoformat(),sha256=hashlib.sha256(data).hexdigest(),files_sha256=input_hashes,unique_cases=len(cases),teacher_disagreements=disagreements,rubric_ambiguities=ambiguities,reviewers=[review_a['reviewer_id'],review_b['reviewer_id']],data_origin='real_student',model_results_seen_during_labeling=False,notes='Metadata records declarations, not independent verification of identity or anonymity. Primary n is unique cases; repeated model calls do not enlarge n. Freeze model source SHA separately before inference. Input snapshots use canonical JSON serialization; hashes refer to these saved bytes, not original formatting.')
    (out/'freeze.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    return manifest
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('responses');p.add_argument('review_a');p.add_argument('review_b');p.add_argument('adjudications');p.add_argument('new_output');a=p.parse_args()
    print(json.dumps(freeze(read(a.responses),read(a.review_a),read(a.review_b),read(a.adjudications),a.new_output),ensure_ascii=False))
