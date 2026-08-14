from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from datetime import timedelta
import json
import logging
import re

from django.db.models import Avg, Count, Q

from core.models import Candidate, Interview, InterviewResponse, InterviewEvaluation, JobDescription
from .interview_engine import (
    get_questions, evaluate_answer, evaluate_technical_answer,
    calculate_overall_score, get_interview_feedback
)

logger = logging.getLogger('ai_recruitment')


def interview_questions_api(request, job_type='general'):
    """API to get interview questions"""
    count = int(request.GET.get('count', 5))
    questions = get_questions(job_type, count)
    return JsonResponse({
        'success': True,
        'questions': questions
    })


def evaluate_answer_api(request):
    """API to evaluate a single answer"""
    if request.method == 'POST':
        data = json.loads(request.body)
        answer = data.get('answer', '')
        question_id = data.get('question_id', 0)

        score = evaluate_answer(answer, question_id)

        return JsonResponse({
            'success': True,
            'score': score,
            'max_score': 1.0,
            'feedback': get_interview_feedback(score)
        })

    return JsonResponse({'success': False, 'error': 'POST required'})


def save_response_api(request):
    """Save an interview response"""
    if request.method == 'POST':
        data = json.loads(request.body)

        interview_id = data.get('interview_id')
        question_index = data.get('question_index')
        question_text = data.get('question_text')
        answer_text = data.get('answer_text')
        keyword_score = data.get('keyword_score', 0)
        confidence_score = data.get('confidence_score', 0)
        transcription = data.get('transcription', '')
        emotion_data = data.get('emotion_data', {})
        voice_analysis = data.get('voice_analysis', {})

        try:
            interview = Interview.objects.get(id=interview_id)

            response, created = InterviewResponse.objects.update_or_create(
                interview=interview,
                question_index=question_index,
                defaults={
                    'question_text': question_text,
                    'answer_text': answer_text,
                    'keyword_score': keyword_score,
                    'confidence_score': confidence_score,
                    'transcription': transcription,
                    'emotion_data': emotion_data,
                    'voice_analysis': voice_analysis,
                }
            )

            return JsonResponse({'success': True, 'response_id': response.id})

        except Interview.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Interview not found'})
        except Exception as e:
            logger.error(f"Error saving response: {e}")
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'error': 'POST required'})


