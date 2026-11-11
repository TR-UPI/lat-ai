import json,os,pathlib,subprocess,sys
root=pathlib.Path(__file__).resolve().parents[1]
out=pathlib.Path(r'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-08/shag-model-selection/outputs/document-pilot-2026-11-11')
python=r'C:/Users/ASUS ROG STRIX/Documents/Codex/2026-11-08/shag-model-selection/work/tester-release/LAD AI Windows/runtime/python/python.exe'
bootstrap="import sys,os,runpy;sys.path.insert(0,"+repr(str(root/'backend'))+");sys.path.append("+repr(str(root/'.runtime/python/Lib/site-packages'))+");os.environ['DJANGO_SETTINGS_MODULE']='config.ai_local';os.environ['LAD_AI_TEST']='1';sys.argv=['manage.py','test','accounts','courses','documents','progress','tutor','--verbosity','1'];runpy.run_path("+repr(str(root/'backend/manage.py'))+",run_name='__main__')"
commands={
 'django-final':[python,'-B','-c',bootstrap],
 'node-final':['C:/Program Files/nodejs/node.exe','--test',*[str(p.relative_to(root)) for p in sorted((root/'integration/ai/test').glob('*.test.mjs'))]],
 'frontend-final':['C:/Program Files/nodejs/node.exe','--test','tests/document-pilot-frontend.test.cjs','tests/dashboard-api.test.cjs','tests/editor-context.test.cjs'],
 'core-provenance':['C:/Program Files/nodejs/node.exe','integration/ai/check.mjs'],
 'django-check':[python,'-B','tools/pilot.py','--python-extra-site','.runtime/python/Lib/site-packages','--runtime','.runtime/pilot-check','manage','check'],
}
results=[]
for name,command in commands.items():
    if name=='frontend-final':
        command=['C:/Program Files/nodejs/node.exe','--test',*[str(p.relative_to(root)) for p in sorted((root/'tests').glob('*.test.cjs'))]]
    result=subprocess.run(command,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
    (out/(name+'.log')).write_bytes(result.stdout)
    results.append({'suite':name,'exit_code':result.returncode,'log':name+'.log'})
    print(name,result.returncode,flush=True)
(out/'verification.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
sys.exit(any(item['exit_code'] for item in results))
