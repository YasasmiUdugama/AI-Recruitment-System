from django.contrib import admin
from .models import Job, Candidate, Interview, Report


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'status', 'created_at']
    list_filter = ['status', 'department']
    search_fields = ['title', 'description']


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'applied_job', 'similarity_score', 'status', 'created_at']
    list_filter = ['status', 'applied_job']
    search_fields = ['first_name', 'last_name', 'email', 'skills']
    ordering = ['-similarity_score']


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'access_token', 'created_at']
    search_fields = ['candidate__first_name', 'candidate__last_name']


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'job', 'generated_at', 'total_applicants', 'selected_count']
    list_filter = ['job']
