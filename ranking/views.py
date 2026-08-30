from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import logging

from core.models import JobDescription, Candidate
from .ranker import rank_cvs, batch_rank, get_top_keywords

logger = logging.getLogger('ai_recruitment')


def rank_job_candidates(request, job_id):

    job = get_object_or_404(JobDescription, id=job_id)

    # Get job description text
    job_text = f"{job.title}\n{job.description}\n{job.required_skills}\n{job.education_required}\n{job.experience_required}"

    # Get candidates with CV text
    candidates = Candidate.objects.filter(applied_job=job).exclude(cv_text='')

    if not candidates:
        return JsonResponse({'success': False, 'error': 'No candidates with parsed CVs found'})

    # Rank candidates
    results = batch_rank(job_text, candidates)

    # Format response
    ranked_list = []
    for candidate, score in results:
        keywords = get_top_keywords(job_text, candidate.cv_text, 5)
        ranked_list.append({
            'candidate_id': candidate.id,
            'name': candidate.full_name,
            'email': candidate.email,
            'score': round(score, 4),
            'status': candidate.status,
            'top_keywords': [k[0] for k in keywords]
        })

    return JsonResponse({
        'success': True,
        'job_title': job.title,
        'total_candidates': len(results),
        'ranked_candidates': ranked_list
    })


def ranking_info(request):
    """Info page about the ranking algorithm"""
    return render(request, 'ranking/ranking_info.html')
