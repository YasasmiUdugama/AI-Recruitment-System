
import logging
import json
import os
import tempfile

from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Avg, Count, Q
from django.core.files.storage import default_storage

from core.models import Interview, InterviewResponse, InterviewEvaluation, Candidate, JobDescription
from .interview_engine import generate_interview_questions, evaluate_answer
from .questions_loader import get_questions, get_question_by_keywords

from voice.voice_analyzer import full_voice_analysis
from emotion.emotion_detector import analyze_video_emotions
from emotion.proctor_detector import analyze_video_proctoring

logger = logging.getLogger('ai_recruitment')


def get_or_create_interview_questions(interview):
    """
    Return this interview's cached question set (text + keywords), generating
    and storing it on first access via Interview.questions_json. This is the
    single source of truth both the portal template and submit_answer_api
    read from, so scoring can't be forged by whatever the client posts.
    """
    if interview.questions_json:
        return interview.questions_json

    questions = generate_interview_questions(interview.candidate, count=5)
    interview.questions_json = questions
    interview.save(update_fields=['questions_json'])
    return questions


# ============ CANDIDATE-FACING APIs ============

def interview_questions_api(request, job_type):
    """Get interview questions by job type (e.g., /interview/questions/technical/)"""
    count = int(request.GET.get('count', 5))
    difficulty = request.GET.get('difficulty', None)

    try:
        questions = get_questions(category=job_type, count=count, difficulty=difficulty)
    except Exception as e:
        logger.error(f"Error loading questions for {job_type}: {e}")
        questions = get_questions(category='general', count=count)

    formatted = []
    for i, q in enumerate(questions, 1):
        formatted.append({
            'index': i,
            'text': q['text'],
            'type': q['type'],
            'difficulty': q['difficulty'],
            'keywords': q['keywords'],
            'time_limit': q['time_limit'],
        })

    return JsonResponse({
        'success': True,
        'job_type': job_type,
        'count': len(formatted),
        'questions': formatted,
    })


@csrf_exempt
def evaluate_answer_api(request):
    """Evaluate a single answer against question keywords"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    answer_text = data.get('answer_text', '')
    question = data.get('question', {})

    score = evaluate_answer(answer_text, question)

    return JsonResponse({
        'success': True,
        'keyword_score': score,
        'max_score': 1.0,
    })


@csrf_exempt
def save_response_api(request):
    """Save an interview response (kept for direct/manual use, e.g. HR tools)"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    interview_id = data.get('interview_id')
    question_data = data.get('question', {})
    answer_text = data.get('answer_text', '')
    confidence_score = data.get('confidence_score', 0.0)
    emotion_data = data.get('emotion_data', {})
    voice_analysis = data.get('voice_analysis', {})

    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)

    keyword_score = evaluate_answer(answer_text, question_data)

    response = InterviewResponse.objects.create(
        interview=interview,
        question_index=question_data.get('index', 0),
        question_text=question_data.get('text', ''),
        answer_text=answer_text,
        keyword_score=keyword_score,
        confidence_score=confidence_score,
        emotion_data=emotion_data,
        voice_analysis=voice_analysis,
    )

    return JsonResponse({
        'success': True,
        'response_id': response.id,
        'keyword_score': keyword_score,
    })


