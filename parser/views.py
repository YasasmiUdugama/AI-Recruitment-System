from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging

from .cv_parser import parse_cv

logger = logging.getLogger('ai_recruitment')


def parse_cv_api(request):
    """API endpoint to parse a CV file"""
    if request.method == 'POST' and request.FILES.get('cv_file'):
        cv_file = request.FILES['cv_file']

        # Save temporarily
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            for chunk in cv_file.chunks():
                tmp.write(chunk)
            tmp_path = tmp.name

        try:
            result = parse_cv(tmp_path)
            return JsonResponse(result)
        except Exception as e:
            logger.error(f"CV parsing API error: {e}")
            return JsonResponse({'success': False, 'error': str(e)})
        finally:
            os.unlink(tmp_path)

    return JsonResponse({'success': False, 'error': 'No file provided'})


def parser_info(request):
    """Info page about the CV parser"""
    return render(request, 'parser/parser_info.html')
