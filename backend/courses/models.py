
from django.db import models


class Course(models.Model):
    title = models.CharField(
        "Название курса",
        max_length=200
    )
    description = models.TextField(
        "Описание курса",
        blank=True
    )
    subject = models.CharField(
        "Предмет",
        max_length=100,
        blank=True
    )
    is_published = models.BooleanField(
        "Опубликован",
        default=False
    )
    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Курс"
        verbose_name_plural = "Курсы"

    def __str__(self):
        return self.title


class Lesson(models.Model):
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name="lessons",
        verbose_name="Курс"
    )
    title = models.CharField(
        "Название урока",
        max_length=200
    )
    content = models.TextField(
        "Теоретический материал",
        blank=True
    )
    order = models.PositiveIntegerField(
        "Порядок урока",
        default=0
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Урок"
        verbose_name_plural = "Уроки"

    def __str__(self):
        return self.title


class Exercise(models.Model):
    lesson = models.ForeignKey(
        Lesson,
        on_delete=models.CASCADE,
        related_name="exercises",
        verbose_name="Урок"
    )

    title = models.CharField(
        "Название задания",
        max_length=200
    )
    description = models.TextField(
        "Условие задания"
    )
    task_type = models.CharField(
        "Тип задания",
        max_length=50,
        default="text"
    )
    order = models.PositiveIntegerField(
        "Порядок задания",
        default=0
    )
    max_score = models.FloatField(
        "Максимальный балл",
        default=100
    )
    is_published = models.BooleanField(
        "Опубликовано",
        default=True
    )
    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True
    )

    class Meta:
        ordering = ["order", "id"]
        verbose_name = "Задание"
        verbose_name_plural = "Задания"

    def __str__(self):
        return self.title