@csrf_exempt
def submit_answer_api(request):
    """
    Consolidated per-question submission — handles the SHORT audio clip the
    candidate records for a single answer (transcription + keyword scoring +
    voice confidence). It does NOT handle video anymore: emotion and
    proctoring (phone/notes/multiple-people) analysis now run ONCE, over the
    full continuous interview recording, in complete_interview_api — see that
    function's docstring for why (this is what closes the "pause recording
    between questions to check a phone" gap).

    Expects multipart/form-data: interview_id, question_index, question_text, audio (file)
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    interview_id = request.POST.get('interview_id')
    question_index = request.POST.get('question_index')
    question_text = request.POST.get('question_text', '')
    audio_file = request.FILES.get('audio')

    if not interview_id or question_index is None:
        return JsonResponse({'success': False, 'error': 'interview_id and question_index required'}, status=400)

    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Interview not found'}, status=404)

    answer_text = ''
    voice_features = {}
    confidence_score = 0.0
    q_pos = None
    try:
        q_pos = int(question_index)
    except (TypeError, ValueError):
        pass

    # ---- Audio: transcription + voice confidence ----
    if audio_file:
        suffix = os.path.splitext(audio_file.name)[1] or '.webm'
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            audio_path = tmp.name
        try:
            voice_result = full_voice_analysis(audio_path)
            answer_text = voice_result.get('transcription', {}).get('text', '').strip()
            voice_features = voice_result.get('voice_features', {})
            confidence_score = voice_features.get('confidence_score', 0.0)
        except Exception as e:
            logger.error(f"Voice analysis failed for interview {interview_id} q{question_index}: {e}")
        finally:
            os.unlink(audio_path)

    # ---- Keyword scoring ----
    # Look up keywords from the interview's server-generated question set
    # (Interview.questions_json), never from client-supplied text — the
    # candidate's browser can't be trusted to report its own keywords.
    stored_questions = get_or_create_interview_questions(interview)
    stored_question = None
    if q_pos is not None and 0 <= q_pos < len(stored_questions):
        stored_question = stored_questions[q_pos]

    keywords = stored_question.get('keywords', []) if stored_question else []
    # Prefer the server's own question text for the saved record too, falling
    # back to whatever the client sent if lookup failed for some reason.
    resolved_question_text = stored_question.get('text', question_text) if stored_question else question_text

    keyword_score = evaluate_answer(answer_text, {'keywords': keywords}) if keywords else 0.5

    response = InterviewResponse.objects.create(
        interview=interview,
        question_index=q_pos if q_pos is not None else 0,
        question_text=resolved_question_text,
        answer_text=answer_text,
        transcription=answer_text,
        keyword_score=keyword_score,
        confidence_score=confidence_score,
        voice_analysis=voice_features,
    )

    if audio_file:
        audio_file.seek(0)
        response.audio_file = audio_file
        response.save()

    return JsonResponse({
        'success': True,
        'response_id': response.id,
        'transcription': answer_text,
        'keyword_score': keyword_score,
        'confidence_score': confidence_score,
    })


@csrf_exempt
def upload_video_api(request):
    """Upload video file for an already-created interview response (manual/HR use)."""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    response_id = request.POST.get('response_id')
    video_file = request.FILES.get('video')

    if not response_id or not video_file:
        return JsonResponse({'error': 'response_id and video file required'}, status=400)

    try:
        response = InterviewResponse.objects.get(id=response_id)
    except InterviewResponse.DoesNotExist:
        return JsonResponse({'error': 'Response not found'}, status=404)

    response.video_file = video_file
    response.save()

    return JsonResponse({
        'success': True,
        'message': 'Video uploaded successfully',
        'video_url': response.video_file.url if response.video_file else None,
    })


@csrf_exempt
def complete_interview_api(request):
    """
    Complete an interview: analyze the ONE continuous recording that spans
    start-to-finish (uploaded here as multipart 'video'), aggregate the
    per-question keyword/voice scores already saved via submit_answer_api,
    and produce the final evaluation.

    Analyzing a single full-length recording — instead of separate per-
    question clips — is deliberate: the camera/mic never stop between
    questions, so there's no window where a candidate could pause recording
    to check a phone or notes unobserved. See interview_portal.html's
    sessionRecorder / finalizeInterviewSubmission() for the capture side.

    Expects multipart/form-data: interview_id, video (file — optional but
    strongly recommended; without it, proctoring/emotion analysis is skipped
    and only keyword/voice scores are used).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    interview_id = request.POST.get('interview_id')
    video_file = request.FILES.get('video')

    if not interview_id:
        # Backward-compat: also accept a plain JSON body with interview_id
        try:
            data = json.loads(request.body or b'{}')
            interview_id = data.get('interview_id')
        except json.JSONDecodeError:
            pass

    if not interview_id:
        return JsonResponse({'error': 'interview_id required'}, status=400)

    try:
        interview = Interview.objects.get(id=interview_id)
    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)

    responses = InterviewResponse.objects.filter(interview=interview)

    if not responses.exists():
        return JsonResponse({'error': 'No responses found'}, status=400)

    avg_keyword = responses.aggregate(avg=Avg('keyword_score'))['avg'] or 0
    avg_confidence = responses.aggregate(avg=Avg('confidence_score'))['avg'] or 0

    # ---- Full-session video analysis: facial emotion + proctoring ----
    facial_summary = {}
    proctoring_summary = {'flags': [], 'clean': True}

    if video_file:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as tmp:
            for chunk in video_file.chunks():
                tmp.write(chunk)
            video_path = tmp.name
        try:
            # Sample every 2s across the WHOLE interview. That's enough
            # resolution to catch a sustained glance at a phone/notes without
            # having to decode every single frame of a multi-minute clip.
            facial_summary = analyze_video_emotions(video_path, sample_interval=2.0)
            proctoring_summary = analyze_video_proctoring(video_path, sample_interval=2.0)
        except Exception as e:
            logger.error(f"Full-session video analysis failed for interview {interview_id}: {e}")
        finally:
            os.unlink(video_path)

        # Persist the raw full-interview recording for HR review.
        video_file.seek(0)
        interview.full_recording = video_file
        interview.save(update_fields=['full_recording'])
    else:
        logger.warning(f"complete_interview_api called for interview {interview_id} with no video attached")

    unique_flags = sorted(set(proctoring_summary.get('flags', [])))
    flagged_for_review = len(unique_flags) > 0

    # Voice signal summary still comes from the per-question audio clips
    # saved by submit_answer_api (transcription/confidence is inherently a
    # per-answer thing, unlike proctoring which needs the whole timeline).
    voice_confidences = []
    pitches = []
    for r in responses:
        va = r.voice_analysis if isinstance(r.voice_analysis, dict) else {}
        if va.get('confidence_score') is not None:
            voice_confidences.append(va['confidence_score'])
        if va.get('pitch') is not None:
            pitches.append(va['pitch'])

    emotion_analysis_summary = {
        'dominant_emotion': facial_summary.get('dominant_emotion'),
        'emotion_distribution': facial_summary.get('emotion_distribution'),
        'positive_ratio': facial_summary.get('positive_ratio'),
        'frames_analyzed': facial_summary.get('total_frames_analyzed'),
        'proctoring': proctoring_summary,
    }
    voice_analysis_summary = {
        'avg_confidence': round(sum(voice_confidences) / len(voice_confidences), 3) if voice_confidences else None,
        'avg_pitch': round(sum(pitches) / len(pitches), 2) if pitches else None,
    }

    overall = (avg_keyword + avg_confidence) / 2 if avg_confidence else avg_keyword
    recommendation = 'recommended' if (overall >= 0.6 and not flagged_for_review) else 'not_recommended'
    notes = f"Proctoring flags raised: {', '.join(unique_flags)}" if unique_flags else ''

    evaluation, created = InterviewEvaluation.objects.update_or_create(
        interview=interview,
        defaults={
            'overall_score': overall,
            'keyword_score_avg': avg_keyword,
            'confidence_score_avg': avg_confidence,
            'emotion_analysis': emotion_analysis_summary,
            'voice_analysis_summary': voice_analysis_summary,
            'recommendation': recommendation,
            'notes': notes,
        }
    )

    interview.status = 'completed'
    interview.completed_date = timezone.now()
    interview.save()

    candidate = interview.candidate
    candidate.status = 'interview_completed'
    candidate.save()

    # NOTE: overall_score/keyword_score_avg/confidence_score_avg are stored
    # on InterviewEvaluation as 0-1 fractions (unchanged from before), but the
    # portal template displays them as "xx/100" and color-codes at 60/30 —
    # so the response below scales them to 0-100 for display. This also fixes
    # a pre-existing bug: the old response never actually included a nested
    # "evaluation" object, which is what interview_portal.html reads — it was
    # silently always falling through to the debug-info branch.
    return JsonResponse({
        'success': True,
        'proctoring_flags': unique_flags,
        'total_responses': responses.count(),
        'evaluation': {
            'overall_score': round(overall * 100, 1),
            'keyword_score_avg': round(avg_keyword * 100, 1),
            'confidence_score_avg': round(avg_confidence * 100, 1),
            'recommendation': evaluation.recommendation,
        },
    })


