# Patch for the AI Research Assistant

Copy these files into your project, keeping the same folder structure (they replace your versions):

    config.py                      app.py                         load_papers.py
    routes/ask.py                  routes/auth.py                 routes/history.py        routes/saved.py
    services/semantic_search.py    services/faiss_recommendation.py   services/rag_service.py
    services/summary_service.py    services/compare_service.py
    scripts/export_subset.py       tests/  (conftest.py + test_app.py)
    .dockerignore                  .github/workflows/ci.yml

Then:

    pip install pytest
    pytest -q                      # 19 tests, ~3 seconds, no model download / MySQL / API key needed

One-time data export (so the Docker image and cloud DB can be filled without the 3.5 GB snapshot):

    python scripts/export_subset.py "C:\path\to\arxiv-metadata-oai-snapshot.json"   # writes data/papers_10k.jsonl
    python load_papers.py                                                            # local DB
    docker compose exec web python load_papers.py                                    # Docker DB

Commit `embeddings/` (papers.index + paper_ids.pkl) and `data/papers_10k.jsonl` to your repo.
`embeddings/paper_embeddings.npy` is no longer used by the app (you can leave it out of the image).
Never commit `.env`.
