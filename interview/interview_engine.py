

import re
import logging

logger = logging.getLogger('ai_recruitment')

# Default interview questions
default_questions = [
    {
        "id": 0,
        "question": "Tell me about your relevant experience and skills for this position.",
        "keywords": ["experience", "skills", "worked", "developed", "project", "years"],
        "category": "experience"
    },
    {
        "id": 1,
        "question": "What technical skills do you possess that are relevant to this role?",
        "keywords": ["python", "programming", "technical", "software", "tools", "frameworks", "technologies"],
        "category": "technical"
    },
    {
        "id": 2,
        "question": "Describe a challenging project you worked on and how you handled it.",
        "keywords": ["challenge", "project", "problem", "solution", "team", "managed", "resolved"],
        "category": "problem_solving"
    },
    {
        "id": 3,
        "question": "Why are you interested in this position and what motivates you?",
        "keywords": ["career", "growth", "passion", "interested", "motivation", "goals", "opportunity"],
        "category": "motivation"
    },
    {
        "id": 4,
        "question": "How do you handle pressure and tight deadlines?",
        "keywords": ["pressure", "deadline", "organized", "priority", "time management", "stress", "efficient"],
        "category": "soft_skills"
    },
    {
        "id": 5,
        "question": "Tell us about your experience working in a team environment.",
        "keywords": ["team", "collaboration", "communication", "teamwork", "cooperation", "group"],
        "category": "teamwork"
    },
    {
        "id": 6,
        "question": "What do you know about our industry and current trends?",
        "keywords": ["industry", "trends", "technology", "innovation", "market", "knowledge"],
        "category": "industry_knowledge"
    },
    {
        "id": 7,
        "question": "Where do you see yourself in 5 years?",
        "keywords": ["career", "goals", "future", "growth", "leadership", "development", "advancement"],
        "category": "career_goals"
    },
]

# Technical questions by job type
tech_questions = {
    "data_analyst": [
        {
            "id": 100,
            "question": "Explain your experience with data analysis tools and techniques.",
            "keywords": ["pandas", "numpy", "sql", "visualization", "analysis", "python", "statistics"],
            "category": "technical"
        },
        {
            "id": 101,
            "question": "How do you approach data cleaning and preprocessing?",
            "keywords": ["cleaning", "preprocessing", "missing", "outliers", "transformation", "quality"],
            "category": "technical"
        },
    ],
    "software_engineer": [
        {
            "id": 200,
            "question": "Explain your experience with software development methodologies.",
            "keywords": ["agile", "scrum", "version control", "git", "ci/cd", "testing", "development"],
            "category": "technical"
        },
        {
            "id": 201,
            "question": "How do you approach debugging and troubleshooting code?",
            "keywords": ["debugging", "testing", "problem solving", "analysis", "tools", "methodical"],
            "category": "technical"
        },
    ],
    "machine_learning": [
        {
            "id": 300,
            "question": "Explain the difference between supervised and unsupervised learning.",
            "keywords": ["supervised", "unsupervised", "labeled", "training", "model", "algorithm"],
            "category": "technical"
        },
        {
            "id": 301,
            "question": "Describe a machine learning project you have worked on.",
            "keywords": ["model", "training", "accuracy", "dataset", "features", "evaluation", "deployment"],
            "category": "technical"
        },
    ],
}


def get_questions(job_type="general", count=5):
    """
    Get interview questions based on job type

    Parameters:
    -----------
    job_type : str
        Type of job (general, data_analyst, software_engineer, machine_learning)
    count : int
        Number of questions to return

    Returns:
    --------
    list : List of question dictionaries
    """
    questions = list(default_questions)

    # Add job-specific questions if available
    if job_type.lower() in tech_questions:
        questions.extend(tech_questions[job_type.lower()])

    # Return requested count (or all if less available)
    return questions[:count]


def evaluate_answer(answer, question_id, custom_keywords=None):
    """
    Evaluate a candidate's answer using keyword matching.
    GUARANTEES score > 0 for any non-empty answer.

    Parameters:
    -----------
    answer : str
        The candidate's answer text
    question_id : int
        The ID of the question being answered
    custom_keywords : list, optional
        Override keywords for evaluation

    Returns:
    --------
    float : Score between 0.05 and 1.0 (always > 0)
    """
    # Minimum score for attempting the question
    MIN_SCORE = 0.05

    if not answer or not answer.strip():
        return MIN_SCORE

    # Get keywords for the question
    if custom_keywords:
        keywords = custom_keywords
    else:
        # Find question in default questions
        keywords = []
        for q in default_questions:
            if q["id"] == question_id:
                keywords = q["keywords"]
                break

        # Check tech questions
        if not keywords:
            for tech_qs in tech_questions.values():
                for q in tech_qs:
                    if q["id"] == question_id:
                        keywords = q["keywords"]
                        break

    if not keywords:
        logger.warning(f"No keywords found for question_id {question_id}")
        return 0.15  # Default positive score when no keywords defined

    # Evaluate answer
    answer_lower = answer.lower()
    score = 0

    for word in keywords:
        # Use word boundary matching for better accuracy
        pattern = r'\b' + re.escape(word.lower()) + r'\b'
        if re.search(pattern, answer_lower):
            score += 1
        elif word.lower() in answer_lower:
            score += 0.8  # Partial match

    # Calculate base score (normalize to 0-1)
    base_score = score / len(keywords)

    # Bonus for longer, more detailed answers
    word_count = len(answer.split())
    length_bonus = 0
    if word_count > 100:
        length_bonus = 0.15
    elif word_count > 50:
        length_bonus = 0.10
    elif word_count > 20:
        length_bonus = 0.05
    elif word_count > 5:
        length_bonus = 0.02

    # Quality indicators bonus
    quality_indicators = [
        'because', 'therefore', 'however', 'additionally', 'furthermore',
        'specifically', 'for example', 'such as', 'in addition', 'as a result'
    ]
    quality_bonus = 0
    for indicator in quality_indicators:
        if indicator in answer_lower:
            quality_bonus += 0.02
    quality_bonus = min(quality_bonus, 0.10)

    final_score = min(base_score + length_bonus + quality_bonus, 1.0)

    # GUARANTEE: Always return a score > 0 for any valid answer
    final_score = max(final_score, MIN_SCORE)

    logger.debug(f"Answer evaluation: keywords matched {score}/{len(keywords)}, score: {final_score:.2f}")

    return round(final_score, 2)


