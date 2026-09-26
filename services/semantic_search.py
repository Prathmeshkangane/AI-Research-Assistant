import time
import pickle
import faiss
import numpy as np

from sentence_transformers import SentenceTransformer
from models.paper import Paper

print("Loading Semantic Search Components...")

model = SentenceTransformer(
    "sentence-transformers/all-MiniLM-L6-v2"
)

index = faiss.read_index(
    "embeddings/papers.index"
)

with open(
    "embeddings/paper_ids.pkl",
    "rb"
) as f:
    paper_ids = pickle.load(f)


def semantic_search(
    query,
    top_k=20
):
    query_embedding = model.encode(
        [query]
    ).astype("float32")

    start = time.time()
    distances, indices = index.search(
        query_embedding,
        top_k
    )
    print(f"FAISS search took {time.time() - start:.4f}s")

    results = []

    for idx in indices[0]:

        arxiv_id = paper_ids[idx]

        paper = Paper.query.get(
            arxiv_id
        )

        if paper:
            results.append(paper)

    return results