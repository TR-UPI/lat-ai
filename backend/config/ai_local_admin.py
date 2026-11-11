"""Authenticated local admin without document-processing dependencies."""
from django.contrib import admin
import accounts.admin  # Existing UserAdmin, including proper password handling.
import progress.admin  # Existing LessonProgress registration.
from courses.models import Course, Lesson, Exercise
from progress.models import ExerciseAttempt

for model in (Course, Lesson, Exercise):
    if not admin.site.is_registered(model):
        admin.site.register(model)

@admin.register(ExerciseAttempt)
class LocalAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'exercise', 'status', 'score', 'submitted_at')
    readonly_fields = ('user', 'exercise', 'answer', 'status', 'score', 'feedback', 'assessment', 'submitted_at')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