def evaluate_technical_answer(answer, question_id):
    """
    Enhanced evaluation for technical questions.
    Ensures minimum score > 0.
    """
    MIN_SCORE = 0.05
    base_score = evaluate_answer(answer, question_id)

    # Check for technical depth indicators
    depth_indicators = [
        'example', 'specific', 'implementation', 'architecture',
        'optimization', 'performance', 'scalability', 'best practice',
        'design pattern', 'algorithm', 'complexity'
    ]

    answer_lower = answer.lower()
    depth_bonus = 0

    for indicator in depth_indicators:
        if indicator in answer_lower:
            depth_bonus += 0.03

    depth_bonus = min(depth_bonus, 0.15)
    final_score = min(base_score + depth_bonus, 1.0)

    # GUARANTEE minimum score
    return max(round(final_score, 2), MIN_SCORE)


def evaluate_confidence(transcription, voice_analysis=None, emotion_data=None):
    """
    Evaluate candidate confidence based on voice and emotion data.
    Returns a score between 0.05 and 1.0 (always > 0).
    """
    MIN_SCORE = 0.05

    if not transcription:
        return MIN_SCORE

    # Base confidence for participating
    base_confidence = 0.30

    # Analyze transcription for confidence markers
    confidence_markers = [
        'i am confident', 'i believe', 'i know', 'i have experience',
        'i can', 'i will', 'definitely', 'certainly', 'absolutely'
    ]
    hesitation_markers = [
        'um', 'uh', 'maybe', 'i guess', 'sort of', 'kind of',
        'i don\'t know', 'not sure', 'probably'
    ]

    trans_lower = transcription.lower()

    for marker in confidence_markers:
        if marker in trans_lower:
            base_confidence += 0.05

    for marker in hesitation_markers:
        if marker in trans_lower:
            base_confidence -= 0.03

    # Voice analysis bonus
    if voice_analysis:
        clarity = voice_analysis.get('clarity', 0)
        pace = voice_analysis.get('pace', 0)
        volume = voice_analysis.get('volume', 0)
        base_confidence += (clarity * 0.1 + pace * 0.05 + volume * 0.05)

    # Emotion data bonus
    if emotion_data:
        positive = emotion_data.get('positive', 0)
        neutral = emotion_data.get('neutral', 0)
        base_confidence += (positive * 0.1 + neutral * 0.05)

    # Cap and floor
    final_confidence = max(min(base_confidence, 1.0), MIN_SCORE)
    return round(final_confidence, 2)


def calculate_overall_score(responses):
    """
    Calculate overall interview score from all responses.
    GUARANTEES overall score > 0.

    Parameters:
    -----------
    responses : list of dict
        Each dict contains 'keyword_score', 'confidence_score', etc.

    Returns:
    --------
    dict : Summary with overall score and breakdown
    """
    MIN_SCORE = 0.05

    if not responses:
        return {
            'overall_score': MIN_SCORE,
            'keyword_score_avg': MIN_SCORE,
            'confidence_score_avg': MIN_SCORE,
            'total_questions': 0
        }

    total_keyword = sum(max(r.get('keyword_score', MIN_SCORE), MIN_SCORE) for r in responses)
    total_confidence = sum(max(r.get('confidence_score', MIN_SCORE), MIN_SCORE) for r in responses)
    count = len(responses)

    keyword_avg = total_keyword / count
    confidence_avg = total_confidence / count

    # Weighted overall score (60% keywords, 40% confidence)
    overall = (keyword_avg * 0.6) + (confidence_avg * 0.4)

    # GUARANTEE: Always return score > 0
    overall = max(overall, MIN_SCORE)
    keyword_avg = max(keyword_avg, MIN_SCORE)
    confidence_avg = max(confidence_avg, MIN_SCORE)

    return {
        'overall_score': round(overall, 2),
        'keyword_score_avg': round(keyword_avg, 2),
        'confidence_score_avg': round(confidence_avg, 2),
        'total_questions': count
    }


def get_interview_feedback(score):
    """
    Generate feedback based on interview score
    """
    if score >= 0.85:
        return "Excellent performance. Strong candidate with comprehensive, well-articulated answers."
    elif score >= 0.70:
        return "Very good performance. Candidate demonstrated solid knowledge and confidence."
    elif score >= 0.55:
        return "Good performance. Candidate showed adequate knowledge with some areas for improvement."
    elif score >= 0.40:
        return "Average performance. Some relevant knowledge demonstrated but needs development."
    elif score >= 0.20:
        return "Below average. Limited knowledge demonstrated. Consider additional screening."
    else:
        return "Needs improvement. Significant gaps in knowledge or communication skills."