@csrf_exempt
def upload_video_api(request):
    """Save the recorded webcam video clip for a single interview question."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})

    interview_id = request.POST.get('interview_id')
    question_index = request.POST.get('question_index')
    question_text = request.POST.get('question_text', '')
    video_file = request.FILES.get('video')

    if not interview_id or question_index is None:
        return JsonResponse({'success': False, 'error': 'Missing interview_id or question_index'})

    if not video_file:
        return JsonResponse({'success': False, 'error': 'No video file received'})

    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Interview not found'})

    try:
        response, created = InterviewResponse.objects.update_or_create(
            interview=interview,
            question_index=int(question_index),
            defaults={'video_file': video_file, 'question_text': question_text},
        )
        logger.info(f"Saved video for interview {interview_id}, question {question_index} (response {response.id})")
        return JsonResponse({'success': True, 'response_id': response.id})
    except Exception as e:
        logger.error(f"Error saving video for interview {interview_id}, question {question_index}: {e}")
        return JsonResponse({'success': False, 'error': str(e)})


def calculate_response_score(answer_text, question_id, job_type='general'):
    """
    Calculate a comprehensive score (0.0 - 1.0) for a single answer.
    Returns score and confidence estimate.
    """
    if not answer_text or not answer_text.strip():
        return 0.05, 0.3

    answer_lower = answer_text.lower()
    words = answer_text.split()
    word_count = len(words)

    base_keyword_score = evaluate_answer(answer_text, question_id)

    score_factors = {
        'keyword_match': base_keyword_score,
        'length_quality': 0.0,
        'technical_depth': 0.0,
        'structure_quality': 0.0,
        'specificity': 0.0,
    }

    if word_count >= 15:
        score_factors['length_quality'] = min(word_count / 80, 1.0)
    elif word_count >= 5:
        score_factors['length_quality'] = 0.3 + (word_count / 50)
    else:
        score_factors['length_quality'] = 0.1

    depth_patterns = [
        r'\b(example|instance|specific|particular)\b',
        r'\b(developed|implemented|designed|created|built)\b',
        r'\b(process|methodology|approach|strategy|framework)\b',
        r'\b(result|outcome|achieved|improved|increased|decreased)\b',
        r'\b(challenge|problem|issue|obstacle|difficulty)\b',
        r'\b(solution|resolved|fixed|addressed|handled)\b',
        r'\b(team|collaborated|led|managed|coordinated)\b',
        r'\b(learned|grew|adapted|evolved|improved)\b',
    ]
    depth_matches = sum(1 for pattern in depth_patterns if re.search(pattern, answer_lower))
    score_factors['technical_depth'] = min(depth_matches / 4, 1.0)

    structure_patterns = [
        r'\b(first|initially|to begin|started)\b',
        r'\b(then|next|after|subsequently|following)\b',
        r'\b(finally|ultimately|in conclusion|overall)\b',
        r'\b(because|since|therefore|thus|as a result)\b',
        r'\b(however|although|while|whereas|despite)\b',
    ]
    structure_matches = sum(1 for pattern in structure_patterns if re.search(pattern, answer_lower))
    score_factors['structure_quality'] = min(structure_matches / 2.5, 1.0)

    specificity_patterns = [
        r'\d+',
        r'\b(year|month|week|day|hour)s?\b',
        r'\b(percent|%|percentage)\b',
        r'\b(python|javascript|java|sql|react|django|flask|aws|azure|gcp)\b',
        r'\b(agile|scrum|kanban|waterfall|devops|ci/cd)\b',
        r'\b(team of|group of|collaborated with|worked with)\b',
    ]
    specificity_matches = sum(1 for pattern in specificity_patterns if re.search(pattern, answer_lower))
    score_factors['specificity'] = min(specificity_matches / 3, 1.0)

    weights = {
        'keyword_match': 0.30,
        'length_quality': 0.20,
        'technical_depth': 0.25,
        'structure_quality': 0.15,
        'specificity': 0.10,
    }

    final_score = sum(score_factors[k] * weights[k] for k in weights.keys())
    final_score = max(final_score, 0.05)

    confidence_base = 0.4
    confidence_word_bonus = min(word_count / 200, 0.3)
    confidence_structure_bonus = score_factors['structure_quality'] * 0.2
    confidence_depth_bonus = score_factors['technical_depth'] * 0.1

    confidence_score = confidence_base + confidence_word_bonus + confidence_structure_bonus + confidence_depth_bonus
    confidence_score = min(confidence_score, 1.0)

    return round(final_score, 2), round(confidence_score, 2)


@csrf_exempt
def complete_interview_api(request):
    """Complete an interview and generate evaluation"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST required'})

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'error': 'Invalid JSON data'})

    interview_id = data.get('interview_id')
    answers = data.get('answers', [])

    if not interview_id:
        return JsonResponse({'success': False, 'error': 'Missing interview_id'})

    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Interview not found'})

    try:
        # FIX: Use transaction to ensure all saves succeed or all fail
        with transaction.atomic():
            if answers and len(answers) > 0:
                logger.info(f"Processing {len(answers)} answers for interview {interview_id}")
                
                for i, ans in enumerate(answers):
                    question_id = ans.get('question_id', i)
                    question_text = ans.get('question_text', '')
                    answer_text = ans.get('answer_text', '')

                    logger.debug(f"Q{i}: answer length={len(answer_text) if answer_text else 0}")

                    # Calculate scores for this answer
                    keyword_score, confidence_score = calculate_response_score(
                        answer_text, question_id, getattr(interview, 'job_type', None) or 'general'
                    )

                    logger.debug(f"Q{i}: keyword_score={keyword_score}, confidence_score={confidence_score}")

                    # Update (or create) the response row without touching video_file,
                    # so any video clip already uploaded for this question is preserved.
                    response, _ = InterviewResponse.objects.update_or_create(
                        interview=interview,
                        question_index=i,
                        defaults={
                            'question_text': question_text,
                            'answer_text': answer_text,
                            'keyword_score': keyword_score,
                            'confidence_score': confidence_score,
                            'transcription': answer_text,
                            'emotion_data': {},
                            'voice_analysis': {},
                        }
                    )

                    logger.info(f"Saved response {response.id} for question {i}")

        # Now fetch all responses
        responses = InterviewResponse.objects.filter(interview=interview)
        response_count = responses.count()
        logger.info(f"Found {response_count} responses for interview {interview_id}")

        if response_count == 0:
            logger.error(f"No responses found after saving for interview {interview_id}")
            return JsonResponse({
                'success': False,
                'error': 'Failed to save responses. Please try again.'
            })

        # Calculate scores from responses
        response_data = []
        for resp in responses:
            ks = resp.keyword_score if resp.keyword_score is not None else 0.05
            cs = resp.confidence_score if resp.confidence_score is not None else 0.3
            
            ks = max(float(ks), 0.05)
            cs = max(float(cs), 0.1)
            
            response_data.append({
                'keyword_score': ks,
                'confidence_score': cs,
            })

        logger.info(f"Calculating overall score from {len(response_data)} responses")
        summary = calculate_overall_score(response_data)

        # Convert to 1-100 scale
        overall_percent = int(summary['overall_score'] * 100)
        keyword_percent = int(summary['keyword_score_avg'] * 100)
        confidence_percent = int(summary['confidence_score_avg'] * 100)

        overall_percent = max(overall_percent, 1)
        keyword_percent = max(keyword_percent, 1)
        confidence_percent = max(confidence_percent, 1)

        recommendation = 'recommended' if summary['overall_score'] >= 0.6 else 'not_recommended'
        feedback = get_interview_feedback(summary['overall_score'])

        logger.info(f"Interview {interview_id}: overall={overall_percent}, keyword={keyword_percent}, confidence={confidence_percent}, rec={recommendation}")

        # Create evaluation
        evaluation, created = InterviewEvaluation.objects.update_or_create(
            interview=interview,
            defaults={
                'overall_score': summary['overall_score'],
                'keyword_score_avg': summary['keyword_score_avg'],
                'confidence_score_avg': summary['confidence_score_avg'],
                'recommendation': recommendation,
                'notes': feedback
            }
        )

        # Update statuses
        interview.status = 'completed'
        interview.completed_date = timezone.now()
        interview.save()

        candidate = interview.candidate
        candidate.status = 'interview_completed'
        candidate.save()

        return JsonResponse({
            'success': True,
            'evaluation': {
                'overall_score': overall_percent,
                'keyword_score_avg': keyword_percent,
                'confidence_score_avg': confidence_percent,
                'recommendation': recommendation,
                'feedback': feedback
            }
        })

    except Exception as e:
        logger.error(f"Error completing interview {interview_id}: {e}", exc_info=True)
        return JsonResponse({'success': False, 'error': str(e)})


