from services.semantic_search import index, paper_ids, fetch_papers_in_order

# O(1) lookup instead of paper_ids.index(...) (O(n)); reuses the index already in memory
# instead of loading a second copy plus the 15 MB embeddings .npy file.
_id_to_pos = {pid: i for i, pid in enumerate(paper_ids)}


def get_similar_papers_faiss(target_paper, top_k=5):

    pos = _id_to_pos.get(target_paper.id)
    if pos is None:
        return []

    query_vector = index.reconstruct(pos).reshape(1, -1).astype("float32")

    _, indices = index.search(query_vector, top_k + 1)

    ids = [
        paper_ids[i]
        for i in indices[0]
        if i != -1 and paper_ids[i] != target_paper.id
    ][:top_k]

    return fetch_papers_in_order(ids)
