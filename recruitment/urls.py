"""
AI Recruitment System - URL Configuration
"""
from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path('', views.dashboard, name='dashboard'),
    path('analytics/', views.analytics, name='analytics'),

    # Jobs
    path('jobs/', views.job_list, name='job_list'),
    path('jobs/create/', views.job_create, name='job_create'),
    path('jobs/<int:job_id>/', views.job_detail, name='job_detail'),
    path('jobs/<int:job_id>/edit/', views.job_edit, name='job_edit'),
    path('jobs/<int:job_id>/delete/', views.job_delete, name='job_delete'),
    path('jobs/<int:job_id>/rank/', views.rank_candidates, name='rank_candidates'),
    path('jobs/<int:job_id>/shortlist/', views.shortlist_candidates, name='shortlist_candidates'),
    path('jobs/<int:job_id>/send-invitations/', views.send_invitations, name='send_invitations'),
    path('jobs/<int:job_id>/send-results/', views.send_results, name='send_results'),
    path('jobs/<int:job_id>/generate-report/', views.generate_report, name='generate_report'),

    # Candidates
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('candidates/upload/', views.candidate_upload, name='candidate_upload'),
    path('candidates/<int:candidate_id>/', views.candidate_detail, name='candidate_detail'),
    path('candidates/<int:candidate_id>/update-status/', views.api_update_status, name='api_update_status'),

    # Reports
    path('reports/', views.report_list, name='report_list'),
    path('reports/<int:report_id>/', views.report_detail, name='report_detail'),

    # Interview
    path('interview/<uuid:token>/', views.interview_portal, name='interview_portal'),

    # Parser API & Info
    path('parser/parse/', views.parse_cv_api, name='parse_cv_api'),
    path('parser/info/', views.parser_info, name='parser_info'),
]
