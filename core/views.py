import logging

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
import json

from .models import (
    JobDescription, Candidate, Interview,
    InterviewEvaluation, EmailLog, HRReport
)
from .cv_parser import parse_cv
from .forms import BulkUploadForm, JobForm, JobEditForm, CandidateEditForm
from ranking.ranker import rank_cvs
from shortlist.shortlister import shortlist_candidates
from emailer.email_sender import send_interview_invitation, send_rejection_email, send_selection_email

logger = logging.getLogger('ai_recruitment')


def dashboard(request):
    """Main dashboard view"""
    jobs = JobDescription.objects.all()
    total_candidates = Candidate.objects.count()
    shortlisted = Candidate.objects.filter(status='shortlisted').count()
    interviews = Interview.objects.filter(status='completed').count()
    selected = Candidate.objects.filter(status='selected').count()

    recent_candidates = Candidate.objects.all()[:10]
    active_jobs = JobDescription.objects.filter(status='active')

    context = {
        'total_jobs': jobs.count(),
        'total_candidates': total_candidates,
        'shortlisted': shortlisted,
        'completed_interviews': interviews,
        'selected': selected,
        'recent_candidates': recent_candidates,
        'active_jobs': active_jobs,
    }
    return render(request, 'core/dashboard.html', context)


def job_list(request):
    """List all job descriptions"""
    jobs = JobDescription.objects.all().order_by('-created_at')
    return render(request, 'core/job_list.html', {'jobs': jobs})


def job_create(request):
    """Create a new job description"""
    if request.method == 'POST':
        form = JobForm(request.POST)
        if form.is_valid():
            job = form.save(commit=False)
            job.created_by = request.user if request.user.is_authenticated else None
            job.save()
            messages.success(request, 'Job description created successfully!')
            return redirect('job_detail', job_id=job.id)
    else:
        form = JobForm()

    return render(request, 'core/job_create.html', {'form': form})


def job_detail(request, job_id):
    """View job details and candidates"""
    job = get_object_or_404(JobDescription, id=job_id)
    candidates = Candidate.objects.filter(applied_job=job).order_by('-similarity_score')
    return render(request, 'core/job_detail.html', {'job': job, 'candidates': candidates})


def job_edit(request, job_id):
    """Edit job description"""
    job = get_object_or_404(JobDescription, id=job_id)
    if request.method == 'POST':
        form = JobEditForm(request.POST, instance=job)
        if form.is_valid():
            form.save()
            messages.success(request, 'Job description updated!')
            return redirect('job_detail', job_id=job.id)
    else:
        form = JobEditForm(instance=job)

    return render(request, 'core/job_edit.html', {'job': job, 'form': form})


def job_delete(request, job_id):
    """Delete job description"""
    job = get_object_or_404(JobDescription, id=job_id)
    if request.method == 'POST':
        job.delete()
        messages.success(request, 'Job deleted successfully!')
        return redirect('job_list')
    return render(request, 'core/job_confirm_delete.html', {'job': job})


