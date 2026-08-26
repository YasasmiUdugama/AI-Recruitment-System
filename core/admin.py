# Save as: core/admin.py  (replaces existing file)
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

    list_display = ['candidate', 'status', 'has_recording', 'scheduled_date', 'completed_date', 'expires_at']
    list_filter = ['status', 'scheduled_date']
    search_fields = ['candidate__first_name', 'candidate__last_name']
    readonly_fields = ['recording_preview', 'access_token', 'questions_json']
    fields = [
        'candidate', 'status', 'scheduled_date', 'completed_date', 'expires_at',
        'access_token', 'questions_json',
        'full_recording', 'recording_preview',
    ]

    def has_recording(self, obj):
        return bool(obj.full_recording)
    has_recording.boolean = True
    has_recording.short_description = 'Recording'

    def recording_preview(self, obj):
        if obj.full_recording:
            return format_html(
                '<video src="{}" controls preload="metadata" style="max-width: 640px; border-radius: 8px;"></video>',
                obj.full_recording.url
            )
        return "No recording saved yet — it's only written once the candidate submits the full interview."
    recording_preview.short_description = 'Full Interview Recording'


@admin.register(InterviewResponse)
class InterviewResponseAdmin(admin.ModelAdmin):

    list_display = ['interview', 'question_index', 'keyword_score', 'confidence_score', 'has_audio', 'created_at']
    list_filter = ['question_index', 'created_at']
    readonly_fields = ['audio_preview', 'created_at']
    fields = [
        'interview', 'question_index', 'question_text', 'answer_text',
        'keyword_score', 'confidence_score', 'transcription',
        'audio_file', 'audio_preview',
        'voice_analysis', 'created_at',
    ]

    def has_audio(self, obj):
        return bool(obj.audio_file)
    has_audio.boolean = True
    has_audio.short_description = 'Audio'

    def audio_preview(self, obj):
        if obj.audio_file:
            return format_html(
                '<audio src="{}" controls preload="metadata"></audio>',
                obj.audio_file.url
            )
        return "No audio recorded for this answer."
    audio_preview.short_description = 'Answer Audio'


@admin.register(InterviewEvaluation)
class InterviewEvaluationAdmin(admin.ModelAdmin):
    list_display = ['interview', 'overall_score', 'recommendation', 'proctoring_status', 'created_at']
    list_filter = ['recommendation', 'created_at']
    readonly_fields = ['created_at']

    def proctoring_status(self, obj):
        emotion_analysis = obj.emotion_analysis if isinstance(obj.emotion_analysis, dict) else {}
        flags = emotion_analysis.get('proctoring', {}).get('flags', [])
        if not flags:
            return format_html('<span style="color: #16a34a;">Clean</span>')
        return format_html('<span style="color: #dc2626;">{}</span>', ', '.join(flags))
    proctoring_status.short_description = 'Proctoring'


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