def interview_portal_questions_api(request):
    """
    Returns this interview's real, server-generated question set (by token),
    for the portal page to render instead of the old hardcoded 5-question JS
    array. Add a route for this in urls.py, e.g.:
        path('portal-questions/', views.interview_portal_questions_api, name='interview_portal_questions'),
    and, ideally, call get_or_create_interview_questions(interview) directly
    from whatever view renders interview_portal.html so the questions are
    embedded server-side at page load instead of fetched after — this
    endpoint is provided as a drop-in option if that's not convenient.
    """
    token = request.GET.get('token')
    if not token:
        return JsonResponse({'success': False, 'error': 'token required'}, status=400)

    try:
        interview = Interview.objects.get(access_token=token)
    except Interview.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Interview not found'}, status=404)

    questions = get_or_create_interview_questions(interview)
    return JsonResponse({'success': True, 'interview_id': interview.id, 'questions': questions})


def interview_info(request):
    """Get interview info by token"""
    token = request.GET.get('token')
    if not token:
        return JsonResponse({'error': 'token required'}, status=400)

    try:
        interview = Interview.objects.get(access_token=token)
    except Interview.DoesNotExist:
        return JsonResponse({'error': 'Interview not found'}, status=404)

    candidate = interview.candidate
    job = candidate.applied_job

    return JsonResponse({
        'success': True,
        'interview': {
            'id': interview.id,
            'status': interview.status,
            'scheduled_date': interview.scheduled_date.isoformat() if interview.scheduled_date else None,
            'expires_at': interview.expires_at.isoformat() if interview.expires_at else None,
            'is_expired': interview.expires_at and interview.expires_at < timezone.now(),
        },
        'candidate': {
            'id': candidate.id,
            'name': candidate.full_name,
            'email': candidate.email,
        },
        'job': {
            'id': job.id,
            'title': job.title,
            'department': job.department,
        },
    })


