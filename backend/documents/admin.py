
import os

from django import forms
from django.contrib import admin, messages

from .models import Document, DocumentChunk
from .processing import process_document


class DocumentAdminForm(forms.ModelForm):

    class Meta:
        model = Document
        fields = "__all__"

    def clean_file(self):
        file = self.cleaned_data.get("file")

        if not file:
            return file

        allowed_extensions = {
            ".pdf", ".docx", ".pptx", ".txt"
        }

        extension = os.path.splitext(file.name)[1].lower()

        if extension not in allowed_extensions:
            raise forms.ValidationError(
                "Разрешены только PDF, DOCX, PPTX и TXT."
            )

        if file.size > 20 * 1024 * 1024:
            raise forms.ValidationError(
                "Максимальный размер файла — 20 МБ."
            )

        return file


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):

    form = DocumentAdminForm

    list_display = (
        "title",
        "lesson",
        "owner",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "lesson__course",
        "created_at",
    )

    search_fields = (
        "title",
        "owner__email",
        "lesson__title",
        "lesson__course__title",
    )

    list_select_related = (
        "owner",
        "lesson",
        "lesson__course",
    )

    readonly_fields = (
        "owner",
        "mime_type",
        "status",
        "extracted_text",
        "created_at",
    )

    fieldsets = (
        ("Учебный материал", {
            "fields": (
                "title",
                "file",
            )
        }),
        ("Привязка к обучению", {
            "fields": (
                "lesson",
            )
        }),
        ("Обработка документа", {
            "fields": (
                "status",
                "mime_type",
                "extracted_text",
            )
        }),
        ("Информация о загрузке", {
            "fields": (
                "owner",
                "created_at",
            )
        }),
    )

    def save_model(self, request, obj, form, change):
        if not change:
            obj.owner = request.user

        super().save_model(request, obj, form, change)

        file_changed = "file" in form.changed_data

        if not change or file_changed:
            success = process_document(obj)

            if success:
                self.message_user(
                    request,
                    "Материал успешно загружен и обработан.",
                    level=messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    "Файл загружен, но при обработке произошла ошибка. "
                    "Проверьте статус документа.",
                    level=messages.ERROR,
                )


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):

    list_display = (
        "document",
        "chunk_index",
        "created_at",
    )

    search_fields = (
        "document__title",
        "content",
    )

    list_select_related = ("document",)

    readonly_fields = (
        "document",
        "content",
        "chunk_index",
        "embedding",
        "created_at",
    )
