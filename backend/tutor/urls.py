from django.urls import path
from .views import TutorAskView, TutorContextView
urlpatterns = [path("ask/", TutorAskView.as_view(), name="tutor-ask"), path('context/', TutorContextView.as_view(), name='tutor-context')]
