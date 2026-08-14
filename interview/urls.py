from django.urls import path
from . import views

urlpatterns = [
    # Original candidate-facing APIs
    path('questions/<str:job_type>/', views.interview_questions_api, name='interview_questions'),
    path('evaluate/', views.evaluate_answer_api, name='evaluate_answer'),
    path('save-response/', views.save_response_api, name='save_response'),
    path('upload-video/', views.upload_video_api, name='upload_video'),
    path('complete/', views.complete_interview_api, name='complete_interview'),
    path('info/', views.interview_info, name='interview_info'),

    # HR Partner API endpoints
    path('api/hr/dashboard/', views.hr_dashboard_api, name='hr_dashboard_api'),
    path('api/hr/interviews/', views.interview_list_api, name='interview_list_api'),
    path('api/hr/interviews/<int:interview_id>/', views.interview_detail_api, name='interview_detail_api'),
    path('api/hr/interviews/<int:interview_id>/report/', views.evaluation_report_api, name='evaluation_report_api'),
    path('api/hr/candidates/', views.candidate_list_api, name='candidate_list_api'),
    path('api/hr/candidates/<int:candidate_id>/', views.candidate_detail_api, name='candidate_detail_api'),
    
    # Debug
    path('debug/responses/<int:interview_id>/', views.debug_interview_responses, name='debug_responses'),
]