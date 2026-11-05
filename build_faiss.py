import os
import faiss
import numpy as np

os.makedirs("embeddings", exist_ok=True)

print("Loading embeddings...")

embeddings = np.load(
    "embeddings/paper_embeddings.npy"
)

embeddings = embeddings.astype("float32")

print("Shape:", embeddings.shape)

dimension = embeddings.shape[1]

index = faiss.IndexFlatL2(dimension)

index.add(embeddings)

print("Vectors indexed:", index.ntotal)

faiss.write_index(
    index,
    "embeddings/papers.index"
)

print("FAISS index saved successfully")