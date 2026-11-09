
from rest_framework import viewsets, permissions
from rest_framework import generics
from documents.models import Document
from documents.serializers import DocumentSerializer

from .models import Course, Lesson, Exercise

from .serializers import (
    CourseSerializer,
    LessonSerializer,
    ExerciseSerializer,
)


class CourseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CourseSerializer
    permission_classes = [permissions.IsAuthenticated]

    queryset = Course.objects.filter(is_published=True)


class LessonViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LessonSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Lesson.objects.filter(
            course_id=self.kwargs["course_pk"],
            course__is_published=True
        )


class ExerciseViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = ExerciseSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Exercise.objects.filter(
            lesson_id=self.kwargs["lesson_pk"],
            lesson__course_id=self.kwargs["course_pk"],
            lesson__course__is_published=True,
            is_published=True
        )
class LessonDocumentsView(generics.ListAPIView):
    serializer_class = DocumentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Document.objects.filter(
            lesson_id=self.kwargs["lesson_pk"],
            lesson__course_id=self.kwargs["course_pk"],
            lesson__course__is_published=True,
            status="ready"
        ).order_by("-created_at")