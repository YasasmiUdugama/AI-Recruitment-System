from django.contrib import admin
from django.utils.html import format_html
from .models import (
    JobDescription, Candidate, Interview,
    InterviewResponse, InterviewEvaluation, EmailLog, HRReport
)


@admin.register(JobDescription)
class JobDescriptionAdmin(admin.ModelAdmin):
    list_display = ['title', 'department', 'status', 'created_at', 'created_by']
    list_filter = ['status', 'department', 'created_at']
    search_fields = ['title', 'description']
    date_hierarchy = 'created_at'


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ['full_name', 'email', 'status', 'similarity_score', 'applied_job', 'created_at']
    list_filter = ['status', 'applied_job', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'skills']
    list_editable = ['status']
    readonly_fields = ['similarity_score', 'cv_text', 'skills', 'education', 'experience']
    date_hierarchy = 'created_at'


@admin.register(Interview)
class InterviewAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'status', 'scheduled_date', 'completed_date', 'expires_at']
    list_filter = ['status', 'scheduled_date']
    search_fields = ['candidate__first_name', 'candidate__last_name']


@admin.register(InterviewResponse)
class InterviewResponseAdmin(admin.ModelAdmin):
    list_display = ['interview', 'question_index', 'keyword_score', 'confidence_score', 'has_video', 'created_at']
    list_filter = ['question_index', 'created_at']
    readonly_fields = ['video_preview', 'created_at']
    fields = [
        'interview', 'question_index', 'question_text', 'answer_text',
        'keyword_score', 'confidence_score', 'transcription',
        'audio_file', 'video_file', 'video_preview',
        'emotion_data', 'voice_analysis', 'created_at',
    ]

    def has_video(self, obj):
        return bool(obj.video_file)
    has_video.boolean = True
    has_video.short_description = 'Video'

    def video_preview(self, obj):
        if obj.video_file:
            return format_html(
                '<video src="{}" controls preload="metadata" style="max-width: 480px; border-radius: 8px;"></video>',
                obj.video_file.url
            )
        return "No video recorded for this answer."
    video_preview.short_description = 'Video Clip'


@admin.register(InterviewEvaluation)
class InterviewEvaluationAdmin(admin.ModelAdmin):
    list_display = ['interview', 'overall_score', 'recommendation', 'created_at']
    list_filter = ['recommendation', 'created_at']


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = ['candidate', 'subject', 'status', 'sent_at']
    list_filter = ['status', 'sent_at']
    search_fields = ['candidate__email', 'subject']


@admin.register(HRReport)
class HRReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'job', 'total_applicants', 'shortlisted_count', 'selected_count', 'generated_at']
    list_filter = ['generated_at']
    search_fields = ['title', 'job__title']