# ============ HR PARTNER APIs ============

def hr_dashboard_api(request):
    """HR dashboard statistics"""
    total_interviews = Interview.objects.count()
    completed = Interview.objects.filter(status='completed').count()
    in_progress = Interview.objects.filter(status='in_progress').count()
    scheduled = Interview.objects.filter(status='scheduled').count()
    pending = Interview.objects.filter(status='pending').count()

    recent_evaluations = InterviewEvaluation.objects.select_related('interview__candidate').order_by('-created_at')[:5]

    eval_data = []
    for ev in recent_evaluations:
        eval_data.append({
            'candidate_name': ev.interview.candidate.full_name,
            'job_title': ev.interview.candidate.applied_job.title,
            'overall_score': ev.overall_score,
            'recommendation': ev.recommendation,
            'date': ev.created_at.isoformat(),
        })

    return JsonResponse({
        'success': True,
        'stats': {
            'total_interviews': total_interviews,
            'completed': completed,
            'in_progress': in_progress,
            'scheduled': scheduled,
            'pending': pending,
        },
        'recent_evaluations': eval_data,
    })


def interview_list_api(request):
    """List all interviews"""
    status_filter = request.GET.get('status')
    interviews = Interview.objects.select_related('candidate', 'candidate__applied_job').all()

    if status_filter:
        interviews = interviews.filter(status=status_filter)

    data = []
    for iv in interviews:
        data.append({
            'id': iv.id,
            'candidate_name': iv.candidate.full_name,
            'job_title': iv.candidate.applied_job.title,
            'status': iv.status,
            'scheduled_date': iv.scheduled_date.isoformat() if iv.scheduled_date else None,
            'completed_date': iv.completed_date.isoformat() if iv.completed_date else None,
            'has_evaluation': hasattr(iv, 'evaluation'),
        })

    return JsonResponse({'success': True, 'interviews': data})


def interview_detail_api(request, interview_id):
    """Get interview detail"""
    interview = get_object_or_404(Interview, id=interview_id)
    candidate = interview.candidate
    responses = InterviewResponse.objects.filter(interview=interview).order_by('question_index')

    response_data = []
    for r in responses:
        response_data.append({
            'question_index': r.question_index,
            'question_text': r.question_text,
            'answer_text': r.answer_text,
            'keyword_score': r.keyword_score,
            'confidence_score': r.confidence_score,
            'has_audio': bool(r.audio_file),
            'created_at': r.created_at.isoformat(),
        })

    evaluation_data = None
    if hasattr(interview, 'evaluation'):
        ev = interview.evaluation
        emotion_analysis = ev.emotion_analysis if isinstance(ev.emotion_analysis, dict) else {}
        evaluation_data = {
            'overall_score': ev.overall_score,
            'keyword_score_avg': ev.keyword_score_avg,
            'confidence_score_avg': ev.confidence_score_avg,
            'recommendation': ev.recommendation,
            'notes': ev.notes,
            'dominant_emotion': emotion_analysis.get('dominant_emotion'),
            'proctoring_flags': emotion_analysis.get('proctoring', {}).get('flags', []),
            'created_at': ev.created_at.isoformat(),
        }

    return JsonResponse({
        'success': True,
        'interview': {
            'id': interview.id,
            'status': interview.status,
            'access_token': str(interview.access_token),
            'scheduled_date': interview.scheduled_date.isoformat() if interview.scheduled_date else None,
            'completed_date': interview.completed_date.isoformat() if interview.completed_date else None,
            'expires_at': interview.expires_at.isoformat() if interview.expires_at else None,
            # The single continuous recording covering the whole interview —
            # this is what emotion/proctoring analysis actually ran on.
            'full_recording_url': interview.full_recording.url if interview.full_recording else None,
        },
        'candidate': {
            'id': candidate.id,
            'name': candidate.full_name,
            'email': candidate.email,
            'phone': candidate.phone,
            'skills': candidate.skills,
        },
        'job': {
            'title': candidate.applied_job.title,
            'department': candidate.applied_job.department,
        },
        'responses': response_data,
        'evaluation': evaluation_data,
    })


