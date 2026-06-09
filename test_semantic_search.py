from app import app
from services.semantic_search import semantic_search

with app.app_context():

    results = semantic_search(
        "machine learning",
        top_k=5
    )

    for paper in results:
        print(paper.title)
        print("-" * 50)