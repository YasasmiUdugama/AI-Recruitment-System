

import logging

logger = logging.getLogger('ai_recruitment')


def shortlist_candidates(ranked_results, threshold=0.01, top_n=10):

    if not ranked_results:
        logger.warning("No ranked results provided for shortlisting")
        return []

    # Step 1: Filter by threshold
    shortlisted = []
    for candidate in ranked_results:
        file_name = candidate[0]
        score = candidate[1]

        if score >= threshold:
            shortlisted.append(candidate)

    # Step 2: Limit by top N (if given)
    if top_n is not None:
        original_count = len(shortlisted)
        shortlisted = shortlisted[:top_n]
        logger.info(f"Shortlisted {len(shortlisted)} out of {original_count} candidates above threshold")
    else:
        logger.info(f"Shortlisted {len(shortlisted)} candidates above threshold {threshold}")

    return shortlisted


def get_shortlist_summary(ranked_results, threshold=0.01, top_n=10):

    total = len(ranked_results)
    above_threshold = len([r for r in ranked_results if r[1] >= threshold])
    shortlisted = shortlist_candidates(ranked_results, threshold, top_n)

    return {
        'total_candidates': total,
        'above_threshold': above_threshold,
        'shortlisted_count': len(shortlisted),
        'threshold': threshold,
        'top_n': top_n,
        'selection_rate': (len(shortlisted) / total * 100) if total > 0 else 0,
        'shortlisted_ids': [s[0] for s in shortlisted],
        'highest_score': ranked_results[0][1] if ranked_results else 0,
        'lowest_shortlisted_score': shortlisted[-1][1] if shortlisted else 0,
    }


def auto_shortlist(job, candidates_queryset, threshold=0.01, top_n=10):
    """
    Automatically shortlist candidates for a job

    Parameters:
    -----------
    job : JobDescription
        The job description object
    candidates_queryset : QuerySet
        Django queryset of Candidate objects
    threshold : float
        Minimum similarity score
    top_n : int
        Maximum number to shortlist

    Returns:
    --------
    list : Shortlisted Candidate objects
    """
    from ranking.ranker import batch_rank

    job_text = f"{job.title}\n{job.description}\n{job.required_skills}"

    # Rank all candidates
    ranked = batch_rank(job_text, candidates_queryset)

    # Convert to list format for shortlister
    ranked_list = [(str(c.id), score) for c, score in ranked]

    # Shortlist
    shortlisted = shortlist_candidates(ranked_list, threshold, top_n)
    shortlisted_ids = [int(s[0]) for s in shortlisted]

    # Get candidate objects
    shortlisted_candidates = []
    for candidate, score in ranked:
        if candidate.id in shortlisted_ids:
            candidate.status = 'shortlisted'
            candidate.save()
            shortlisted_candidates.append(candidate)

    logger.info(f"Auto-shortlisted {len(shortlisted_candidates)} candidates for job: {job.title}")

    return shortlisted_candidates
