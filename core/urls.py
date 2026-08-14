"""
Core App - URL Configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('analytics/', views.analytics_dashboard, name='analytics'),

    # Job Management
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/create/', views.job_create, name='job_create'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/edit/', views.job_edit, name='job_edit'),
    path('jobs/<int:job_id>/delete/', views.job_delete, name='job_delete'),

    # Candidate Management
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('candidates/upload/', views.candidate_upload, name='candidate_upload'),
    path('candidates/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    path('candidates/<int:candidate_id>/edit/', views.candidate_edit, name='candidate_edit'),
        path('candidates/<int:candidate_id>/delete/', views.candidate_delete, name='candidate_delete'),

    # Ranking & Shortlisting
    path('jobs/<int:job_id>/rank/', views.rank_candidates, name='rank_candidates'),
    path('jobs/<int:job_id>/shortlist/', views.shortlist_top_candidates, name='shortlist_candidates'),

    # Interview
    path('interview/<uuid:token>/', views.interview_portal, name='interview_portal'),

    # Email & Notifications
    path('jobs/<int:job_id>/send-invitations/', views.send_interview_invitations, name='send_invitations'),
    path('jobs/<int:job_id>/send-results/', views.send_results, name='send_results'),

    # Reports
    path('jobs/<int:job_id>/generate-report/', views.generate_report, name='generate_report'),
    path('reports/', views.report_list, name='report_list'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),

    # API Endpoints
    path('api/jobs/<int:job_id>/stats/', views.api_job_stats, name='api_job_stats'),
    path('api/candidates/<int:candidate_id>/update-status/', views.api_update_candidate_status, name='api_update_status'),
]
