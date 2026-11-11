from pathlib import Path
import hashlib
import json
import shutil

root = Path(__file__).resolve().parents[1]
candidate = root / 'work/assessment-candidate4-2026-11-11'
shutil.copytree(root / 'work/assessment-candidate3-2026-11-11', candidate)
path = candidate / 'integration/ai/core/src/assessment.mjs'
text = path.read_text(encoding='utf-8')
marker = 'Верни только JSON с criterion_1, criterion_2, criterion_3.'
addition = '''Номер фрагмента означает прямое подтверждение именно этого критерия. Выводить промежуточные шаги за ученика запрещено: утверждение «условие истинно» не является утверждением «выполняется if, else пропускается». Критерий о выбранной ветке требует упоминания ветки в ответе; одного результата сравнения или печати недостаточно.
Взаимоисключающие утверждения тоже являются противоречием: «значения — строки» и «значения — числа» нельзя одновременно зачесть как верное определение типа, даже если во второй фразе нет слова «не».
Пример независимости критериев: критерии «условие истинно; выполняется if, else пропускается; вывод A». Ответ [0: "Условие истинно", 1: "На экране A"] => {"criterion_1":0,"criterion_2":-1,"criterion_3":1}.
'''
assert text.count(marker) == 1
path.write_text(text.replace(marker, addition + marker), encoding='utf-8', newline='\n')
rubric_path = candidate / 'integration/ai/core/data/assessment-rubrics.json'
rubrics = json.loads(rubric_path.read_text(encoding='utf-8'))
rubrics['assessment_revision'] = '2026-11-11-evidence-v1'
rubric_path.write_text(json.dumps(rubrics, ensure_ascii=False, indent=2) + '\n', encoding='utf-8', newline='\n')
files = ['src/assessment.mjs', 'src/local-model.mjs', 'data/assessment-rubrics.json']
manifest = {file: hashlib.sha256((candidate / 'integration/ai/core' / file).read_bytes()).hexdigest() for file in files}
(root / 'outputs/assessment-fix-2026-11-11/candidate4-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(candidate)
