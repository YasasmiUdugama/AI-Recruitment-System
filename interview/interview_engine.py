import logging
from .questions_loader import get_questions, get_question_by_keywords

logger = logging.getLogger('ai_recruitment')


def generate_interview_questions(candidate, count=5):
    """
    Generate interview questions for a candidate based on their job/skills.
    Replaces old default_questions and tech_questions logic.
    """
    job = candidate.applied_job
    required_skills = getattr(job, 'required_skills', '')
    job_title = job.title.lower() if job.title else ''

    # Determine category based on job title
    category = 'general'
    if any(word in job_title for word in ['developer', 'engineer', 'programmer', 'software', 'tech', 'python', 'java', 'web']):
        category = 'technical'
    elif any(word in job_title for word in ['designer', 'ui', 'ux', 'graphic']):
        category = 'design'
    elif 'hr' in job_title or 'human resource' in job_title:
        category = 'hr'
    elif any(word in job_title for word in ['data', 'analyst', 'scientist']):
        category = 'technical'

    # Try skill-based smart selection first
    if required_skills:
        try:
            questions = get_question_by_keywords(required_skills, count=count)
        except Exception as e:
            logger.warning(f"Skill-based question selection failed: {e}")
            questions = get_questions(category=category, count=count)
    else:
        questions = get_questions(category=category, count=count)

    # Format for the interview portal
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

    logger.info(f"Generated {len(formatted)} questions for candidate {candidate.full_name} (category: {category})")
    return formatted


def evaluate_answer(answer_text, question):

    if not answer_text or not question:
        return 0.0

    answer_lower = answer_text.lower()
    keywords = question.get('keywords', [])

    if not keywords:
        return 0.5 

    matched = sum(1 for kw in keywords if kw.lower() in answer_lower)
    score = matched / len(keywords)

    # Boost score slightly for longer, relevant answers
    word_count = len(answer_text.split())
    if word_count > 20 and score > 0:
        score = min(1.0, score + 0.1)

    logger.debug(f"Answer evaluation: {matched}/{len(keywords)} keywords matched, score={score:.2f}")
    return round(score, 2)