"""Local formative assessment and validation of its stored evidence."""
import json
import math
import uuid
from pathlib import Path
from django.db import transaction
from django.utils import timezone
from courses.models import Exercise
from tutor.transport import call_assessment
from .models import ExerciseAttempt

RUBRICS = json.loads((Path(__file__).resolve().parents[2] / 'integration/ai/core/data/assessment-rubrics.json').read_text(encoding='utf-8'))

def valid_evidence(checks, evidence, answer):
    return (
        isinstance(checks, list) and len(checks) == 3 and all(type(check) is bool for check in checks)
        and isinstance(evidence, list) and len(evidence) == 3
        and all(
            isinstance(quote, str) and len(quote) <= 4000
            and (bool(quote.strip()) and quote in answer if passed else quote == '')
            for passed, quote in zip(checks, evidence)
        )
    )


def automatic_hint_result(attempt, task_key, digest, max_score):
    """Return the pass flag only for a current, internally consistent server assessment."""
    assessment = attempt.assessment
    if (
        not isinstance(assessment, dict)
        or assessment.get('source') != 'local_model'
        or assessment.get('reason') != 'ok'
        or assessment.get('rubric_version') != RUBRICS['version']
        or assessment.get('task_key') != task_key
        or task_key not in RUBRICS['tasks']
        or assessment.get('content_digest') != digest
        or not math.isfinite(max_score) or not 0 < max_score <= 100000
    ):
        return None
    request_id = assessment.get('request_id')
    try:
        if not isinstance(request_id, str) or str(uuid.UUID(request_id)) != request_id:
            return None
    except ValueError:
        return None
    checks = assessment.get('checks')
    if not valid_evidence(checks, assessment.get('evidence'), attempt.answer):
        return None
    if attempt.score != round(max_score * sum(checks) / 3, 2):
        return None
    return all(checks)


def assess_attempt(attempt, update_progress):
    from tutor.context import content_digest, mapping_for
    exercise=attempt.exercise
    lesson=exercise.lesson
    course=lesson.course
    request_id=str(uuid.uuid4())
    metadata=dict(source='local_model', request_id=request_id, rubric_version=RUBRICS['version'])
    digest=content_digest(course,lesson,exercise)
    mapping=mapping_for(course,lesson,exercise)
    task=RUBRICS['tasks'].get((mapping or {}).get('task_key'))
    checks=None
    reason='unsupported_task'
    # Persist identity before dispatch. A failed/unknown call is never retried here.
    attempt.assessment=metadata
    with transaction.atomic():
        attempt.save(update_fields=['assessment'])
        update_progress(attempt.user,lesson)
    if task and math.isfinite(exercise.max_score) and 0 < exercise.max_score <= 100000:
        metadata.update(task_key=mapping['task_key'],content_digest=digest)
        try:
            status,result=call_assessment(dict(request_id=request_id,answer=attempt.answer),dict(actor_id=attempt.user_id,attempt_id=attempt.pk,digest=digest,task_key=mapping['task_key']))
            if status!=200 or result.get('contract_version')!='1.0' or result.get('request_id')!=request_id or result.get('outcome')!='assessed' or result.get('rubric_version')!=RUBRICS['version']:
                raise ValueError('assessment unavailable')
            checks=result.get('checks')
            evidence=result.get('evidence')
            if not valid_evidence(checks, evidence, attempt.answer):
                raise ValueError('invalid assessment evidence')
            metadata['evidence']=evidence
            reason='ok'
        except Exception:
            checks=None;reason='unavailable'
    with transaction.atomic():
        # Acquire the SQLite writer before reading current content/progress.
        # A concurrent human review cannot be overwritten by a late model result.
        owned=ExerciseAttempt.objects.filter(pk=attempt.pk,status='submitted').update(status='submitted')
        if owned:
            current=Exercise.objects.select_related('lesson__course').get(pk=exercise.pk)
            current_mapping=mapping_for(current.lesson.course,current.lesson,current)
            if not current.is_published or not current.lesson.course.is_published or content_digest(current.lesson.course,current.lesson,current)!=digest or current_mapping!=mapping:
                checks=None;reason='content_changed'
            metadata.update(reason=reason,finished_at=timezone.now().isoformat())
            if checks is not None:
                metadata['checks']=checks
                score=round(exercise.max_score*sum(checks)/3,2)
                feedback='Автоматическая оценка ИИ. '+ ' '.join(('Зачтено: ' if ok else 'Нужно уточнить: ')+criterion for ok,criterion in zip(checks,task['criteria']))
                values=dict(status='auto_checked',score=score,feedback=feedback,assessment=metadata)
            else:
                detail='Для этого задания нет актуальных критериев автопроверки.' if reason in ('unsupported_task','content_changed') else 'Локальная модель недоступна или не вернула корректную проверку.'
                values=dict(status='assessment_failed',score=None,feedback=detail+' Ответ сохранён, балл не выставлен. После устранения причины можно отправить новую попытку.',assessment=metadata)
            ExerciseAttempt.objects.filter(pk=attempt.pk).update(**values)
        update_progress(attempt.user,lesson)
    attempt.refresh_from_db()