def evaluation_report_api(request, interview_id):
    """Get evaluation report for an interview"""
    interview = get_object_or_404(Interview, id=interview_id)

    try:
        evaluation = interview.evaluation
    except InterviewEvaluation.DoesNotExist:
        return JsonResponse({'error': 'Evaluation not found'}, status=404)

    responses = InterviewResponse.objects.filter(interview=interview).order_by('question_index')

    question_scores = []
    for r in responses:
        question_scores.append({
            'question': r.question_text,
            'keyword_score': r.keyword_score,
            'confidence_score': r.confidence_score,
        })

    emotion_analysis = evaluation.emotion_analysis if isinstance(evaluation.emotion_analysis, dict) else {}

    return JsonResponse({
        'success': True,
        'candidate_name': interview.candidate.full_name,
        'job_title': interview.candidate.applied_job.title,
        'overall_score': evaluation.overall_score,
        'keyword_score_avg': evaluation.keyword_score_avg,
        'confidence_score_avg': evaluation.confidence_score_avg,
        'recommendation': evaluation.recommendation,
        'notes': evaluation.notes,
        'dominant_emotion': emotion_analysis.get('dominant_emotion'),
        'proctoring_flags': emotion_analysis.get('proctoring', {}).get('flags', []),
        'full_recording_url': interview.full_recording.url if interview.full_recording else None,
        'question_breakdown': question_scores,
        'generated_at': evaluation.created_at.isoformat(),
    })


def candidate_list_api(request):
    """List all candidates"""
    status_filter = request.GET.get('status')
    job_filter = request.GET.get('job')

    candidates = Candidate.objects.select_related('applied_job').all()

    if status_filter:
        candidates = candidates.filter(status=status_filter)
    if job_filter:
        candidates = candidates.filter(applied_job_id=job_filter)

    data = []
    for c in candidates:
        data.append({
            'id': c.id,
            'name': c.full_name,
            'email': c.email,
            'phone': c.phone,
            'status': c.status,
            'similarity_score': c.similarity_score,
            'job_title': c.applied_job.title,
            'has_interview': hasattr(c, 'interview'),
        })

    return JsonResponse({'success': True, 'candidates': data})


def candidate_detail_api(request, candidate_id):
    """Get candidate detail"""
    candidate = get_object_or_404(Candidate, id=candidate_id)

    interview_data = None
    if hasattr(candidate, 'interview'):
        iv = candidate.interview
        interview_data = {
            'id': iv.id,
            'status': iv.status,
            'scheduled_date': iv.scheduled_date.isoformat() if iv.scheduled_date else None,
        }

    return JsonResponse({
        'success': True,
        'candidate': {
            'id': candidate.id,
            'first_name': candidate.first_name,
            'last_name': candidate.last_name,
            'full_name': candidate.full_name,
            'email': candidate.email,
            'phone': candidate.phone,
            'skills': candidate.skills,
            'education': candidate.education,
            'experience': candidate.experience,
            'status': candidate.status,
            'similarity_score': candidate.similarity_score,
            'created_at': candidate.created_at.isoformat(),
        },
        'job': {
            'id': candidate.applied_job.id,
            'title': candidate.applied_job.title,
            'department': candidate.applied_job.department,
        },
        'interview': interview_data,
    })


# ============ DEBUG ============

def debug_interview_responses(request, interview_id):
    """Debug: view all responses for an interview"""
    interview = get_object_or_404(Interview, id=interview_id)
    responses = InterviewResponse.objects.filter(interview=interview).order_by('question_index')

    data = []
    for r in responses:
        data.append({
            'id': r.id,
            'question_index': r.question_index,
            'question_text': r.question_text,
            'answer_text': r.answer_text[:200] + '...' if len(r.answer_text) > 200 else r.answer_text,
            'keyword_score': r.keyword_score,
            'confidence_score': r.confidence_score,
            'emotion_data': r.emotion_data,
            'has_audio': bool(r.audio_file),
            'has_video': bool(r.video_file),
            'created_at': r.created_at.isoformat(),
        })

    return JsonResponse({
        'success': True,
        'interview_id': interview_id,
        'candidate': interview.candidate.full_name,
        'total_responses': len(data),
        'responses': data,
    })