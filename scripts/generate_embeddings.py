import sys
import os

sys.path.append(
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            ".."
        )
    )
)

import pickle
import numpy as np

from sentence_transformers import SentenceTransformer

from flask import Flask
from config import Config
from models import db

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
from models.paper import Paper

# Create embeddings directory
os.makedirs(
    "embeddings",
    exist_ok=True
)

print("Loading model...")

model = SentenceTransformer(
    "all-MiniLM-L6-v2"
)

def clean(s):
    return " ".join((s or "").split())

with app.app_context():

    papers = Paper.query.all()

    print(
        f"Loaded {len(papers)} papers"
    )

    paper_ids = [
        paper.id
        for paper in papers
    ]

    # Better semantic representation
    texts = [
    f"Title: {clean(paper.title)}. Categories: {clean(paper.categories)}. Abstract: {clean(paper.abstract)}"
    for paper in papers
    ]

    print(
        "Generating embeddings..."
    )

    embeddings = model.encode(
        texts,
        show_progress_bar=True,
        batch_size=32,
        convert_to_numpy=True
    )

    print(
        f"Embedding Shape: {embeddings.shape}"
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

print(
    "Embeddings saved successfully"
)