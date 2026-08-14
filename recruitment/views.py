"""
AI Recruitment System - Views
"""
import os
import uuid
import json
import logging

from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import Count, Q
from django.db.models.functions import TruncMonth
from django.views.decorators.csrf import csrf_exempt
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
from django.contrib.auth.decorators import login_required

from .models import Job, Candidate, Interview, Report
from .cv_parser import parse_cv
from .forms import JobForm, JobEditForm, BulkUploadForm
from .utils import (
    calculate_similarity_score,
    auto_shortlist_candidates,
    recalculate_job_scores,
)

logger = logging.getLogger('ai_recruitment')


# =============================================================================
# DASHBOARD & ANALYTICS
# =============================================================================

def dashboard(request):
    """Main dashboard view"""
    total_jobs = Job.objects.filter(status='active').count()
    total_candidates = Candidate.objects.count()
    shortlisted = Candidate.objects.filter(status='shortlisted').count()
    completed_interviews = Candidate.objects.filter(status='interview_completed').count()
    selected = Candidate.objects.filter(status='selected').count()

    recent_candidates = Candidate.objects.select_related('applied_job').order_by('-created_at')[:10]
    active_jobs = Job.objects.filter(status='active').order_by('-created_at')[:5]

    context = {
        'total_jobs': total_jobs,
        'total_candidates': total_candidates,
        'shortlisted': shortlisted,
        'completed_interviews': completed_interviews,
        'selected': selected,
        'recent_candidates': recent_candidates,
        'active_jobs': active_jobs,
    }
    return render(request, 'recruitment/dashboard.html', context)


def analytics(request):
    """Analytics dashboard with charts"""
    total_jobs = Job.objects.count()
    total_candidates = Candidate.objects.count()
    shortlisted = Candidate.objects.filter(status='shortlisted').count()
    selected = Candidate.objects.filter(status='selected').count()

    status_distribution = list(
        Candidate.objects.values('status')
        .annotate(count=Count('id'))
        .order_by('-count')
    )

    top_jobs = list(
        Job.objects.annotate(applicant_count=Count('candidates'))
        .order_by('-applicant_count')[:10]
        .values('title', 'applicant_count')
    )

    monthly_data = list(
        Candidate.objects.annotate(month=TruncMonth('created_at'))
        .values('month')
        .annotate(count=Count('id'))
        .order_by('month')
    )

    context = {
        'total_jobs': total_jobs,
        'total_candidates': total_candidates,
        'shortlisted': shortlisted,
        'selected': selected,
        'status_distribution': json.dumps(status_distribution),
        'top_jobs': json.dumps(top_jobs),
        'monthly_data': json.dumps(monthly_data, default=str),
    }
    return render(request, 'recruitment/analytics.html', context)


# =============================================================================
# JOB VIEWS
# =============================================================================

def job_list(request):
    """List all jobs"""
    jobs = Job.objects.prefetch_related('candidates').order_by('-created_at')
    return render(request, 'recruitment/job_list.html', {'jobs': jobs})


def job_detail(request, job_id):
    """Job detail with candidates"""
    job = get_object_or_404(Job, id=job_id)
    candidates = job.candidates.order_by('-similarity_score')
    return render(request, 'recruitment/job_detail.html', {
        'job': job,
        'candidates': candidates,
    })


def job_create(request):
    """Create new job"""
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.status = 'active'
            job.save()
            messages.success(request, 'Job created successfully!')
            return redirect('job_list')
    else:
        form = JobForm()
    return render(request, 'recruitment/job_create.html', {'form': form})


def job_edit(request, job_id):
    """Edit existing job"""
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        form = JobEditForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job updated successfully!')
            return redirect('job_detail', job_id=job.id)
    else:
        form = JobEditForm(instance=job)
    return render(request, 'recruitment/job_edit.html', {
        'form': form,
        'job': job,
    })


def job_delete(request, job_id):
    """Delete job with confirmation"""
    job = get_object_or_404(Job, id=job_id)
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job deleted successfully!')
        return redirect('job_list')
    return render(request, 'recruitment/job_confirm_delete.html', {'job': job})


# =============================================================================
# CANDIDATE VIEWS - BULK UPLOAD WITH AUTO-PARSING
# =============================================================================

def candidate_list(request):
    """List all candidates with filters"""
    candidates = Candidate.objects.select_related('applied_job').order_by('-created_at')
    jobs = Job.objects.filter(status='active')

    status_filter = request.GET.get('status')
    job_filter = request.GET.get('job')

    if status_filter:
        candidates = candidates.filter(status=status_filter)
    if job_filter:
        candidates = candidates.filter(applied_job_id=job_filter)

    return render(request, 'recruitment/candidate_list.html', {
        'candidates': candidates,
        'jobs': jobs,
        'status_filter': status_filter,
        'job_filter': job_filter,
    })


