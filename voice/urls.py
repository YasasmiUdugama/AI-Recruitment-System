from django.urls import path
from . import views

urlpatterns = [
    path('transcribe/', views.transcribe_api, name='voice_transcribe'),
    path('analyze/', views.analyze_voice_api, name='voice_analyze'),
    path('full-analysis/', views.full_analysis_api, name='voice_full_analysis'),
    path('info/', views.voice_info, name='voice_info'),
]
