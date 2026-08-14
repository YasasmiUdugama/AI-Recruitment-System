"""
AI Recruitment System - Models
"""
import uuid
from django.db import models


class Job(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('closed', 'Closed'),
        ('draft', 'Draft'),
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    required_skills = models.TextField(blank=True, help_text="Comma-separated skills")
    experience_required = models.CharField(max_length=100, blank=True)
    education_required = models.CharField(max_length=100, blank=True)
    department = models.CharField(max_length=100, blank=True)
    location = models.CharField(max_length=100, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Candidate(models.Model):
    STATUS_CHOICES = [
        ('new', 'New'),
        ('screening', 'Screening'),
        ('shortlisted', 'Shortlisted'),
        ('interview_scheduled', 'Interview Scheduled'),
        ('interview_completed', 'Interview Completed'),
        ('selected', 'Selected'),
        ('rejected', 'Rejected'),
    ]

    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=50, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='new')
    similarity_score = models.FloatField(default=0.0)
    applied_job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='candidates')
    skills = models.TextField(blank=True)
    education = models.TextField(blank=True)
    experience = models.TextField(blank=True)
    cv_file = models.FileField(upload_to='cvs/%Y/%m/%d/')
    extracted_text = models.TextField(blank=True, help_text="Raw text extracted from CV")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-similarity_score', '-created_at']

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name or "Unknown Candidate"

    def __str__(self):
        return self.full_name


class Interview(models.Model):
    candidate = models.OneToOneField(
        Candidate, 
        on_delete=models.CASCADE, 
        related_name='interview'
    )
    access_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    evaluation = models.JSONField(blank=True, null=True)
    scheduled_at = models.DateTimeField(blank=True, null=True)
    completed_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Interview for {self.candidate.full_name}"


class Report(models.Model):
    title = models.CharField(max_length=200)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='reports')
    generated_at = models.DateTimeField(auto_now_add=True)
    total_applicants = models.IntegerField(default=0)
    shortlisted_count = models.IntegerField(default=0)
    interviewed_count = models.IntegerField(default=0)
    selected_count = models.IntegerField(default=0)
    rejected_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-generated_at']

    def __str__(self):
        return self.title