def interview_info(request):
    """Info page about the AI interview system"""
    return render(request, 'interview/interview_info.html')


# ---------------------------------------------------------------------------
# HR Partner API endpoints
# ---------------------------------------------------------------------------

def hr_dashboard_api(request):
    """High-level summary stats for the HR dashboard"""
    total_candidates = Candidate.objects.count()
    total_jobs = JobDescription.objects.filter(status='active').count()

    interview_counts = Interview.objects.aggregate(
        pending=Count('id', filter=Q(status='pending')),
        scheduled=Count('id', filter=Q(status='scheduled')),
        in_progress=Count('id', filter=Q(status='in_progress')),
        completed=Count('id', filter=Q(status='completed')),
        expired=Count('id', filter=Q(status='expired')),
    )

    evaluation_stats = InterviewEvaluation.objects.aggregate(
        avg_overall_score=Avg('overall_score'),
        recommended_count=Count('id', filter=Q(recommendation='recommended')),
        not_recommended_count=Count('id', filter=Q(recommendation='not_recommended')),
    )

    candidate_status_counts = {
        row['status']: row['count']
        for row in Candidate.objects.values('status').annotate(count=Count('id'))
    }

    return JsonResponse({
        'success': True,
        'total_candidates': total_candidates,
        'active_jobs': total_jobs,
        'interviews': interview_counts,
        'evaluations': {
            'average_score': round((evaluation_stats['avg_overall_score'] or 0) * 100, 1),
            'recommended': evaluation_stats['recommended_count'],
            'not_recommended': evaluation_stats['not_recommended_count'],
        },
        'candidates_by_status': candidate_status_counts,
    })


def interview_list_api(request):
    """List all interviews, optionally filtered by status"""
    interviews = Interview.objects.select_related('candidate', 'candidate__applied_job').all()

    status = request.GET.get('status')
    if status:
        interviews = interviews.filter(status=status)

    job_id = request.GET.get('job_id')
    if job_id:
        interviews = interviews.filter(candidate__applied_job_id=job_id)

    data = []
    for interview in interviews:
        evaluation = getattr(interview, 'evaluation', None)
        data.append({
            'id': interview.id,
            'candidate_id': interview.candidate_id,
            'candidate_name': interview.candidate.full_name,
            'job_title': interview.candidate.applied_job.title,
            'status': interview.status,
            'scheduled_date': interview.scheduled_date,
            'completed_date': interview.completed_date,
            'overall_score': round(evaluation.overall_score * 100) if evaluation else None,
            'recommendation': evaluation.recommendation if evaluation else None,
        })

    return JsonResponse({'success': True, 'count': len(data), 'interviews': data})