def candidate_upload(request):
    """
    BULK CV UPLOAD
    --------------
    Matches candidate_upload.html: a single, bulk-only upload flow.
    Multiple CVs can be uploaded at once for one job. Each CV is:
      1. Saved and parsed via parse_cv() - name, email, skills, education,
         and experience are all extracted automatically from the CV text
         (recruitment-sourced cv_parser.py)
      2. Turned into a Candidate record
      3. Scored against the job description via TF-IDF + Cosine Similarity
         (core's ranking.ranker, same pipeline as the rest of the app)
      4. Auto-shortlisted if it clears the threshold (core's shortlist app)
    """
    if request.method == 'POST':
        form = BulkUploadForm(request.POST, request.FILES)
        if form.is_valid():
            job = form.cleaned_data['job_id']
            cv_files = form.cleaned_data['cv_files']
            threshold = form.cleaned_data.get('threshold') or 0.01
            top_n = form.cleaned_data.get('top_n') or 10

            created_candidates = []
            failed_files = []

            for cv_file in cv_files:
                try:
                    candidate = Candidate.objects.create(
                        first_name='',
                        last_name='',
                        email='',
                        cv_file=cv_file,
                        applied_job=job,
                        status='new'
                    )

                    result = parse_cv(candidate.cv_file.path)
                    if not result['success']:
                        raise ValueError(result['error'] or 'No text could be extracted')

                    candidate.cv_text = result['text']
                    candidate.first_name = result['first_name'] or 'Unknown'
                    candidate.last_name = result['last_name']
                    candidate.email = result['email']
                    candidate.skills = result['skills']
                    candidate.education = result['education']
                    candidate.experience = result['experience']
                    candidate.status = 'screening'
                    candidate.save()

                    created_candidates.append(candidate)
                    logger.info(f"Bulk upload: created candidate {candidate.full_name} for job {job.title}")

                except Exception as e:
                    logger.error(f"Bulk upload failed for {cv_file.name}: {e}")
                    failed_files.append((cv_file.name, str(e)))

            # Rank the newly created candidates against the job description
            if created_candidates:
                job_description = f"{job.title}\n{job.description}\n{job.required_skills}"
                cv_texts = {
                    str(c.id): c.cv_text for c in created_candidates if c.cv_text
                }

                if cv_texts:
                    ranked_results = rank_cvs(job_description, cv_texts)
                    candidate_map = {str(c.id): c for c in created_candidates}
                    for candidate_id, score in ranked_results:
                        candidate_map[candidate_id].similarity_score = score
                        candidate_map[candidate_id].save(update_fields=['similarity_score'])

                    # Auto-shortlist top candidates from this batch
                    ranked_list = [(str(c.id), c.similarity_score) for c in created_candidates]
                    shortlisted = shortlist_candidates(ranked_list, threshold=threshold, top_n=top_n)
                    shortlisted_ids = {int(c[0]) for c in shortlisted}

                    for candidate in created_candidates:
                        if candidate.id in shortlisted_ids and candidate.status == 'screening':
                            candidate.status = 'shortlisted'
                            candidate.save(update_fields=['status'])

                    if shortlisted_ids:
                        messages.info(request, f'Auto-shortlisted {len(shortlisted_ids)} top candidates from this batch.')

            if created_candidates:
                messages.success(request, f'Successfully uploaded and parsed {len(created_candidates)} CVs for {job.title}.')

            if failed_files:
                for fname, err in failed_files[:5]:
                    messages.warning(request, f'{fname}: {err}')
                if len(failed_files) > 5:
                    messages.warning(request, f'... and {len(failed_files) - 5} more files failed.')

            return redirect('candidate_list')
        else:
            messages.error(request, 'Please fix the errors below.')
    else:
        form = BulkUploadForm()

    jobs = JobDescription.objects.filter(status='active')
    return render(request, 'core/candidate_upload.html', {'form': form, 'jobs': jobs})


def candidate_detail(request, candidate_id):
    """View candidate details"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    context = {
        'candidate': candidate,
        'interview': getattr(candidate, 'interview', None),
    }
    return render(request, 'core/candidate_detail.html', context)

def candidate_edit(request, candidate_id):
    """Edit candidate name and email"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    if request.method == 'POST':
        form = CandidateEditForm(request.POST, instance=candidate)
        if form.is_valid():
            form.save()
            messages.success(request, 'Candidate details updated successfully!')
            return redirect('candidate_detail', candidate_id=candidate.id)
    else:
        form = CandidateEditForm(instance=candidate)

    return render(request, 'core/candidate_edit.html', {'candidate': candidate, 'form': form})

def candidate_delete(request, candidate_id):
    """Delete candidate and their CV file"""
    candidate = get_object_or_404(Candidate, id=candidate_id)
    if request.method == 'POST':
        # Optional: delete the physical CV file from storage
        if candidate.cv_file:
            candidate.cv_file.delete(save=False)
        candidate.delete()
        messages.success(request, 'Candidate deleted successfully!')
        return redirect('candidate_list')
    return render(request, 'core/candidate_confirm_delete.html', {'candidate': candidate})


def candidate_list(request):
    """List all candidates"""
    candidates = Candidate.objects.all().order_by('-created_at')
    status_filter = request.GET.get('status')
    job_filter = request.GET.get('job')

    if status_filter:
        candidates = candidates.filter(status=status_filter)
    if job_filter:
        candidates = candidates.filter(applied_job_id=job_filter)

    jobs = JobDescription.objects.all()
    return render(request, 'core/candidate_list.html', {
        'candidates': candidates,
        'jobs': jobs,
        'status_filter': status_filter,
        'job_filter': job_filter
    })


