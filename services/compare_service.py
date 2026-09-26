import google.generativeai as genai
import os

genai.configure(
    api_key=os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)

def compare_papers(
    paper1,
    paper2
):

    prompt = f"""
    Compare these research papers.

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
    4. Which paper appears stronger
    """

    response = model.generate_content(
        prompt
    )

    return response.text