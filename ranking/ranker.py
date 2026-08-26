

import re
import logging
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

logger = logging.getLogger('ai_recruitment')


def preprocess_text(text):
    """Clean and preprocess text for better TF-IDF results"""
    if not text:
        return ""

    # Convert to lowercase
    text = text.lower()

    # Remove special characters but keep spaces
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', text)

    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text).strip()

    return text


def rank_cvs(job_description, cv_texts):

    if not job_description or not cv_texts:
        logger.warning("Empty job description or CV texts provided")
        return []

    # Preprocess job description
    processed_job = preprocess_text(job_description)

    # Preprocess CV texts and filter out empty ones
    processed_cvs = {}
    for cv_id, cv_text in cv_texts.items():
        processed = preprocess_text(cv_text)
        if processed:
            processed_cvs[cv_id] = processed

    if not processed_cvs:
        logger.warning("No valid CV texts after preprocessing")
        return []


    documents = [processed_job] + list(processed_cvs.values())

    try:

        vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=5000,
            ngram_range=(1, 2),  # Use unigrams and bigrams
            min_df=1,
            max_df=1.0
        )

        tfidf_matrix = vectorizer.fit_transform(documents)

        similarity_scores = cosine_similarity(
            tfidf_matrix[0:1],
            tfidf_matrix[1:]
        ).flatten()


        results = []
        cv_ids = list(processed_cvs.keys())

        for i, cv_id in enumerate(cv_ids):
            score = float(similarity_scores[i])
            results.append((cv_id, score))


        results.sort(key=lambda x: x[1], reverse=True)

        logger.info(f"Ranked {len(results)} CVs against job description")
        logger.info(f"Top score: {results[0][1]:.4f}" if results else "No results")

        return results

    except Exception as e:
        logger.error(f"Error in CV ranking: {e}")
        return []


def get_top_keywords(job_description, cv_text, n_keywords=10):
    """
    Extract top matching keywords between job description and a CV
    """
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        documents = [preprocess_text(job_description), preprocess_text(cv_text)]

        vectorizer = TfidfVectorizer(
            stop_words='english',
            max_features=1000,
            ngram_range=(1, 2),
            max_df=1.0 
        )

        tfidf_matrix = vectorizer.fit_transform(documents)
        feature_names = vectorizer.get_feature_names_out()

        # Get top features for the CV (index 1)
        scores = tfidf_matrix[1].toarray().flatten()
        top_indices = scores.argsort()[-n_keywords:][::-1]

        keywords = [(feature_names[i], float(scores[i])) for i in top_indices if scores[i] > 0]

        return keywords

    except Exception as e:
        logger.error(f"Error extracting keywords: {e}")
        return []


def batch_rank(job_description, candidates_queryset):

    cv_texts = {}
    candidate_map = {}

    for candidate in candidates_queryset:
        if candidate.cv_text:
            cv_texts[str(candidate.id)] = candidate.cv_text
            candidate_map[str(candidate.id)] = candidate

    ranked = rank_cvs(job_description, cv_texts)

    results = []
    for candidate_id, score in ranked:
        if candidate_id in candidate_map:
            results.append((candidate_map[candidate_id], score))

    return results
