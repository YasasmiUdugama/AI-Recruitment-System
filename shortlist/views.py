from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
import logging

from core.models import JobDescription, Candidate
from .shortlister import shortlist_candidates, get_shortlist_summary

logger = logging.getLogger('ai_recruitment')


def shortlist_api(request, job_id):
    """API endpoint to shortlist candidates for a job"""
    job = get_object_or_404(JobDescription, id=job_id)

    # Get parameters
    threshold = float(request.GET.get('threshold', 0.01))
    top_n = int(request.GET.get('top_n', 10))

    # Get ranked candidates
    candidates = Candidate.objects.filter(applied_job=job).order_by('-similarity_score')

    if not candidates:
        return JsonResponse({'success': False, 'error': 'No candidates found'})

    ranked_list = [(str(c.id), c.similarity_score) for c in candidates if c.similarity_score > 0]

    if not ranked_list:
        return JsonResponse({'success': False, 'error': 'No ranked candidates found. Run ranking first.'})

    summary = get_shortlist_summary(ranked_list, threshold, top_n)

    shortlisted_ids = summary['shortlisted_ids']

    shortlisted_candidates = []
    for candidate in candidates:
        if candidate.id in shortlisted_ids and candidate.status == 'screening':
            candidate.status = 'shortlisted'
            candidate.save()
            shortlisted_candidates.append({
                'id': candidate.id,
                'name': candidate.full_name,
                'email': candidate.email,
                'score': round(candidate.similarity_score, 4)
            })

    return JsonResponse({
        'success': True,
        'summary': summary,
        'shortlisted': shortlisted_candidates
    })


def shortlist_info(request):

    return render(request, 'shortlist/shortlist_info.html')
