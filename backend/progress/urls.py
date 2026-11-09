
from django.urls import path

from .views import (
    ProgressListView,
    StudentDashboardView,
    ExerciseAttemptListCreateView,
    ExerciseAttemptReviewView,
)

urlpatterns = [
    path(
        "",
        ProgressListView.as_view(),
        name="progress",
    ),
    path(
        "dashboard/",
        StudentDashboardView.as_view(),
        name="dashboard",
    ),
    path(
        "attempts/",
        ExerciseAttemptListCreateView.as_view(),
        name="exercise-attempts",
    ),
    path(
        "attempts/<int:pk>/review/",
        ExerciseAttemptReviewView.as_view(),
        name="exercise-attempt-review",
    ),
]
