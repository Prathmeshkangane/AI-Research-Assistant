from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from app import app
from models.paper import Paper

model = SentenceTransformer("all-MiniLM-L6-v2")

with app.app_context():

    papers = Paper.query.limit(5).all()

    abstracts = [paper.abstract for paper in papers]

    embeddings = model.encode(abstracts)

    similarity_matrix = cosine_similarity(embeddings)

    print("\nPapers:\n")

    for i, paper in enumerate(papers):
        print(f"{i}: {paper.title[:80]}")

    print("\nMost Similar Pairs:\n")

    for i in range(len(papers)):
        for j in range(i + 1, len(papers)):

            print(
                f"Paper {i} ↔ Paper {j} : "
                f"{similarity_matrix[i][j]:.4f}"
            )