"""Strict structural audit of a reviewer handout before issuing it. No semantic privacy claim."""
from pathlib import Path
import json,argparse

def verify(folder,reference_responses,reference_rubrics):
    folder=Path(folder)
    paths=list(folder.rglob('*'))
    if any(p.is_symlink() for p in paths):raise ValueError('Symlinks are not allowed')
    files={p.relative_to(folder).as_posix() for p in paths if p.is_file()}
    if files!={'responses.json','review.json','rubrics.json','READ_ME.txt'}:raise ValueError('Unexpected or missing handout files')
    read=lambda name:json.loads((folder/name).read_text(encoding='utf-8-sig'))
    responses=read('responses.json')
    expected=[{k:r[k] for k in ['id','task_key','answer']} for r in reference_responses['cases']]
    if responses!=expected or any(set(r)!={'id','task_key','answer'} for r in responses):raise ValueError('Response whitelist or content mismatch')
    if len({r['id'] for r in responses})!=len(responses):raise ValueError('Duplicate IDs')
    rubric=read('rubrics.json');expected_rubric={'version':reference_rubrics['version'],'tasks':{k:{'code':v['code'],'criteria':v['criteria']} for k,v in reference_rubrics['tasks'].items()}}
    if rubric!=expected_rubric:raise ValueError('Rubric whitelist or content mismatch')
    review=read('review.json')
    expected_review={'reviewer_id':'','completed_without_model_results':False,'cases':[{'id':r['id'],'checks':[None,None,None],'evidence_notes':['','',''],'contradiction_notes':'','ambiguous_rubric':False} for r in responses]}
    if review!=expected_review:raise ValueError('Review contains prefilled labels or extra metadata')
    from importlib.util import spec_from_file_location,module_from_spec
    spec=spec_from_file_location('exporter',Path(__file__).with_name('export-blind-review.py'));module=module_from_spec(spec);spec.loader.exec_module(module)
    if (folder/'READ_ME.txt').read_text(encoding='utf-8')!=module.INSTRUCTIONS:raise ValueError('Reviewer instructions changed')
    return {'passed':True,'cases':len(responses),'files':4,'limitation':'Structural whitelist only. Personal data or label hints embedded in the original answer require human review. Run before issuing blank handout; filled reviews intentionally fail.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('folder');p.add_argument('responses');p.add_argument('rubrics');a=p.parse_args();read=lambda p:json.loads(Path(p).read_text(encoding='utf-8-sig'));print(json.dumps(verify(a.folder,read(a.responses),read(a.rubrics))))
