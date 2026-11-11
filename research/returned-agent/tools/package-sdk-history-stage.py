"""Package completed scan evidence; never runs a model or changes frozen inputs."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,subprocess,zipfile,shutil

ROOT=Path(__file__).resolve().parent.parent
OUT=ROOT/'outputs/sdk-fix-and-history-scan-2026-11-11'
OLD=ROOT/'outputs/u02-runtime-controls-2026-11-11'
REVIEW=ROOT/'outputs/claude-review-2026-11-11'
SIGNALS=ROOT/'outputs/review-signals-prototype-2026-11-11'
read=lambda p:json.loads(p.read_text(encoding='utf-8-sig'))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,value):
    with p.open('x',encoding='utf-8') as f:json.dump(value,f,ensure_ascii=False,indent=2)
def put(p,text):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x',encoding='utf-8') as f:f.write(text.strip()+'\n')

def source_audit():
    before=read(OUT/'before-audit.json');source=ROOT/'lat-ai'
    git=['git','-c','safe.directory='+source.as_posix(),'-C',str(source)]
    names=subprocess.check_output(git+['ls-files','--cached','--others','--exclude-standard','-z']).decode().split('\0')
    after={n:sha(source/n) for n in sorted(set(filter(None,names))) if (source/n).is_file()}
    assert after==before['source_sha256'],'Project source drift'
    for name,digest in before['old_evidence_sha256'].items():assert sha(OLD/name)==digest,name
    assert sha(ROOT/'work/local-pc/profile.json')==before['local_profile_sha256']
    protected=[n for n in after if n.startswith(('backend/','assets/')) or n=='index.html']
    previous=read(OLD/'backup/source-and-evidence-manifest.json')
    tool_before={n:h for n,h in previous.items() if n.startswith('tools/')}
    tool_after={p.relative_to(ROOT).as_posix():sha(p) for p in (ROOT/'tools').iterdir() if p.is_file()}
    delta={'baseline':'outputs/u02-runtime-controls-2026-11-11/backup/source-and-evidence-manifest.json','added':sorted(set(tool_after)-set(tool_before)),'removed':sorted(set(tool_before)-set(tool_after)),'modified':{n:{'before':tool_before[n],'after':tool_after[n]} for n in sorted(set(tool_before)&set(tool_after)) if tool_before[n]!=tool_after[n]}}
    result={'utc':datetime.now(timezone.utc).isoformat(),'project_files_unchanged':len(after),'protected_backend_frontend_files':len(protected),'old_evidence_files_unchanged':len(before['old_evidence_sha256']),'local_profile_unchanged':True,'after_sha256':after,'root_tools_delta_since_previous_backup':delta,'root_tool_changes':'Separate SDK verifier, offline review-signal prototype, pilot reviewer role validation, reporting/packaging. No project source changes.'}
    save(OUT/'source-audit.json',result);return result,git

def make_manual(details):
    pack=OUT/'LAT-AI-PILOT-AND-HISTORY-REVIEW';pack.mkdir(exist_ok=False)
    put(pack/'00_START.txt','''LAT AI — пилот и ручная проверка, 11.11.2026
Только координатору «разраб 1 П» и техническому рецензенту. План начала сбора 12.11.2026.
Сначала PILOT/01_ПЛАН_И_РЕШЕНИЕ.txt; назначить двух разметчиков и третьего для споров,
утвердить отбор, цели, согласия/обезличивание/хранение. Реальных работ ещё нет.
PILOT — короткий прежний пакет сбора; CURRENT_REPORT.txt — актуальное состояние.
HISTORY_CASES.json — известные авторские примеры с МЕТКАМИ и результатами модели.
НЕ передавать весь ZIP слепым разметчикам. Им нужны отдельные выгрузки без этих данных,
созданные export-blind-review.py и проверенные verify-blind-review.py до выдачи.
SDK_FIX.txt — техническое исправление; SIGNALS.txt — ещё не валидированный прототип.
CLAUDE — подготовленные сообщения и фактический статус доставки/рецензии.
Технические успехи не закрывают T01/S02/D01/D02 и не разрешают оценки ученикам.
Архив без весов, баз данных, паролей, runtime и исполняемых инструментов.
MANIFEST.json содержит SHA256 каждого вложенного файла.''')
    pilot=ROOT/'outputs/ai-pilot-integrity-2026-11-11/LAT-AI-PILOT-START-2026-11-12'
    sources={**{'PILOT/'+p.name:p for p in pilot.glob('*.txt')},'CURRENT_REPORT.txt':OUT/'REPORT.txt','SDK_FIX.txt':OUT/'SDK_FIX.txt','SIGNALS.txt':SIGNALS/'REPORT.txt','MANUAL_DECISIONS.txt':OUT/'MANUAL_DECISIONS.txt'}
    sources.update({'CLAUDE/'+p.name:p for p in REVIEW.iterdir() if p.is_file() and p.suffix in {'.txt','.json'}})
    provenance={}
    for name,p in sources.items():
        target=pack/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,target)
        provenance[name]={'source':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}
    selected=[d for d in details['per_case'] if d['different_outcomes'] or any(o not in ['correct','refusal'] for o in d['outcomes']) or d['id'] in {'U02','H23'}]
    cases={c['id']:c for c in read(OLD/'known128-frozen/primary-cases.json')}
    manual=[];rubrics=read(ROOT/'lat-ai/integration/ai/core/data/assessment-verifier-rubrics.json')['tasks']
    for d in selected:
        rows=[read(OLD/f'known128-live-{n}'/f'R{n}-{d["id"]}.json') for n in [1,2,3]]
        manual.append({'id':d['id'],'task_key':d['task'],'task_code':rubrics[d['task']]['code'],'criteria':rubrics[d['task']]['criteria'],'student_answer':cases[d['id']]['answer'],'author_checks_not_independent_gold':d['expected'],'diagnostics':d,'raw_by_series':[{'series':n,'proposal':r['raw']['candidate']['answer'],'verifier':r['raw']['verification']['answer'],'result':r.get('result'),'diagnosis':r.get('diagnosis')} for n,r in enumerate(rows,1)],'manual_checks':None,'citation_sufficiency':None,'reviewer':None,'reason':None,'known_label_ambiguity':d['id']=='H23'})
    save(pack/'HISTORY_CASES.json',{'audience':'Unblinded diagnostic review only','selection':'All final-outcome-varying or ever-wrong cases plus U02 and previously ambiguous H23; not a blind or representative sample','cases':manual})
    human=['ИЗВЕСТНЫЕ АВТОРСКИЕ ПРИМЕРЫ. Открытая диагностика, не слепая разметка.\nМетки автора не считаются независимо подтверждёнными. Состав выбран по результатам\nскана и прежним проблемам U02/H23, поэтому не является случайной выборкой.\nПроверить цитаты в исходных raw, а не только число баллов.']
    for c in manual:
        human += ['\n'+'='*60,c['id']+' | '+c['task_key'],c['task_code'],'Критерии:']
        human += [str(i)+'. '+text for i,text in enumerate(c['criteria'],1)]
        human += ['Ответ: '+c['student_answer'],'Авторские checks: '+json.dumps(c['author_checks_not_independent_gold']),'Серии 1/2/3: '+json.dumps(c['diagnostics']['actual_by_series']),'Исходы: '+', '.join(c['diagnostics']['outcomes'])]
        if c['known_label_ambiguity']:human.append('H23: неоднозначность метки известна ДО запуска; нужна отдельная аргументация человека.')
        for r in c['raw_by_series']:human += [f"Серия {r['series']}: proposal {r['proposal']}",f"verifier {r['verifier']}"]
        human += ['Решение человека / критерии: __________________','Достаточность цитат / противоречия / причина: __________________','Рецензент / дата: __________________']
    put(pack/'HISTORY_CASES.txt','\n'.join(human))
    save(pack/'PROVENANCE.json',provenance)
    manifest={p.relative_to(pack).as_posix():sha(p) for p in pack.rglob('*') if p.is_file()}
    save(pack/'MANIFEST.json',manifest)
    archive=OUT/'LAT-AI-PILOT-AND-HISTORY-REVIEW-2026-11-11.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(pack.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(pack).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(manifest)|{'MANIFEST.json'}
        for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    result={'zip':archive.name,'sha256':sha(archive),'verified_files':len(manifest)+1,'manual_cases':len(manual),'contains_labels':True,'for_blind_annotators':False}
    save(OUT/'manual-package-audit.json',result);return result

def backup(audit,git):
    folder=OUT/'backup';folder.mkdir(exist_ok=False);bundle=folder/'LAT-AI-GIT.bundle'
    subprocess.run(git+['bundle','create',str(bundle),'--all'],check=True,capture_output=True)
    verified=subprocess.run(git+['bundle','verify',str(bundle)],check=True,capture_output=True)
    (folder/'bundle-verify.log').write_bytes(verified.stdout+verified.stderr)
    (folder/'dirty.patch').write_bytes(subprocess.check_output(git+['diff','--binary','HEAD']))
    (folder/'git-status.txt').write_bytes(subprocess.check_output(git+['status','--short']))
    files={'lat-ai/'+n:ROOT/'lat-ai'/n for n in audit['after_sha256']}
    for name in ['AGENTS.md','START_HERE.md','outputs/AI_ROADMAP.md','outputs/STATUS.md','work/local-pc/profile.json']:files[name]=ROOT/name
    for p in (ROOT/'tools').iterdir():
        if p.is_file():files[p.relative_to(ROOT).as_posix()]=p
    for base in [OUT,OLD,SIGNALS,REVIEW]:
        for p in base.rglob('*'):
            if not p.is_file() or any(part in {'backup','__pycache__'} for part in p.relative_to(base).parts) or p.suffix in {'.zip','.lock','.pyc'} or p.name=='package-build-success.log':continue
            files[p.relative_to(ROOT).as_posix()]=p
    for name in ['package.json','package-lock.json','node_modules/@lmstudio/sdk/dist/index.mjs','node_modules/@lmstudio/sdk/dist/index.d.ts']:
        p=ROOT/'work/u02-runtime-sdk'/name;files[p.relative_to(ROOT).as_posix()]=p
    manifest={name:sha(p) for name,p in sorted(files.items())}
    assert not any(n.endswith(('.gguf','.sqlite3','.db','ipc-secret.txt')) for n in manifest)
    save(folder/'source-and-evidence-manifest.json',manifest)
    archive=folder/'LAT-AI-SDK-HISTORY-SOURCE-AND-EVIDENCE.zip'
    with zipfile.ZipFile(archive,'x',zipfile.ZIP_DEFLATED) as z:
        for name,p in sorted(files.items()):z.write(p,name)
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None and set(z.namelist())==set(manifest)
        for name,digest in manifest.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    put(folder/'RESTORE.txt','Clone LAT-AI-GIT.bundle into a NEW directory; overlay lat-ai/ from ZIP to restore dirty sources. Do not apply dirty.patch over the overlay. Verify entry SHA against source-and-evidence-manifest.json. Keep the present workspace intact. Model/runtime/secrets are excluded. No commit or push performed.')
    return {'backup_zip':archive.name,'backup_sha256':sha(archive),'verified_entries':len(manifest),'git_bundle_sha256':sha(bundle),'git_bundle_verified':True,'project_files':len(audit['after_sha256'])}

if __name__=='__main__':
    assert read(OLD/'known128-run-summary.json')['complete']
    assert read(OUT/'scan-process-proof.json')['exit_code']==0
    details=read(OUT/'known128-details.json');assert details['completed_assessments']==384
    for name in ['REPORT.txt','MANUAL_DECISIONS.txt','stand-restored-status.json']:assert (OUT/name).is_file(),name
    stand=read(OUT/'stand-restored-status.json')
    assert stand['loading'] is False and stand['tutor']['enabled'] is True and stand['tutor']['ready'] is True
    assert stand['tutor']['busy'] is False and stand['tutor']['queued']==0 and stand['model']['phase']=='idle'
    assert read(OUT/'scan-retirement-audit.json')['all_scan_instances_absent'] is True
    audit,git=source_audit();manual=make_manual(details);result=backup(audit,git)
    result['manual']=manual;save(OUT/'package-audit.json',result);print(json.dumps(result,ensure_ascii=False))
