
from django.urls import path

from .views import (
    DocumentListCreateView,
    DocumentDeleteView,
    DocumentSearchView,
)

urlpatterns = [
    path(
        "",
        DocumentListCreateView.as_view(),
        name="document-list-create"
    ),

    path(
        "search/",
        DocumentSearchView.as_view(),
        name="document-search"
    ),

    path(
        "<int:pk>/",
        DocumentDeleteView.as_view(),
        name="document-delete"
    ),
]
