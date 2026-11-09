
from django.conf import settings
from django.db import models
from courses.models import Lesson, Exercise


class LessonProgress(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="lesson_progress",
        verbose_name="Ученик"
    )

    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="progress_records",
        verbose_name="Урок"
    )

    completed = models.BooleanField(
        "Урок завершён",
        default=False
    )

    score = models.FloatField(
        "Средний балл",
        null=True,
        blank=True
    )

    updated_at = models.DateTimeField(
        "Дата обновления",
        auto_now=True
    )

    class Meta:
        unique_together = ("user", "lesson")
        verbose_name = "Прогресс урока"
        verbose_name_plural = "Прогресс учеников"
        ordering = ["-updated_at"]

    def __str__(self):
        return f"{self.user} — {self.lesson}"


class ExerciseAttempt(models.Model):

    STATUS_CHOICES = [
        ("submitted", "Отправлено"),
        ("checked", "Проверено"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="exercise_attempts",
        verbose_name="Ученик"
    )

    exercise = models.ForeignKey(
        Exercise,
        on_delete=models.CASCADE,
        related_name="attempts",
        verbose_name="Задание"
    )

    answer = models.TextField(
        "Ответ ученика"
    )

    score = models.FloatField(
        "Полученный балл",
        null=True,
        blank=True
    )

    feedback = models.TextField(
        "Комментарий к ответу",
        blank=True
    )

    status = models.CharField(
        "Статус проверки",
        max_length=20,
        choices=STATUS_CHOICES,
        default="submitted"
    )

    submitted_at = models.DateTimeField(
        "Дата отправки",
        auto_now_add=True
    )

    class Meta:
        ordering = ["-submitted_at"]
        verbose_name = "Попытка выполнения задания"
        verbose_name_plural = "Попытки выполнения заданий"

    def __str__(self):
        return f"{self.user} — {self.exercise}"
