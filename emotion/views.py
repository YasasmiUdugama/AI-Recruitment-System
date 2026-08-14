from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import os
import logging

from .emotion_detector import (
    analyze_image_emotions, analyze_video_emotions,
    get_emotion_summary, calculate_emotion_score
)

logger = logging.getLogger('ai_recruitment')


def analyze_image_api(request):
    if request.method == 'POST' and request.FILES.get('image'):
        image_file = request.FILES['image']

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.jpg') as tmp:
            for chunk in image_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = analyze_image_emotions(tmp_path)
            result['summary'] = get_emotion_summary(result)
            result['score'] = calculate_emotion_score(result)
            return JsonResponse({
                'success': True,
                'analysis': result
            })
        except Exception as e:
            logger.error(f"Image emotion analysis error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
        finally:
            os.unlink(tmp_path)

    return JsonResponse({'success': False, 'error': 'No image provided'})


def analyze_video_api(request):
    if request.method == 'POST' and request.FILES.get('video'):
        video_file = request.FILES['video']
        interval = float(request.POST.get('interval', 1.0))

        import tempfile
        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp4') as tmp:
            for chunk in video_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = analyze_video_emotions(tmp_path, interval)
            result['summary'] = get_emotion_summary(result)
            result['score'] = calculate_emotion_score(result)
            return JsonResponse({
                'success': True,
                'analysis': result
            })
        except Exception as e:
            logger.error(f"Video emotion analysis error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
        finally:
            os.unlink(tmp_path)

    return JsonResponse({'success': False, 'error': 'No video provided'})


def emotion_info(request):
    return render(request, 'emotion/emotion_info.html')
