from django.urls import path
from . import views

urlpatterns = [
    path('rank-job/<int:job_id>/', views.rank_job_candidates, name='rank_job_candidates'),
    path('info/', views.ranking_info, name='ranking_info'),
]
