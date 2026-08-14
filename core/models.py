from django.db import models
from django.contrib.auth.models import User
import uuid
import os


def cv_file_path(instance, filename):
    """Generate file path for CV uploads"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('cvs', filename)


def recording_file_path(instance, filename):
    """Generate file path for voice recordings"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('recordings', filename)


def interview_video_path(instance, filename):
    """Generate file path for interview video clips"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('interview_videos', filename)


class JobDescription(models.Model):
    """Job descriptions posted by HR"""
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('draft', 'Draft'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    required_skills = models.TextField(help_text="Comma-separated required skills")
    experience_required = models.CharField(max_length=100)
    education_required = models.CharField(max_length=200)
    department = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=200, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-created_at']


class Candidate(models.Model):
    """Candidates who uploaded their CVs"""
    STATUS_CHOICES = [
        ('new', 'New'),
        ('screening', 'Under Screening'),
        ('shortlisted', 'Shortlisted'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('interview_completed', 'Interview Completed'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    cv_file = models.FileField(upload_to=cv_file_path)
    cv_text = models.TextField(blank=True, help_text="Extracted text from CV")
    skills = models.TextField(blank=True, help_text="Extracted skills from CV")
    education = models.TextField(blank=True, help_text="Extracted education from CV")
    experience = models.TextField(blank=True, help_text="Extracted experience from CV")
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new')
    similarity_score = models.FloatField(default=0.0)
    applied_job = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name='candidates')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    class Meta:
        ordering = ['-similarity_score', '-created_at']


class Interview(models.Model):
    """Interview sessions for shortlisted candidates"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('expired', 'Expired'),
    ]

    candidate = models.OneToOneField(Candidate, on_delete=models.CASCADE, related_name='interview')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    scheduled_date = models.DateTimeField(null=True, blank=True)
    completed_date = models.DateTimeField(null=True, blank=True)
    access_token = models.UUIDField(default=uuid.uuid4, unique=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Interview - {self.candidate.full_name}"


class InterviewResponse(models.Model):
    """Individual question responses during interview"""
    interview = models.ForeignKey(Interview, on_delete=models.CASCADE, related_name='responses')
    question_index = models.IntegerField()
    question_text = models.TextField()
    answer_text = models.TextField(blank=True)
    audio_file = models.FileField(upload_to=recording_file_path, blank=True, null=True)
    video_file = models.FileField(upload_to=interview_video_path, blank=True, null=True, help_text="Recorded webcam video clip for this answer")
    transcription = models.TextField(blank=True)
    keyword_score = models.FloatField(default=0.0)
    confidence_score = models.FloatField(default=0.0)
    emotion_data = models.JSONField(default=dict, blank=True)
    voice_analysis = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Q{self.question_index} - {self.interview.candidate.full_name}"

    class Meta:
        ordering = ['question_index']


class InterviewEvaluation(models.Model):
    """Final evaluation after interview completion"""
    interview = models.OneToOneField(Interview, on_delete=models.CASCADE, related_name='evaluation')
    overall_score = models.FloatField(default=0.0)
    keyword_score_avg = models.FloatField(default=0.0)
    confidence_score_avg = models.FloatField(default=0.0)
    emotion_analysis = models.JSONField(default=dict, blank=True)
    voice_analysis_summary = models.JSONField(default=dict, blank=True)
    recommendation = models.CharField(
        max_length=20,
        choices=[('recommended', 'Recommended'), ('not_recommended', 'Not Recommended')],
        default='not_recommended'
    )
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Evaluation - {self.interview.candidate.full_name}"


class EmailLog(models.Model):
    """Log of all emails sent by the system"""
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='emails')
    subject = models.CharField(max_length=300)
    body = models.TextField()
    status = models.CharField(max_length=20, choices=[('sent', 'Sent'), ('failed', 'Failed')])
    error_message = models.TextField(blank=True)
    sent_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.subject} - {self.candidate.email}"

    class Meta:
        ordering = ['-sent_at']


class HRReport(models.Model):
    """Generated reports for HR team"""
    job = models.ForeignKey(JobDescription, on_delete=models.CASCADE, related_name='reports')
    title = models.CharField(max_length=200)
    total_applicants = models.IntegerField(default=0)
    shortlisted_count = models.IntegerField(default=0)
    interviewed_count = models.IntegerField(default=0)
    selected_count = models.IntegerField(default=0)
    rejected_count = models.IntegerField(default=0)
    report_data = models.JSONField(default=dict, blank=True)
    generated_at = models.DateTimeField(auto_now_add=True)
    generated_by = models.ForeignKey(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.title

    class Meta:
        ordering = ['-generated_at']