def rank_candidates(request, job_id):
    """Rank candidates for a job using TF-IDF and Cosine Similarity"""
    job = get_object_or_404(JobDescription, id=job_id)
    candidates = Candidate.objects.filter(applied_job=job, cv_text__isnull=False).exclude(cv_text='')

    if not candidates:
        messages.warning(request, 'No candidates with parsed CVs found for this job!')
        return redirect('job_detail', job_id=job.id)

    # Prepare data for ranking
    job_description = f"{job.title}\n{job.description}\n{job.required_skills}"
    cv_texts = {}
    candidate_map = {}

    for candidate in candidates:
        cv_texts[str(candidate.id)] = candidate.cv_text
        candidate_map[str(candidate.id)] = candidate

    # Rank using TF-IDF + Cosine Similarity
    ranked_results = rank_cvs(job_description, cv_texts)

    # Update candidate scores
    for candidate_id, score in ranked_results:
        candidate = candidate_map[candidate_id]
        candidate.similarity_score = score
        candidate.save()

    messages.success(request, f'Candidates ranked successfully! {len(ranked_results)} candidates processed.')
    return redirect('job_detail', job_id=job.id)


def shortlist_top_candidates(request, job_id):
    """Shortlist top candidates"""
    job = get_object_or_404(JobDescription, id=job_id)
    candidates = Candidate.objects.filter(applied_job=job).order_by('-similarity_score')

    if not candidates:
        messages.warning(request, 'No candidates found for this job!')
        return redirect('job_detail', job_id=job.id)

    # Get threshold from settings or request
    threshold = float(request.GET.get('threshold', 0.01))
    top_n = int(request.GET.get('top_n', 10))

    ranked_list = [(str(c.id), c.similarity_score) for c in candidates]
    shortlisted = shortlist_candidates(ranked_list, threshold=threshold, top_n=top_n)

    shortlisted_ids = [int(c[0]) for c in shortlisted]

    # Update status for shortlisted candidates
    shortlisted_count = 0
    for candidate in candidates:
        if candidate.id in shortlisted_ids and candidate.status == 'screening':
            candidate.status = 'shortlisted'
            candidate.save()
            shortlisted_count += 1

    messages.success(request, f'{shortlisted_count} candidates shortlisted!')
    return redirect('job_detail', job_id=job.id)


def send_interview_invitations(request, job_id):
    """Send interview invitations to shortlisted candidates"""
    job = get_object_or_404(JobDescription, id=job_id)
    shortlisted = Candidate.objects.filter(applied_job=job, status='shortlisted')

    sent_count = 0
    failed_count = 0

    for candidate in shortlisted:
        # Create interview record
        interview, created = Interview.objects.get_or_create(
            candidate=candidate,
            defaults={
                'status': 'scheduled',
                'scheduled_date': timezone.now(),
                'expires_at': timezone.now() + timedelta(days=3)
            }
        )

        if created:
            candidate.status = 'interview_scheduled'
            candidate.save()

        # Send email
        success, error = send_interview_invitation(candidate.email, candidate.full_name, interview.access_token)

        EmailLog.objects.create(
            candidate=candidate,
            subject='Interview Invitation',
            body=f'Interview invitation sent to {candidate.email}',
            status='sent' if success else 'failed',
            error_message=error if not success else ''
        )

        if success:
            sent_count += 1
        else:
            failed_count += 1

    messages.success(request, f'Invitations sent: {sent_count}, Failed: {failed_count}')
    return redirect('job_detail', job_id=job.id)


def send_results(request, job_id):
    """Send final results to all candidates"""
    job = get_object_or_404(JobDescription, id=job_id)
    candidates = Candidate.objects.filter(applied_job=job)

    for candidate in candidates:
        if candidate.status == 'selected':
            success, error = send_selection_email(candidate.email, candidate.full_name)
        elif candidate.status == 'rejected':
            success, error = send_rejection_email(candidate.email, candidate.full_name)
        else:
            continue

        EmailLog.objects.create(
            candidate=candidate,
            subject='Application Result',
            body=f'Result email sent to {candidate.email}',
            status='sent' if success else 'failed',
            error_message=error if not success else ''
        )

    messages.success(request, 'Result emails sent to all candidates!')
    return redirect('job_detail', job_id=job.id)


