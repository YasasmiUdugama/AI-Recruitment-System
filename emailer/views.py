from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import logging

from core.models import Candidate, EmailLog
from .email_sender import (
    send_interview_invitation, send_rejection_email,
    send_selection_email, send_interview_reminder
)

logger = logging.getLogger('ai_recruitment')


def send_invitation_api(request, candidate_id):
    if request.method == 'POST':
        candidate = get_object_or_404(Candidate, id=candidate_id)

        if not hasattr(candidate, 'interview'):
            return JsonResponse({'success': False, 'error': 'No interview scheduled for this candidate'})

        success, error = send_interview_invitation(
            candidate.email,
            candidate.full_name,
            candidate.interview.access_token
        )

        EmailLog.objects.create(
            candidate=candidate,
            subject='Interview Invitation',
            body=f'Interview invitation sent to {candidate.email}',
            status='sent' if success else 'failed',
            error_message=error if not success else ''
        )

        return JsonResponse({
            'success': success,
            'message': 'Invitation sent' if success else f'Failed: {error}'
        })

    return JsonResponse({'success': False, 'error': 'POST required'})


def send_rejection_api(request, candidate_id):
    """API to send rejection email"""
    if request.method == 'POST':
        candidate = get_object_or_404(Candidate, id=candidate_id)

        success, error = send_rejection_email(
            candidate.email,
            candidate.full_name
        )

        EmailLog.objects.create(
            candidate=candidate,
            subject='Application Status Update',
            body=f'Rejection email sent to {candidate.email}',
            status='sent' if success else 'failed',
            error_message=error if not success else ''
        )

        return JsonResponse({
            'success': success,
            'message': 'Rejection email sent' if success else f'Failed: {error}'
        })

    return JsonResponse({'success': False, 'error': 'POST required'})


def send_selection_api(request, candidate_id):
    if request.method == 'POST':
        candidate = get_object_or_404(Candidate, id=candidate_id)

        success, error = send_selection_email(
            candidate.email,
            candidate.full_name,
            candidate.applied_job.title
        )

        EmailLog.objects.create(
            candidate=candidate,
            subject='Congratulations - Job Offer',
            body=f'Selection email sent to {candidate.email}',
            status='sent' if success else 'failed',
            error_message=error if not success else ''
        )

        return JsonResponse({
            'success': success,
            'message': 'Selection email sent' if success else f'Failed: {error}'
        })

    return JsonResponse({'success': False, 'error': 'POST required'})


def email_logs(request):
    logs = EmailLog.objects.all().order_by('-sent_at')
    return render(request, 'emailer/email_logs.html', {'logs': logs})


def email_info(request):
    """Info page about email system"""
    return render(request, 'emailer/email_info.html')
