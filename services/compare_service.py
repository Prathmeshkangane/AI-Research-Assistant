from services.llm import generate_text


def compare_papers(paper1, paper2):

    prompt = f"""
    Compare these research papers using only the abstracts below.

    Paper 1:
    Title:
    {paper1.title}

    Abstract:
    {paper1.abstract}

    Paper 2:
    Title:
    {paper2.title}

    Abstract:
    {paper2.abstract}

    Provide:

    1. Similarities
    2. Differences
    3. Methodologies
    4. Strengths and limitations of each (state that this is based on abstracts only)
    """

    return generate_text(prompt)