from django.urls import path, include
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from django.contrib import admin
from django.apps import apps
from django.views.static import serve
from pathlib import Path
from . import ai_local_admin  # Register only the supported local sections.

def admin_static(request, path):
    # Only Django's own admin assets; never expose runtime, source or media.
    root = Path(apps.get_app_config('admin').path) / 'static' / 'admin'
    return serve(request, path, document_root=root)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('static/admin/<path:path>', admin_static),
    path('api/v1/auth/register/', include('accounts.urls')),
    path('api/v1/auth/token/', TokenObtainPairView.as_view()),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view()),
    path('api/v1/accounts/', include('accounts.profile_urls')),
    path('api/v1/courses/', include('courses.urls')),
    path('api/v1/progress/', include('progress.urls')),
    path('api/v1/tutor/', include('tutor.urls')),
    path('api/v1/documents/', include('documents.study_urls')),
]
