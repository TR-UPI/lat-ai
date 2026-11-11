from django.urls import path

from . import study_views as views

urlpatterns = [
    path('', views.DocumentListUpload.as_view(), name='study-document-list'),
    path('packs/', views.StudyPackList.as_view(), name='study-pack-list'),
    path('packs/<int:pk>/', views.StudyPackDetail.as_view(), name='study-pack-detail'),
    path('packs/<int:pk>/hints/', views.StudyHint.as_view(), name='study-hint'),
    path('packs/<int:pk>/attempts/', views.StudyAttemptSubmit.as_view(), name='study-attempt'),
    path('<int:pk>/', views.DocumentDetail.as_view(), name='study-document-detail'),
    path('<int:pk>/download/', views.DocumentDownload.as_view(), name='study-document-download'),
    path('<int:pk>/generate/', views.GenerateStudyPack.as_view(), name='study-generate'),
]
