from app import app
from models.paper import Paper
from services.faiss_recommendation import get_similar_papers_faiss

with app.app_context():

    paper = Paper.query.first()

    print("\nSelected Paper:")
    print(paper.title)

    recommendations = get_similar_papers_faiss(
        paper,
        top_k=5
    )

    print("\nRecommended Papers:\n")

    for rec in recommendations:
        print(rec.title)