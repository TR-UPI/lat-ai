
from django.conf import settings
from django.db import models
from pgvector.django import VectorField


def user_document_path(instance, filename):
    return f"users/{instance.owner_id}/documents/{filename}"


class Document(models.Model):
    STATUS_CHOICES = [
        ("uploaded", "Загружен"),
        ("processing", "Обрабатывается"),
        ("ready", "Готов"),
        ("failed", "Ошибка"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Владелец"
    )

    lesson = models.ForeignKey(
        "courses.Lesson",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="documents",
        verbose_name="Урок"
    )

    title = models.CharField(
        "Название материала",
        max_length=255
    )

    file = models.FileField(
        "Файл",
        upload_to=user_document_path
    )

    mime_type = models.CharField(
        "Тип файла",
        max_length=120,
        blank=True
    )

    status = models.CharField(
        "Статус обработки",
        max_length=20,
        choices=STATUS_CHOICES,
        default="uploaded"
    )

    extracted_text = models.TextField(
        "Извлечённый текст",
        blank=True
    )

    created_at = models.DateTimeField(
        "Дата загрузки",
        auto_now_add=True
    )

    class Meta:
        verbose_name = "Учебный материал"
        verbose_name_plural = "Учебные материалы"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class DocumentChunk(models.Model):
    embedding = VectorField(
        dimensions=384,
        null=True,
        blank=True
    )

    document = models.ForeignKey(
        Document,
        on_delete=models.CASCADE,
        related_name="chunks",
        verbose_name="Документ"
    )

    content = models.TextField(
        "Содержимое фрагмента"
    )

    chunk_index = models.PositiveIntegerField(
        "Номер фрагмента"
    )

    created_at = models.DateTimeField(
        "Дата создания",
        auto_now_add=True
    )

    class Meta:
        ordering = ["chunk_index"]
        unique_together = ("document", "chunk_index")
        verbose_name = "Фрагмент документа"
        verbose_name_plural = "Фрагменты документов"

    def __str__(self):
        return f"{self.document.title} — фрагмент {self.chunk_index}"
