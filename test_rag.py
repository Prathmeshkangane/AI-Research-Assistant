from app import app
from services.rag_service import answer_question

with app.app_context():

    question = input("Question: ")

    answer, papers = answer_question(question)

    print("\nANSWER:\n")
    print(answer)

    print("\nRETRIEVED PAPERS:\n")

    for i, paper in enumerate(papers, start=1):
        print(f"{i}. {paper.title}")