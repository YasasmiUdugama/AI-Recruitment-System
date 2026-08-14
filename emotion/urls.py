from django.urls import path
from . import views

urlpatterns = [
    path('analyze-image/', views.analyze_image_api, name='analyze_image'),
    path('analyze-video/', views.analyze_video_api, name='analyze_video'),
    path('info/', views.emotion_info, name='emotion_info'),
]
