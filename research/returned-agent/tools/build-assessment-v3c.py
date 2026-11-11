from pathlib import Path
import shutil,json
root=Path(__file__).resolve().parents[1];src=root/'work/assessment-v3b-2026-11-11';dst=root/'work/assessment-v3c-2026-11-11'
assert not dst.exists();shutil.copytree(src,dst)
p=dst/'integration/ai/core/src/assessment-verifier.mjs';s=p.read_text(encoding='utf-8')
negative={
'L1.types.1':dict(student_answer=[dict(id='S1',text='Два аргумента имеют строковый тип'),dict(id='S2',text='Плюс объединяет эти тексты'),dict(id='S3',text='32 на экран не поступает')],output=dict(left_string='S1',right_string='S1',concatenation='S2',output_32=None,counter_1=None,counter_2=None,counter_3='S3')),
'L1.condition.1':dict(student_answer=[dict(id='S1',text='x:2, равенство верно'),dict(id='S2',text='Выполнен if, else пропущен'),dict(id='S3',text='Напечатано нет')],output=dict(x_two='S1',condition_true='S1',if_runs='S2',else_skipped='S2',output_yes=None,counter_1=None,counter_2=None,counter_3='S3')),
'L2.range.1':dict(student_answer=[dict(id='S1',text='Перебор 2,3,4'),dict(id='S2',text='Граница5 не включается'),dict(id='S3',text='Печать всех чисел в одной строке')],output=dict(value_two='S1',value_three='S1',value_four='S1',stop_excluded='S2',separate_lines=None,counter_1=None,counter_2=None,counter_3='S3')),
'L2.accumulator.1':dict(student_answer=[dict(id='S1',text='s задано нулём один раз до цикла, не сбрасывается'),dict(id='S2',text='Шаги1,2,3 дают суммы1,3,6'),dict(id='S3',text='print в теле цикла на каждом шаге')],output=dict(initial_zero='S1',no_reset='S1',sum_one='S2',sum_three='S2',sum_six='S2',print_outside=None,print_once=None,counter_1=None,counter_2=None,counter_3='S3'))}
s=s.replace('export const assessmentSystem=', 'const partialExamples='+json.dumps(negative,ensure_ascii=False,separators=(',',':'))+';\nexport const assessmentSystem=')
s=s.replace('return {format_demonstration:demonstrations[req.assessment.task_key],trusted_code:task.code,trusted_criteria:task.criteria,','return {format_demonstration:demonstrations[req.assessment.task_key],partial_demonstration:partialExamples[req.assessment.task_key],')
s=s.replace('format_demonstration — пример формата и логики, не часть оцениваемого ответа.', 'format_demonstration и partial_demonstration — примеры формата, не часть оцениваемого ответа. Не оценивай ответ целиком: извлекай каждый факт независимо. Одна ошибочная фраза не отменяет остальные верные утверждения.')
p.write_text(s,encoding='utf-8')
p=dst/'integration/ai/core/src/assessment.mjs';p.write_text('''import {readFileSync} from 'node:fs';
import {validateAssessment as validateFacts} from './assessment-verifier.mjs';
export {assessmentInput,assessmentSystem,assessmentSchema} from './assessment-verifier.mjs';
export const rubrics=JSON.parse(readFileSync(new URL('../data/assessment-rubrics.json',import.meta.url),'utf8'));
export function validateAssessment(raw,answer){return validateFacts(raw,answer,raw?.task_key);}
''',encoding='utf-8')
p=dst/'integration/ai/core/src/local-model.mjs';s=p.read_text(encoding='utf-8')
s=s.replace("import {assessmentInput as verifierInput,assessmentSystem as verifierSystem,assessmentSchema as verifierSchema} from './assessment-verifier.mjs';\n",'')
s=s.replace('assessmentSchema,validateCandidate','assessmentSchema')
start=s.index(' async generate(req,options){');end=s.index(' async #generateOnce',start)
s=s[:start]+''' async generate(req,options){
  const raw=await this.#generateOnce(req,options);
  return req.role==='assess'?{...raw,task_key:req.assessment.task_key}:raw;
 }
'''+s[end:]
s=s.replace('maxTokens=192,verification=false','maxTokens=192').replace('(verification?verifierSystem:assessmentSystem)','assessmentSystem').replace('(verification?verifierInput(req):assessmentInput(req))','assessmentInput(req)').replace('(verification?verifierSchema(req):assessmentSchema(req))','assessmentSchema(req)')
p.write_text(s,encoding='utf-8')
p=dst/'integration/ai/core/data/assessment-rubrics.json';j=json.loads(p.read_text());j['assessment_revision']='2026-11-11-evidence-v3c-atomic-single';p.write_text(json.dumps(j,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
print('C isolated: one atomic extraction call, positive+partial examples, no whole-program grading input; not selected for deployment')
