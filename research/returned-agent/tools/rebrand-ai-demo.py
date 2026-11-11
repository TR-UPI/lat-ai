"""One-off LAT AI label migration for the isolated demo; run with its services stopped."""
import json
import os
from pathlib import Path
import shutil
import sqlite3
import sys
from datetime import datetime

root=Path(__file__).resolve().parents[1]
source=root/'lat-ai';runtime=source/'.runtime/i02'
seed=json.loads((runtime/'seed.json').read_text(encoding='utf-8'))
assert seed['profile']=='isolated-ai-review'
os.environ['DJANGO_SETTINGS_MODULE']='config.ai_local'
os.environ['LAD_AI_RUNTIME']=str(runtime)
sys.path.insert(0,str(source/'backend'))
import django
django.setup()
from courses.models import Course,Lesson,Exercise
from tutor.context import content_digest
from django.db import transaction

course_ids={c['course_id'] for c in seed['contexts']}
courses=list(Course.objects.filter(id__in=course_ids))
assert len(courses)==len(course_ids)
changes=[c for c in courses if c.title=='Python · ручная проверка LAD AI']
if not changes:
    print('LAT AI demo labels already current; nothing changed.')
    sys.exit(0)
mapping_path=runtime/'mapping.json'
mapping=json.loads(mapping_path.read_text(encoding='utf-8'))
for key,value in mapping['contexts'].items():
    course_id,lesson_id,exercise_id=map(int,key.split(':'))
    course=Course.objects.get(pk=course_id);lesson=Lesson.objects.get(pk=lesson_id)
    exercise=Exercise.objects.get(pk=exercise_id) if exercise_id else None
    assert value['digest']==content_digest(course,lesson,exercise),'Existing mapping mismatch; refusing migration'
backup=runtime/'backups'/('lat-brand-'+datetime.now().strftime('%Y%m%d-%H%M%S'))
backup.mkdir(parents=True,exist_ok=False)
with sqlite3.connect(runtime/'django.sqlite3') as db,sqlite3.connect(backup/'django.sqlite3') as copy:
    db.backup(copy)
shutil.copy2(mapping_path,backup/'mapping.json')
with transaction.atomic():
    for course in changes:
        course.title='Python · ручная проверка LAT AI'
        course.save(update_fields=['title'])
    for key,value in mapping['contexts'].items():
        course_id,lesson_id,exercise_id=map(int,key.split(':'))
        course=Course.objects.get(pk=course_id);lesson=Lesson.objects.get(pk=lesson_id)
        exercise=Exercise.objects.get(pk=exercise_id) if exercise_id else None
        value['digest']=content_digest(course,lesson,exercise)
    temp=mapping_path.with_suffix('.brand-pending.json')
    temp.write_text(json.dumps(mapping,ensure_ascii=False,indent=2),encoding='utf-8')
os.replace(temp,mapping_path)
print(json.dumps({'renamed_course_ids':[c.id for c in changes],'mapping_entries':len(mapping['contexts']),'private_backup':str(backup),'attempt_history_preserved':True}))
