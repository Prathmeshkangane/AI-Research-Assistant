import pickle
import faiss
import numpy as np

from models.paper import Paper

# Load once at startup
index = faiss.read_index(
    "embeddings/papers.index"
)

embeddings = np.load(
    "embeddings/paper_embeddings.npy"
)

with open(
    "embeddings/paper_ids.pkl",
    "rb"
) as f:
    paper_ids = pickle.load(f)


def get_similar_papers_faiss(
    target_paper,
    top_k=5
):

    try:
        idx = paper_ids.index(
            target_paper.id
        )
    except ValueError:
        return []

    query_vector = embeddings[idx]

    query_vector = np.array(
        [query_vector],
        dtype="float32"
    )

    distances, indices = index.search(
        query_vector,
        top_k + 1
    )

    recommendations = []

    for i in indices[0]:

        if paper_ids[i] == target_paper.id:
            continue

        paper = Paper.query.get(
            paper_ids[i]
        )

        if paper:
            recommendations.append(
                paper
            )

    return recommendations[:top_k]