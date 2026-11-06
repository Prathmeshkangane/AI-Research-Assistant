import json
import logging
import os
import pickle
import time

import faiss
import numpy as np

from models.paper import Paper

log = logging.getLogger(__name__)

EMB_DIR = os.getenv("EMBEDDINGS_DIR", "embeddings")
DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def resolve_settings(env, meta):
    """Which model / query prefix / backend to use.
    Priority: environment variable > embeddings/meta.json (written by rebuild_embeddings.py) > default.
    Reading meta.json means the model ALWAYS matches the index it was built with."""
    model = env.get("EMBED_MODEL") or meta.get("model") or DEFAULT_MODEL
    prefix = env["QUERY_PREFIX"] if "QUERY_PREFIX" in env else meta.get("query_prefix", "")
    backend = (env.get("EMBED_BACKEND") or "torch").lower()      # "torch" (sentence-transformers) or "onnx" (fastembed)
    return model, prefix, backend


_meta_path = os.path.join(EMB_DIR, "meta.json")
_meta = json.load(open(_meta_path, encoding="utf-8")) if os.path.exists(_meta_path) else {}
EMBED_MODEL, QUERY_PREFIX, BACKEND = resolve_settings(os.environ, _meta)

log.info("Loading semantic search components: model=%s backend=%s", EMBED_MODEL, BACKEND)

if BACKEND == "onnx":
    # Light runtime for the web server: no PyTorch, much less memory.
    from fastembed import TextEmbedding
    model = TextEmbedding(model_name=EMBED_MODEL, cache_dir=os.getenv("FASTEMBED_CACHE_PATH"))
else:
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(EMBED_MODEL)

index = faiss.read_index(os.path.join(EMB_DIR, "papers.index"))

with open(os.path.join(EMB_DIR, "paper_ids.pkl"), "rb") as f:
    paper_ids = pickle.load(f)


def encode_query(text):
    """Query vector, L2-normalised (so cosine = 1 - L2_distance / 2 holds for any model)."""
    text = f"{QUERY_PREFIX} {text}" if QUERY_PREFIX else text
    if BACKEND == "onnx":
        vec = np.asarray(list(model.embed([text])), dtype="float32").reshape(1, -1)
        return vec / np.maximum(np.linalg.norm(vec, axis=1, keepdims=True), 1e-12)
    return model.encode([text], normalize_embeddings=True).astype("float32")


def fetch_papers_in_order(ids):
    """ONE database query for all ids (was one query per result), returned in the given order."""
    if not ids:
        return []
    rows = Paper.query.filter(Paper.id.in_(ids)).all()
    by_id = {p.id: p for p in rows}
    return [by_id[i] for i in ids if i in by_id]


def semantic_search(query, top_k=20, return_scores=False):
    """Returns a list of Paper objects, best first.
    With return_scores=True returns [(Paper, l2_distance), ...] (smaller distance = more similar)."""
    query = (query or "").strip()
    if not query:
        return []

    query_embedding = encode_query(query)

    start = time.perf_counter()
    distances, indices = index.search(query_embedding, top_k)
    log.info("faiss_search_ms=%.2f", (time.perf_counter() - start) * 1000)

    hits = [
        (paper_ids[i], float(d))
        for i, d in zip(indices[0], distances[0])
        if i != -1                      # FAISS returns -1 when fewer than top_k vectors exist
    ]
    papers = fetch_papers_in_order([pid for pid, _ in hits])

    if return_scores:
        dist = dict(hits)
        return [(p, dist[p.id]) for p in papers]
    return papers