from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from django.conf import settings
from django.conf.urls.static import static
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

def health(request):
    return JsonResponse({"status": "ok", "service": "LAT AI API"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/", health),
    path("api/v1/auth/register/", include("accounts.urls")),
    path("api/v1/auth/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/v1/auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("api/v1/accounts/", include("accounts.profile_urls")),
    path("api/v1/courses/", include("courses.urls")),
    path("api/v1/documents/", include("documents.urls")),
    path("api/v1/tutor/", include("tutor.urls")),
    path("api/v1/progress/", include("progress.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
