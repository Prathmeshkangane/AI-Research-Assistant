import google.generativeai as genai
from config import Config

from services.semantic_search import semantic_search

genai.configure(
    api_key=Config.GEMINI_API_KEY
)

model = genai.GenerativeModel(
    "gemini-2.5-flash"
)


def answer_question(question):

    papers = semantic_search(
        question,
        top_k=5
    )

    context = ""

    for paper in papers:

        context += f"""
Title: {paper.title}

Abstract:
{paper.abstract}

-------------------
"""

    prompt = f"""
You are an AI Research Assistant.

Answer the user's question using ONLY
the research paper context below.

If the answer is not found in the context,
say that the available papers do not contain
sufficient information.

Context:

{context}

Question:

{question}
"""

    response = model.generate_content(
        prompt
    )

    return response.text, papers