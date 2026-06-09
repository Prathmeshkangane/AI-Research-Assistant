from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

from models.paper import Paper

# Load once when application starts
model = SentenceTransformer("all-MiniLM-L6-v2")


def get_similar_papers(target_paper, top_k=5):

    papers = Paper.query.limit(1000).all()

    abstracts = [paper.abstract for paper in papers]

    embeddings = model.encode(abstracts)

    target_embedding = model.encode(
        [target_paper.abstract]
    )

    similarities = cosine_similarity(
        target_embedding,
        embeddings
    )[0]

    scored_papers = []

    for paper, score in zip(papers, similarities):

        if paper.id != target_paper.id:

            scored_papers.append(
                (paper, score)
            )

    scored_papers.sort(
        key=lambda x: x[1],
        reverse=True
    )

    return scored_papers[:top_k]