import pickle

with open("embeddings/paper_ids.pkl", "rb") as f:
    paper_ids = pickle.load(f)

print(type(paper_ids[0]))
print(paper_ids[0])