def interview_detail_api(request, interview_id):
    """Details for a single interview, including its responses"""
    interview = get_object_or_404(
        Interview.objects.select_related('candidate', 'candidate__applied_job'),
        id=interview_id
    )

    responses = InterviewResponse.objects.filter(interview=interview).order_by('question_index')
    evaluation = getattr(interview, 'evaluation', None)

    response_data = [
        {
            'question_index': r.question_index,
            'question_text': r.question_text,
            'answer_text': r.answer_text,
            'keyword_score': r.keyword_score,
            'confidence_score': r.confidence_score,
            'video_url': (r.video_file.url if r.video_file else None),
        }
        for r in responses
    ]

    return JsonResponse({
        'success': True,
        'interview': {
            'id': interview.id,
            'candidate_id': interview.candidate_id,
            'candidate_name': interview.candidate.full_name,
            'job_title': interview.candidate.applied_job.title,
            'status': interview.status,
            'scheduled_date': interview.scheduled_date,
            'completed_date': interview.completed_date,
        },
        'responses': response_data,
        'evaluation': {
            'overall_score': round(evaluation.overall_score * 100),
            'keyword_score_avg': round(evaluation.keyword_score_avg * 100),
            'confidence_score_avg': round(evaluation.confidence_score_avg * 100),
            'recommendation': evaluation.recommendation,
            'notes': evaluation.notes,
        } if evaluation else None,
    })


def evaluation_report_api(request, interview_id):
    """Full evaluation report for a completed interview"""
    interview = get_object_or_404(
        Interview.objects.select_related('candidate', 'candidate__applied_job'),
        id=interview_id
    )
    evaluation = get_object_or_404(InterviewEvaluation, interview=interview)
    responses = InterviewResponse.objects.filter(interview=interview).order_by('question_index')

    return JsonResponse({
        'success': True,
        'candidate': {
            'id': interview.candidate.id,
            'name': interview.candidate.full_name,
            'email': interview.candidate.email,
            'job_title': interview.candidate.applied_job.title,
        },
        'evaluation': {
            'overall_score': round(evaluation.overall_score * 100),
            'keyword_score_avg': round(evaluation.keyword_score_avg * 100),
            'confidence_score_avg': round(evaluation.confidence_score_avg * 100),
            'recommendation': evaluation.recommendation,
            'notes': evaluation.notes,
            'generated_at': evaluation.created_at,
        },
        'responses': [
            {
                'question_index': r.question_index,
                'question_text': r.question_text,
                'answer_text': r.answer_text,
                'keyword_score': r.keyword_score,
                'confidence_score': r.confidence_score,
                'video_url': (r.video_file.url if r.video_file else None),
            }
            for r in responses
        ],
    })


def candidate_list_api(request):
    """List all candidates, optionally filtered by status or job"""
    candidates = Candidate.objects.select_related('applied_job').all()

    status = request.GET.get('status')
    if status:
        candidates = candidates.filter(status=status)

    job_id = request.GET.get('job_id')
    if job_id:
        candidates = candidates.filter(applied_job_id=job_id)

    data = [
        {
            'id': c.id,
            'name': c.full_name,
            'email': c.email,
            'phone': c.phone,
            'job_title': c.applied_job.title,
            'status': c.status,
            'similarity_score': c.similarity_score,
            'created_at': c.created_at,
        }
        for c in candidates
    ]

    return JsonResponse({'success': True, 'count': len(data), 'candidates': data})


def candidate_detail_api(request, candidate_id):
    """Details for a single candidate, including interview status if available"""
    candidate = get_object_or_404(Candidate.objects.select_related('applied_job'), id=candidate_id)
    interview = getattr(candidate, 'interview', None)

    return JsonResponse({
        'success': True,
        'candidate': {
            'id': candidate.id,
            'name': candidate.full_name,
            'email': candidate.email,
            'phone': candidate.phone,
            'job_title': candidate.applied_job.title,
            'status': candidate.status,
            'similarity_score': candidate.similarity_score,
            'skills': candidate.skills,
            'education': candidate.education,
            'experience': candidate.experience,
            'created_at': candidate.created_at,
        },
        'interview': {
            'id': interview.id,
            'status': interview.status,
            'scheduled_date': interview.scheduled_date,
            'completed_date': interview.completed_date,
        } if interview else None,
    })


def debug_interview_responses(request, interview_id):
    """Debug endpoint: dump raw responses for an interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    responses = InterviewResponse.objects.filter(interview=interview).order_by('question_index')

    data = [
        {
            'id': r.id,
            'question_index': r.question_index,
            'question_text': r.question_text,
            'answer_text': r.answer_text,
            'keyword_score': r.keyword_score,
            'confidence_score': r.confidence_score,
            'transcription': r.transcription,
            'created_at': r.created_at,
        }
        for r in responses
    ]

    return JsonResponse({
        'success': True,
        'interview_id': interview.id,
        'interview_status': interview.status,
        'response_count': len(data),
        'responses': data,
    })