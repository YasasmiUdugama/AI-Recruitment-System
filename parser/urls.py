from django.urls import path
from . import views

urlpatterns = [
    path('parse/', views.parse_cv_api, name='parse_cv_api'),
    path('info/', views.parser_info, name='parser_info'),
]
