from pathlib import Path
import json
root=Path(__file__).resolve().parents[1];p=root/'work/assessment-v3b-2026-11-11/integration/ai/core/src/assessment-verifier.mjs'
s=p.read_text(encoding='utf-8')
examples={
'L1.types.1':dict(student_answer=[dict(id='S1',text='Напечатано 32'),dict(id='S2',text='Оба аргумента строковые'),dict(id='S3',text='Их соединяет плюс')],output=dict(left_string='S2',right_string='S2',concatenation='S3',output_32='S1',counter_1=None,counter_2=None,counter_3=None)),
'L1.condition.1':dict(student_answer=[dict(id='S1',text='Сравнение верно, поскольку x равно 2'),dict(id='S2',text='if печатает да'),dict(id='S3',text='else не выполняется')],output=dict(x_two='S1',condition_true='S1',if_runs='S2',else_skipped='S3',output_yes='S2',counter_1=None,counter_2=None,counter_3=None)),
'L2.range.1':dict(student_answer=[dict(id='S1',text='На первой строке 2, на второй 3, на третьей 4'),dict(id='S2',text='Предел 5 исключается')],output=dict(value_two='S1',value_three='S1',value_four='S1',stop_excluded='S2',separate_lines='S1',counter_1=None,counter_2=None,counter_3=None)),
'L2.accumulator.1':dict(student_answer=[dict(id='S1',text='До цикла s=0 однократно, без сброса внутри'),dict(id='S2',text='Шаги прибавления 1,2,3 дают суммы 1,3,6'),dict(id='S3',text='print за циклом печатает однократно')],output=dict(initial_zero='S1',no_reset='S1',sum_one='S2',sum_three='S2',sum_six='S2',print_outside='S3',print_once='S3',counter_1=None,counter_2=None,counter_3=None))}
s=s.replace('export const assessmentSystem=', 'const demonstrations='+json.dumps(examples,ensure_ascii=False,separators=(',',':'))+';\nexport const assessmentSystem=')
s=s.replace('return {trusted_code:task.code,','return {format_demonstration:demonstrations[req.assessment.task_key],trusted_code:task.code,')
s=s.replace('Проверь факты в объяснении ученика,','format_demonstration — пример формата и логики, не часть оцениваемого ответа. Оценивается только student_answer на верхнем уровне; не копируй ссылки примера без проверки. Проверь факты в объяснении ученика,')
p.write_text(s,encoding='utf-8')
print('Added per-task extraction demonstrations, all authored from known development patterns; frozen32 unused')
