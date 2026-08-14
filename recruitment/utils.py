"""
AI Recruitment System - Utilities
TF-IDF + Cosine Similarity scoring and auto-shortlisting
"""
import math
import re
from collections import Counter


def tokenize(text):
    """Simple tokenizer - extracts alphabetic words"""
    if not text:
        return []
    return re.findall(r'\b[a-zA-Z]{2,}\b', text.lower())


def compute_tf(text):
    """Compute term frequency"""
    tokens = tokenize(text)
    if not tokens:
        return {}
    token_count = Counter(tokens)
    total = len(tokens)
    return {token: count / total for token, count in token_count.items()}


def compute_idf(documents):
    """Compute inverse document frequency"""
    N = len(documents)
    if N == 0:
        return {}

    idf = {}
    tokenized_docs = [set(tokenize(doc)) for doc in documents]
    all_tokens = set()

    for tokens in tokenized_docs:
        all_tokens.update(tokens)

    for token in all_tokens:
        doc_count = sum(1 for tokens in tokenized_docs if token in tokens)
        idf[token] = math.log(N / (doc_count + 1)) + 1

    return idf


def compute_tfidf(text, idf):
    """Compute TF-IDF vector for a document"""
    tf = compute_tf(text)
    return {token: tf[token] * idf.get(token, 0) for token in tf}


def cosine_similarity(vec1, vec2):
    """Calculate cosine similarity between two vectors"""
    intersection = set(vec1.keys()) & set(vec2.keys())
    numerator = sum(vec1[x] * vec2[x] for x in intersection)

    sum1 = sum(v ** 2 for v in vec1.values())
    sum2 = sum(v ** 2 for v in vec2.values())
    denominator = math.sqrt(sum1) * math.sqrt(sum2)

    if not denominator:
        return 0.0
    return float(numerator) / denominator


def calculate_similarity_score(job, candidate):
    """
    Calculate similarity between job and candidate using TF-IDF and Cosine Similarity.
    Combines job description, title, skills, experience, education requirements
    with candidate's CV text, skills, experience, and education.
    """
    job_text = " ".join(filter(None, [
        job.title,
        job.description,
        job.required_skills,
        job.experience_required,
        job.education_required,
        job.department,
    ]))

    candidate_text = " ".join(filter(None, [
        candidate.extracted_text,
        candidate.skills,
        candidate.experience,
        candidate.education,
    ]))

    if not candidate_text.strip():
        return 0.0

    docs = [job_text, candidate_text]
    idf = compute_idf(docs)
    job_vec = compute_tfidf(job_text, idf)
    cand_vec = compute_tfidf(candidate_text, idf)

    return cosine_similarity(job_vec, cand_vec)


def auto_shortlist_candidates(job, threshold=0.01, top_n=10):
    """
    Automatically shortlist top candidates based on similarity score.
    Only candidates with 'new' or 'screening' status are considered.
    """
    from .models import Candidate

    candidates = Candidate.objects.filter(
        applied_job=job,
        status__in=['new', 'screening']
    ).order_by('-similarity_score')

    shortlisted = []
    for candidate in candidates[:top_n]:
        if candidate.similarity_score >= threshold:
            candidate.status = 'shortlisted'
            candidate.save(update_fields=['status'])
            shortlisted.append(candidate)

    return shortlisted


def recalculate_job_scores(job):
    """Recalculate similarity scores for all candidates of a job"""
    from .models import Candidate

    candidates = Candidate.objects.filter(applied_job=job)
    updated = 0

    for candidate in candidates:
        score = calculate_similarity_score(job, candidate)
        if abs(score - candidate.similarity_score) > 0.001:
            candidate.similarity_score = score
            candidate.save(update_fields=['similarity_score'])
            updated += 1

    return updated
