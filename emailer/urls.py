from django.urls import path
from . import views

urlpatterns = [
    path('send-invitation/<int:candidate_id>/', views.send_invitation_api, name='send_invitation'),
    path('send-rejection/<int:candidate_id>/', views.send_rejection_api, name='send_rejection'),
    path('send-selection/<int:candidate_id>/', views.send_selection_api, name='send_selection'),
    path('logs/', views.email_logs, name='email_logs'),
    path('info/', views.email_info, name='email_info'),
]
