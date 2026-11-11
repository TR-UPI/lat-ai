from pathlib import Path
import shutil
root=Path(__file__).resolve().parent.parent
base=root/'outputs/u02-investigation-2026-11-11';out=base/'crossover';out.mkdir(exist_ok=False)
source=(root/'tools/diagnose-u02-order.mjs').read_text(encoding='utf-8')
source=source.replace("out=join(root,'outputs/u02-investigation-2026-11-11')","out=join(root,'outputs/u02-investigation-2026-11-11/crossover')")
old="sessions:[{id:'C1',order:['U02']},{id:'A1',order:['N05','U15','U02']},{id:'B1',order:['V11','U02']},{id:'B2',order:['V11','U02']},{id:'A2',order:['N05','U15','U02']},{id:'C2',order:['U02']}]"
assert old in source
source=source.replace(old,"sessions:[{id:'B-A-B',order:['V11','U02','N05','U15','U02','V11','U02']}]")
source=source.replace('C=fresh owned load U02 first; A=historical first three tasks; B=recent first two tasks. Two loads per condition, mirrored order.','Within ONE owned model instance: B=V11,U02; then A=N05,U15,U02; then B=V11,U02. Follow-up diagnostic frozen after the initial order association, not an independent holdout. This separates instance identity from order; does not isolate cache internals.')
source=source.replace('{sessions:6,assessments:12,target_U02:6}','{sessions:1,assessments:7,target_U02:3}')
source=source.replace('for(const id of session.order){','for(const [stepIndex,id] of session.order.entries()){')
source=source.replace("join(folder,id+'-transport-error.json')","join(folder,String(stepIndex+1)+'-'+id+'-transport-error.json')")
source=source.replace("join(folder,id+'.json')","join(folder,String(stepIndex+1)+'-'+id+'.json')")
source=source.replace('targetRows.push({session:session.id,condition:session.id[0],','targetRows.push({session:session.id,step:stepIndex+1,condition:stepIndex===4?\'A\':\'B\',')
(root/'tools/diagnose-u02-crossover.mjs').write_text(source,encoding='utf-8')
for name in ['model-fingerprint.json','current-reconstructed-requests.json']:shutil.copy2(base/name,out/name)
print('Prepared one-instance B-A-B diagnostic; seven known-case assessments, three U02 observations, no prompt change.')