def generate_report(request, job_id):
    """Generate HR report for a job"""
    job = get_object_or_404(JobDescription, id=job_id)
    candidates = Candidate.objects.filter(applied_job=job)

    total = candidates.count()
    shortlisted = candidates.filter(status='shortlisted').count()
    interviewed = Interview.objects.filter(candidate__in=candidates, status='completed').count()
    selected = candidates.filter(status='selected').count()
    rejected = candidates.filter(status='rejected').count()

    report_data = {
        'status_breakdown': list(candidates.values('status').annotate(count=Count('status'))),
        'avg_similarity': list(candidates.aggregate(avg=Avg('similarity_score')).values())[0] or 0,
        'top_skills': get_top_skills(candidates),
    }

    report = HRReport.objects.create(
        job=job,
        title=f"Recruitment Report - {job.title} - {timezone.now().strftime('%Y-%m-%d')}",
        total_applicants=total,
        shortlisted_count=shortlisted,
        interviewed_count=interviewed,
        selected_count=selected,
        rejected_count=rejected,
        report_data=report_data,
        generated_by=request.user if request.user.is_authenticated else None
    )

    messages.success(request, 'HR Report generated successfully!')
    return redirect('report_detail', report_id=report.id)


def report_detail(request, report_id):
    """View HR report"""
    report = get_object_or_404(HRReport, id=report_id)
    return render(request, 'core/report_detail.html', {'report': report})


def report_list(request):
    """List all HR reports"""
    reports = HRReport.objects.all().order_by('-generated_at')
    return render(request, 'core/report_list.html', {'reports': reports})


def interview_portal(request, token):
    """Candidate interview portal - accessed via unique token"""
    interview = get_object_or_404(Interview, access_token=token)

    if interview.status == 'expired' or (interview.expires_at and interview.expires_at < timezone.now()):
        return render(request, 'interview/interview_expired.html')

    if request.method == 'POST':
        # Mark interview as completed
        interview.status = 'completed'
        interview.completed_date = timezone.now()
        interview.save()

        candidate = interview.candidate
        candidate.status = 'interview_completed'
        candidate.save()

        messages.success(request, 'Interview completed successfully!')
        return render(request, 'interview/interview_completed.html')

    interview.status = 'in_progress'
    interview.save()

    return render(request, 'interview/interview_portal.html', {
        'interview': interview,
        'candidate': interview.candidate
    })


def api_job_stats(request, job_id):
    """API endpoint for job statistics"""
    job = get_object_or_404(JobDescription, id=job_id)
    candidates = Candidate.objects.filter(applied_job=job)

    data = {
        'total_applicants': candidates.count(),
        'status_breakdown': list(candidates.values('status').annotate(count=Count('status'))),
        'avg_similarity_score': candidates.aggregate(avg=Avg('similarity_score'))['avg'] or 0,
    }
    return JsonResponse(data)


def api_update_candidate_status(request, candidate_id):
    """API endpoint to update candidate status"""
    if request.method == 'POST':
        candidate = get_object_or_404(Candidate, id=candidate_id)
        new_status = request.POST.get('status')
        if new_status in [s[0] for s in Candidate.STATUS_CHOICES]:
            candidate.status = new_status
            candidate.save()
            return JsonResponse({'success': True, 'status': new_status})
        return JsonResponse({'success': False, 'error': 'Invalid status'})
    return JsonResponse({'success': False, 'error': 'Method not allowed'})


def get_top_skills(candidates):
    """Extract top skills from candidates"""
    from collections import Counter
    all_skills = []
    for candidate in candidates:
        if candidate.skills:
            skills = [s.strip() for s in candidate.skills.split(',')]
            all_skills.extend(skills)
    return Counter(all_skills).most_common(10)


def analytics_dashboard(request):
    """Analytics dashboard with charts"""
    # Overall stats
    total_jobs = JobDescription.objects.count()
    total_candidates = Candidate.objects.count()
    shortlisted = Candidate.objects.filter(status='shortlisted').count()
    selected = Candidate.objects.filter(status='selected').count()

    # Status distribution for pie chart
    status_distribution = list(Candidate.objects.values('status').annotate(count=Count('status')))

    # Monthly applications
    from django.db.models.functions import TruncMonth
    monthly_data = list(Candidate.objects.annotate(
        month=TruncMonth('created_at')
    ).values('month').annotate(count=Count('id')).order_by('month'))

    # Top jobs by applicants
    top_jobs = list(JobDescription.objects.annotate(
        applicant_count=Count('candidates')
    ).values('title', 'applicant_count').order_by('-applicant_count')[:10])

    context = {
        'total_jobs': total_jobs,
        'total_candidates': total_candidates,
        'shortlisted': shortlisted,
        'selected': selected,
        'status_distribution': json.dumps(status_distribution),
        'monthly_data': json.dumps(monthly_data, default=str),
        'top_jobs': json.dumps(top_jobs),
    }
    return render(request, 'core/analytics.html', context)