def candidate_detail(request, candidate_id):
    """Candidate detail view"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    interview = getattr(candidate, 'interview', None)
    return render(request, 'recruitment/candidate_detail.html', {
        'candidate': candidate,
        'interview': interview,
    })


def candidate_upload(request):
    """
    BULK CV UPLOAD VIEW
    -------------------
    1. User selects a Job and uploads multiple CV files
    2. Each CV is parsed automatically:
       - Name extraction (first_name, last_name)
       - Email extraction
       - Skills, Education, Experience extraction
    3. A Candidate is created for each CV automatically
    4. Similarity score is calculated against the Job description
    5. Top candidates are auto-shortlisted based on threshold
    """
    if request.method == 'POST':
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.cleaned_data['job_id']
            cv_files = request.FILES.getlist('cv_files')

            created_count = 0
            failed_files = []
            created_candidates = []

            for cv_file in cv_files:
                temp_path = None
                try:
                    # Save file temporarily for parsing
                    temp_path = default_storage.save(
                        f'temp/{uuid.uuid4().hex}_{cv_file.name}',
                        ContentFile(cv_file.read())
                    )
                    full_temp_path = os.path.join(
                        default_storage.location, temp_path
                    )

                    # Parse CV
                    result = parse_cv(full_temp_path)

                    if not result['success']:
                        failed_files.append((cv_file.name, result['error']))
                        if temp_path:
                            default_storage.delete(temp_path)
                        continue

                    # Extract name
                    first_name = result['first_name'] or 'Unknown'
                    last_name = result['last_name'] or 'Candidate'

                    # Create candidate
                    candidate = Candidate.objects.create(
                        first_name=first_name,
                        last_name=last_name,
                        email=result['email'] or f"unknown_{uuid.uuid4().hex[:8]}@placeholder.com",
                        applied_job=job,
                        skills=result['skills'],
                        education=result['education'],
                        experience=result['experience'],
                        extracted_text=result['text'][:5000],
                        cv_file=cv_file,
                        status='new',
                        similarity_score=0.0,
                    )

                    # Calculate similarity score
                    score = calculate_similarity_score(job, candidate)
                    candidate.similarity_score = round(score, 4)
                    candidate.save(update_fields=['similarity_score'])

                    created_candidates.append(candidate)
                    created_count += 1
                    logger.info(f"Created candidate {candidate.full_name} with score {score:.4f}")

                except Exception as e:
                    logger.error(f"Error processing {cv_file.name}: {e}")
                    failed_files.append((cv_file.name, str(e)))
                finally:
                    # Cleanup temp file
                    if temp_path:
                        try:
                            default_storage.delete(temp_path)
                        except:
                            pass

            # AUTO-SHORTLIST: Select top candidates
            if created_candidates:
                shortlisted = auto_shortlist_candidates(
                    job, threshold=0.01, top_n=10
                )
                if shortlisted:
                    messages.info(
                        request,
                        f'\u2b50 Auto-shortlisted {len(shortlisted)} top candidates.'
                    )

            # Feedback messages
            if created_count > 0:
                messages.success(
                    request,
                    f'\u2705 Successfully created {created_count} candidates from uploaded CVs.'
                )

            if failed_files:
                for fname, err in failed_files[:5]:
                    messages.warning(request, f'\u26a0\ufe0f {fname}: {err}')
                if len(failed_files) > 5:
                    messages.warning(
                        request,
                        f'... and {len(failed_files) - 5} more files failed.'
                    )

            return redirect('candidate_list')
    else:
        form = BulkUploadForm()

    jobs = Job.objects.filter(status='active')
    return render(request, 'recruitment/candidate_upload.html', {
        'form': form,
        'jobs': jobs,
    })


def api_update_status(request, candidate_id):
    """API endpoint to update candidate status"""
    if request.method == 'POST':
        candidate = get_object_or_404(Candidate, id=candidate_id)
        status = request.POST.get('status')
        if status in [s[0] for s in Candidate.STATUS_CHOICES]:
            candidate.status = status
            candidate.save(update_fields=['status'])
            messages.success(request, 'Status updated successfully!')
        return redirect('candidate_detail', candidate_id=candidate.id)
    return JsonResponse({'success': False, 'error': 'Invalid request method'})


# =============================================================================
# RANKING & SHORTLISTING
# =============================================================================

def rank_candidates(request, job_id):
    """Rank all candidates for a job by similarity score"""
    job = get_object_or_404(Job, id=job_id)

    # Recalculate all scores
    updated = recalculate_job_scores(job)
    if updated:
        messages.info(request, f'Recalculated scores for {updated} candidates.')

    candidates = job.candidates.order_by('-similarity_score')
    return render(request, 'recruitment/ranking_info.html', {
        'job': job,
        'candidates': candidates,
    })


def shortlist_candidates(request, job_id):
    """Auto-shortlist candidates based on threshold and top N"""
    job = get_object_or_404(Job, id=job_id)

    try:
        threshold = float(request.GET.get('threshold', 0.01))
        top_n = int(request.GET.get('top_n', 10))
    except (ValueError, TypeError):
        threshold = 0.01
        top_n = 10

    # Ensure scores are up to date
    recalculate_job_scores(job)

    shortlisted = auto_shortlist_candidates(job, threshold=threshold, top_n=top_n)
    messages.success(
        request,
        f'Shortlisted {len(shortlisted)} candidates (threshold: {threshold}, top: {top_n})'
    )
    return redirect('job_detail', job_id=job.id)


# =============================================================================
# COMMUNICATION
# =============================================================================

def send_invitations(request, job_id):
    """Send interview invitations to shortlisted candidates"""
    job = get_object_or_404(Job, id=job_id)
    shortlisted = job.candidates.filter(status='shortlisted')

    count = 0
    for candidate in shortlisted:
        if not hasattr(candidate, 'interview'):
            try:
                Interview.objects.create(candidate=candidate)
                candidate.status = 'interview_scheduled'
                candidate.save(update_fields=['status'])
                count += 1
            except Exception as e:
                logger.error(f"Error creating interview for {candidate}: {e}")

    messages.success(request, f'Scheduled interviews for {count} candidates.')
    return redirect('job_detail', job_id=job.id)


def send_results(request, job_id):
    """Send results to candidates (stub - integrate with email backend)"""
    job = get_object_or_404(Job, id=job_id)
    messages.success(request, 'Results notification queued for all candidates.')
    return redirect('job_detail', job_id=job.id)


# =============================================================================
# REPORTS
# =============================================================================

def generate_report(request, job_id):
    """Generate recruitment report for a job"""
    job = get_object_or_404(Job, id=job_id)

    report = Report.objects.create(
        title=f"Recruitment Report - {job.title}",
        job=job,
        total_applicants=job.candidates.count(),
        shortlisted_count=job.candidates.filter(status='shortlisted').count(),
        interviewed_count=job.candidates.filter(
            status__in=['interview_scheduled', 'interview_completed']
        ).count(),
        selected_count=job.candidates.filter(status='selected').count(),
        rejected_count=job.candidates.filter(status='rejected').count(),
    )

    messages.success(request, 'Report generated successfully!')
    return redirect('report_detail', report_id=report.id)


def report_list(request):
    """List all reports"""
    reports = Report.objects.select_related('job').order_by('-generated_at')
    return render(request, 'recruitment/report_list.html', {'reports': reports})


def report_detail(request, report_id):
    """View report details"""
    report = get_object_or_404(Report, id=report_id)
    return render(request, 'recruitment/report_detail.html', {'report': report})


# =============================================================================
# INTERVIEW
# =============================================================================

def interview_portal(request, token):
    """Interview portal accessed via unique token"""
    interview = get_object_or_404(Interview, access_token=token)
    return render(request, 'recruitment/interview_portal.html', {
        'interview': interview,
    })


# =============================================================================
# PARSER API
# =============================================================================

@csrf_exempt
def parse_cv_api(request):
    """API endpoint to parse a CV file and return extracted data"""
    if request.method == 'POST' and request.FILES.get('cv_file'):
        cv_file = request.FILES['cv_file']
        temp_path = None

        try:
            temp_path = default_storage.save(
                f'temp/api_{uuid.uuid4().hex}_{cv_file.name}',
                ContentFile(cv_file.read())
            )
            full_temp_path = os.path.join(default_storage.location, temp_path)

            result = parse_cv(full_temp_path)
            return JsonResponse(result)
        except Exception as e:
            logger.error(f"CV parsing API error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
        finally:
            if temp_path:
                try:
                    default_storage.delete(temp_path)
                except:
                    pass

    return JsonResponse({'success': False, 'error': 'No file provided'})


def parser_info(request):
    """Info page about the CV parser"""
    return render(request, 'recruitment/parser_info.html')
