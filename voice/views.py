from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import logging

from .voice_analyzer import speech_to_text, analyze_voice_features, full_voice_analysis

logger = logging.getLogger('ai_recruitment')


def transcribe_api(request):
    if request.method == 'POST' and request.FILES.get('audio'):
        audio_file = request.FILES['audio']
        model = request.POST.get('model', 'base')

        # Save temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = speech_to_text(tmp_path, model)
            return JsonResponse({
                'success': True,
                'transcription': result['text'],
                'language': result['language'],
                'confidence': result['confidence']
            })
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
        finally:
            os.unlink(tmp_path)

    return JsonResponse({'success': False, 'error': 'No audio file provided'})


def analyze_voice_api(request):

    if request.method == 'POST' and request.FILES.get('audio'):
        audio_file = request.FILES['audio']

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = analyze_voice_features(tmp_path)
            return JsonResponse({
                'success': True,
                'analysis': result
            })
        except Exception as e:
            logger.error(f"Voice analysis error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
        finally:
            os.unlink(tmp_path)

    return JsonResponse({'success': False, 'error': 'No audio file provided'})


def full_analysis_api(request):
    if request.method == 'POST' and request.FILES.get('audio'):
        audio_file = request.FILES['audio']
        model = request.POST.get('model', 'base')

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp:
            for chunk in audio_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = full_voice_analysis(tmp_path, model)
            return JsonResponse({
                'success': True,
                'result': result
            })
        except Exception as e:
            logger.error(f"Full analysis error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
        finally:
            os.unlink(tmp_path)

    return JsonResponse({'success': False, 'error': 'No audio file provided'})


def voice_info(request):
    return render(request, 'voice/voice_info.html')
