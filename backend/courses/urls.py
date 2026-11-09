
from django.urls import path, include
from .views import LessonDocumentsView
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter

from .views import (
    CourseViewSet,
    LessonViewSet,
    ExerciseViewSet,
)


router = DefaultRouter()
router.register("", CourseViewSet, basename="course")


nested = NestedDefaultRouter(
    router, "", lookup="course"
)

nested.register(
    "lessons",
    LessonViewSet,
    basename="course-lessons"
)


exercises = NestedDefaultRouter(
    nested, "lessons", lookup="lesson"
)

exercises.register(
    "exercises",
    ExerciseViewSet,
    basename="lesson-exercises"
)


urlpatterns = [
    path("", include(router.urls)),
    path("", include(nested.urls)),
    path("", include(exercises.urls)),
    path(
    "<int:course_pk>/lessons/<int:lesson_pk>/documents/",
    LessonDocumentsView.as_view(),
    name="lesson-documents"
),
]
