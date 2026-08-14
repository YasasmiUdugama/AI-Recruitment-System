from django.urls import path
from . import views

urlpatterns = [
    path('api/<int:job_id>/', views.shortlist_api, name='shortlist_api'),
    path('info/', views.shortlist_info, name='shortlist_info'),
]
