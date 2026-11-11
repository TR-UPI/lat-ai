from pathlib import Path
import shutil
root=Path(__file__).resolve().parent.parent;base=root/'outputs/u02-investigation-2026-11-11';out=base/'reverse-crossover';out.mkdir(exist_ok=False)
source=(root/'tools/diagnose-u02-crossover.mjs').read_text(encoding='utf-8')
source=source.replace("out=join(root,'outputs/u02-investigation-2026-11-11/crossover')","out=join(root,'outputs/u02-investigation-2026-11-11/reverse-crossover')")
source=source.replace("sessions:[{id:'B-A-B',order:['V11','U02','N05','U15','U02','V11','U02']}]","sessions:[{id:'A-B-A',order:['N05','U15','U02','V11','U02','N05','U15','U02']}]")
source=source.replace('Within ONE owned model instance: B=V11,U02; then A=N05,U15,U02; then B=V11,U02.','Within ONE owned model instance: A=N05,U15,U02; then B=V11,U02; then A=N05,U15,U02. Reverse follow-up because B-A-B did not switch back after its first U02 undergrade.')
source=source.replace('{sessions:1,assessments:7,target_U02:3}','{sessions:1,assessments:8,target_U02:3}')
source=source.replace("condition:stepIndex===4?'A':'B'","condition:stepIndex===4?'B':'A'")
(root/'tools/diagnose-u02-reverse-crossover.mjs').write_text(source,encoding='utf-8')
for name in ['model-fingerprint.json','current-reconstructed-requests.json']:shutil.copy2(base/name,out/name)
print('Prepared reverse A-B-A, eight known assessments, three U02 targets; no prompt changes.')
