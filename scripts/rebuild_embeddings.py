"""
Rebuilds embeddings AND the FAISS index in one step, for any embedding model.
Run from the project root (next to app.py).

  python rebuild_embeddings.py                                    # MiniLM -> embeddings/
  python rebuild_embeddings.py --model BAAI/bge-small-en-v1.5 --out embeddings_bge
  python rebuild_embeddings.py --model intfloat/e5-small-v2 --doc_prefix passage: --out embeddings_e5

It only needs the database (not the old index), so it never gets stuck on a missing embeddings folder.
"""
import argparse
import os
import pickle
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import faiss
import numpy as np
from flask import Flask
from sentence_transformers import SentenceTransformer

from config import Config
from models import db
from models.paper import Paper

ap = argparse.ArgumentParser()
ap.add_argument("--model", default="sentence-transformers/all-MiniLM-L6-v2")
ap.add_argument("--doc_prefix", default="", help="text put before every paper, e.g. passage:  (for e5 models)")
ap.add_argument("--out", default="embeddings")
args = ap.parse_args()

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

os.makedirs(args.out, exist_ok=True)


def clean(s):
    return " ".join((s or "").split())


print("Loading model:", args.model)
model = SentenceTransformer(args.model)

with app.app_context():
    papers = Paper.query.all()
    print(f"Loaded {len(papers)} papers")
    paper_ids = [p.id for p in papers]
    prefix = f"{args.doc_prefix} " if args.doc_prefix else ""
    texts = [
        f"{prefix}Title: {clean(p.title)}. Categories: {clean(p.categories)}. Abstract: {clean(p.abstract)}"
        for p in papers
    ]

print("Generating embeddings (this takes several minutes on CPU)...")
embeddings = model.encode(
    texts, show_progress_bar=True, batch_size=32, convert_to_numpy=True,
    normalize_embeddings=True,          # unit-length vectors: L2 ranking == cosine ranking
).astype("float32")
print("Embedding shape:", embeddings.shape)

np.save(os.path.join(args.out, "paper_embeddings.npy"), embeddings)
with open(os.path.join(args.out, "paper_ids.pkl"), "wb") as f:
    pickle.dump(paper_ids, f)

index = faiss.IndexFlatL2(embeddings.shape[1])
index.add(embeddings)
faiss.write_index(index, os.path.join(args.out, "papers.index"))
print(f"Saved {index.ntotal} vectors to {args.out}/  (use it with:  set EMBEDDINGS_DIR={args.out})")