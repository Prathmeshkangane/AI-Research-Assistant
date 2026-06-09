import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
)
import os
import pickle
import numpy as np

from sentence_transformers import SentenceTransformer

from app import app
from models.paper import Paper

os.makedirs("embeddings", exist_ok=True)

print("Loading model...")

model = SentenceTransformer("all-MiniLM-L6-v2")

with app.app_context():

    papers = Paper.query.all()

    print(f"Loaded {len(papers)} papers")

    paper_ids = [paper.id for paper in papers]

    abstracts = [
        paper.abstract
        for paper in papers
    ]

    print("Generating embeddings...")

    embeddings = model.encode(
        abstracts,
        show_progress_bar=True,
        batch_size=32
    )

    np.save(
        "embeddings/paper_embeddings.npy",
        embeddings
    )

    with open(
        "embeddings/paper_ids.pkl",
        "wb"
    ) as f:

        pickle.dump(
            paper_ids,
            f
        )

print("Embeddings saved successfully")