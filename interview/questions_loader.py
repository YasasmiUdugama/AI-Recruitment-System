import pandas as pd
import os
import random
from django.conf import settings


EXCEL_PATH = getattr(
    settings,
    'INTERVIEW_QUESTIONS_EXCEL',
    os.path.join(settings.BASE_DIR, 'data', 'interview_questions.xlsx')
)


_question_cache = None


def load_questions_from_excel(refresh=False):

    global _question_cache
    if _question_cache is not None and not refresh:
        return _question_cache

    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(
            f"Interview questions Excel file not found at: {EXCEL_PATH}.\n"
            f"Please place 'interview_questions.xlsx' in your project root or set INTERVIEW_QUESTIONS_EXCEL in settings.py"
        )

    df = pd.read_excel(EXCEL_PATH, engine='openpyxl')


    df.columns = [c.strip().lower().replace(' ', '_') for c in df.columns]

    questions = {}
    for _, row in df.iterrows():
        category = str(row.get('category', 'general')).strip().lower()
        question_dict = {
            'text': str(row.get('question_text', '')).strip(),
            'type': str(row.get('question_type', 'general')).strip(),
            'difficulty': str(row.get('difficulty', 'medium')).strip(),
            'keywords': [k.strip() for k in str(row.get('keywords', '')).split(',') if k.strip()],
            'time_limit': int(row.get('time_limit', 120)) if pd.notna(row.get('time_limit')) else 120,
        }

        if category not in questions:
            questions[category] = []
        questions[category].append(question_dict)

    _question_cache = questions
    return questions


def get_questions(category='general', count=5, difficulty=None):

    all_questions = load_questions_from_excel()

    # Map common aliases
    category_map = {
        'default': 'general',
        'tech': 'technical',
        'technology': 'technical',
        'coding': 'coding',
        'hr': 'hr',
        'general': 'general',
        'design': 'design',
    }
    category = category_map.get(category.lower(), category.lower())


    pool = all_questions.get(category, all_questions.get('general', []))

    if difficulty:
        pool = [q for q in pool if q['difficulty'].lower() == difficulty.lower()]

    if not pool:

        pool = all_questions.get('general', [])

    
    if count >= len(pool):
        return pool

    return random.sample(pool, count)


def get_question_by_keywords(job_skills, count=5):

    all_questions = load_questions_from_excel()
    if isinstance(job_skills, str):
        job_skills = [s.strip().lower() for s in job_skills.split(',')]

    scored_questions = []

    for category, qlist in all_questions.items():
        for q in qlist:
            score = 0
            q_keywords = [k.lower() for k in q['keywords']]
            for skill in job_skills:
                if any(skill in kw or kw in skill for kw in q_keywords):
                    score += 1
            if score > 0:
                scored_questions.append((score, q))


    scored_questions.sort(key=lambda x: x[0], reverse=True)

    selected = [q for _, q in scored_questions[:count]]

    if len(selected) < count:
        general = all_questions.get('general', [])
        remaining = count - len(selected)
        extras = [q for q in general if q not in selected]
        if extras:
            selected.extend(random.sample(extras, min(remaining, len(extras))))

    return selected


def reload_questions():

    global _question_cache
    _question_cache = None
    return load_questions_from_excel()