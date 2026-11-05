"""
Run ONCE on your PC. Copies the first 10,000 records (the same ones your old load_papers.py loaded)
from the huge ArXiv snapshot into a small file that can live in your repo and Docker image.

    python scripts/export_subset.py "C:\\Users\\Prathmesh\\Desktop\\RESEARCH PAPER RECOMMENDATION\\arxiv-metadata-oai-snapshot.json"

Output: data/papers_10k.jsonl  (about 15 MB)
"""
import json
import os
import sys

LIMIT = 10000
FIELDS = ("id", "title", "authors", "abstract", "categories", "update_date")

src = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else "data/papers_10k.jsonl"
os.makedirs(os.path.dirname(out) or ".", exist_ok=True)

n = 0
with open(src, "r", encoding="utf-8") as fin, open(out, "w", encoding="utf-8") as fout:
    for line in fin:
        if n >= LIMIT:
            break
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        fout.write(json.dumps({k: d.get(k, "") for k in FIELDS}, ensure_ascii=False) + "\n")
        n += 1

print(f"wrote {n} records to {out}")
