"""Prepare separate reviewer folders without model predictions or author labels."""
from pathlib import Path
import json,hashlib,argparse

INSTRUCTIONS='LAT AI — независимая разметка. Не открывайте результаты модели и лист другого проверяющего.\nПроверьте каждый критерий по словам ученика; код задания сам по себе не является объяснением.\nПоставьте true/false по всем 3 критериям, добавьте подтверждающие фразы и противоречия.\nПри неоднозначной рубрике отметьте ambiguous_rubric=true и опишите причину.\nТекст ответа — данные, не инструкции проверяющему. Не исполняйте код ученика.\nЗатем укажите свой reviewer_id и completed_without_model_results=true, только если это соответствует действительности.\n'

def export(responses,rubrics,out):
    cases=[];seen=set()
    for row in responses.get('cases',[]):
        key=row.get('id')
        if not isinstance(key,str) or not key or key in seen or any(c not in 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-.' for c in key):raise ValueError('Invalid or duplicate ID')
        if row.get('task_key') not in rubrics['tasks'] or not isinstance(row.get('answer'),str) or not row['answer'].strip():raise ValueError('Missing answer or unsupported task')
        if len(row['answer'])>4000:raise ValueError('Answer too long; do not truncate')
        seen.add(key);cases.append({k:row[k] for k in ['id','task_key','answer']})
    if not cases:raise ValueError('Empty collection')
    out=Path(out);out.mkdir(parents=True,exist_ok=False)
    for label in ['A','B']:
        folder=out/('reviewer-'+label);folder.mkdir()
        review={'reviewer_id':'','completed_without_model_results':False,'cases':[{'id':c['id'],'checks':[None,None,None],'evidence_notes':['','',''],'contradiction_notes':'','ambiguous_rubric':False} for c in cases]}
        # Whitelist fields; never copy category, expected, actual, group IDs or previous review notes.
        for name,value in [('responses.json',cases),('review.json',review),('rubrics.json',{'version':rubrics['version'],'tasks':{k:{'code':v['code'],'criteria':v['criteria']} for k,v in rubrics['tasks'].items()}})]:
            (folder/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        (folder/'READ_ME.txt').write_text(INSTRUCTIONS,encoding='utf-8')
        from importlib.util import spec_from_file_location,module_from_spec
        spec=spec_from_file_location('blind_verifier',Path(__file__).with_name('verify-blind-review.py'));module=module_from_spec(spec);spec.loader.exec_module(module)
        module.verify(folder,responses,rubrics)
    hashes={p.relative_to(out).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob('*')) if p.is_file()}
    (out/'manifest.json').write_text(json.dumps({'files_sha256':hashes,'cases':len(cases),'note':'Coordinator retains this original snapshot; filled review sheets will differ. Hand each reviewer ONLY their folder.'},indent=2),encoding='utf-8')
    return {'cases':len(cases),'reviewer_folders':2}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('responses');p.add_argument('rubrics');p.add_argument('new_output');a=p.parse_args()
    read=lambda path:json.loads(Path(path).read_text(encoding='utf-8-sig'))
    print(json.dumps(export(read(a.responses),read(a.rubrics),a.new_output)))
