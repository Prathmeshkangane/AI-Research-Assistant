import google.generativeai as genai
import os
genai.configure(
    api_key = os.getenv("GEMINI_API_KEY")
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)

def summarize_paper(paper):

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

    response = model.generate_content(
        prompt
    )

    return response.text