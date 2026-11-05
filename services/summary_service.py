from services.llm import generate_text, FAILURE_MESSAGES

_cache = {}   # paper_id -> summary (resets on restart; move to a DB column later if you want it permanent)


def summarize_paper(paper):

    if paper.id in _cache:
        return _cache[paper.id]

    prompt = f"""
    Summarize this research paper.

    Title:
    {paper.title}

    Abstract:
    {paper.abstract}

    Give:

    1. Short Summary
    2. Key Contributions
    3. Methodology
    4. Future Scope
    """

    text = generate_text(prompt)

    if text not in FAILURE_MESSAGES:      # never cache an error message
        _cache[paper.id] = text
    return text