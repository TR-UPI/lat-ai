
from django.contrib import admin, messages
from django.utils.html import format_html

from .models import Course, Lesson, Exercise
from documents.models import Document
from documents.processing import process_document


class ExerciseInline(admin.StackedInline):
    model = Exercise
    extra = 0
    show_change_link = True

    fields = (
        "title",
        "description",
        "task_type",
        "order",
        "max_score",
        "is_published",
    )

    verbose_name = "Практическое задание"
    verbose_name_plural = "Практические задания"


class DocumentInline(admin.StackedInline):
    model = Document
    extra = 0
    show_change_link = True

    fields = (
        "title",
        "file",
        "status",
        "mime_type",
        "created_at",
    )

    readonly_fields = (
        "status",
        "mime_type",
        "created_at",
    )

    verbose_name = "Учебный материал"
    verbose_name_plural = "Прикреплённые учебные материалы"


class LessonInline(admin.StackedInline):
    model = Lesson
    extra = 0
    show_change_link = True

    fields = (
        "title",
        "order",
    )

    verbose_name = "Урок"
    verbose_name_plural = "Уроки курса"


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "subject",
        "lessons_total",
        "publication_status",
        "created_at",
    )

    list_filter = (
        "is_published",
        "subject",
    )

    search_fields = (
        "title",
        "description",
        "subject",
    )

    inlines = [LessonInline]

    fieldsets = (
        ("Информация о курсе", {
            "fields": (
                "title",
                "subject",
                "description",
            )
        }),
        ("Публикация курса", {
            "fields": ("is_published",)
        }),
    )

    @admin.display(description="Количество уроков")
    def lessons_total(self, obj):
        return obj.lessons.count()

    @admin.display(description="Статус")
    def publication_status(self, obj):
        if obj.is_published:
            return format_html(
                '<span style="color:green;font-weight:bold;">Опубликован</span>'
            )

        return format_html(
            '<span style="color:#d97706;font-weight:bold;">Черновик</span>'
        )


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "course",
        "order",
        "exercises_total",
        "documents_total",
    )

    list_filter = ("course",)

    search_fields = (
        "title",
        "content",
        "course__title",
    )

    inlines = [
        ExerciseInline,
        DocumentInline,
    ]

    fieldsets = (
        ("Основная информация", {
            "fields": (
                "course",
                "title",
                "order",
            )
        }),
        ("Теоретический материал", {
            "fields": ("content",),
            "description": "При необходимости здесь можно разместить текст теории."
        }),
    )

    @admin.display(description="Количество заданий")
    def exercises_total(self, obj):
        return obj.exercises.count()

    @admin.display(description="Количество материалов")
    def documents_total(self, obj):
        return obj.documents.count()

    def save_formset(self, request, form, formset, change):
        if formset.model is not Document:
            return super().save_formset(
                request, form, formset, change
            )

        instances = formset.save(commit=False)

        for obj in formset.deleted_objects:
            obj.delete()

        forms_by_instance = {
            id(inline_form.instance): inline_form
            for inline_form in formset.forms
            if inline_form.instance
        }

        documents_to_process = []

        for obj in instances:
            is_new = obj.pk is None

            if is_new:
                obj.owner = request.user

            obj.save()

            inline_form = forms_by_instance.get(id(obj))

            if is_new or (
                inline_form
                and "file" in inline_form.changed_data
            ):
                documents_to_process.append(obj)

        formset.save_m2m()

        for document in documents_to_process:
            success = process_document(document)

            if success:
                self.message_user(
                    request,
                    f"Материал «{document.title}» успешно обработан.",
                    level=messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    f"Ошибка обработки материала «{document.title}».",
                    level=messages.ERROR,
                )


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "lesson",
        "task_type",
        "max_score",
        "is_published",
    )

    list_filter = (
        "task_type",
        "is_published",
    )

    search_fields = (
        "title",
        "description",
        "lesson__title",
    )

    fieldsets = (
        ("Основная информация", {
            "fields": (
                "lesson",
                "title",
                "task_type",
                "order",
            )
        }),
        ("Условие задания", {
            "fields": ("description",)
        }),
        ("Оценивание", {
            "fields": (
                "max_score",
                "is_published",
            )
        }),
    )
