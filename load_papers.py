"""
Loads papers into the database from data/papers_10k.jsonl (create it with scripts/export_subset.py).
Safe to run twice: papers that already exist are skipped.

    python load_papers.py                        # uses data/papers_10k.jsonl
    python load_papers.py --source other.jsonl --limit 5000

Inside Docker Compose:   docker compose exec web python load_papers.py
Against Aiven/cloud DB:  set the DB_* variables (and DB_SSL_CA) and run it from your PC.
"""
import argparse
import json

from app import app
from models import db
from models.paper import Paper

parser = argparse.ArgumentParser()
parser.add_argument("--source", default="data/papers_10k.jsonl")
parser.add_argument("--limit", type=int, default=10000)
args = parser.parse_args()

added = skipped = 0

with app.app_context():

    existing = {pid for (pid,) in db.session.query(Paper.id).all()}

    with open(args.source, "r", encoding="utf-8") as file:

        for line_no, line in enumerate(file, start=1):

            if line_no > args.limit:
                break

            try:
                data = json.loads(line)
                if data.get("id", "") in existing:
                    skipped += 1
                    continue

                db.session.add(Paper(
                    id=data.get("id", ""),
                    title=data.get("title", "").strip(),
                    authors=data.get("authors", "").strip(),
                    abstract=data.get("abstract", "").strip(),
                    categories=data.get("categories", "").strip(),
                    update_date=data.get("update_date", "")
                ))
                added += 1

                if added % 500 == 0:
                    db.session.commit()
                    print(f"{added} papers loaded")

            except Exception as e:
                db.session.rollback()
                print(f"Error on line {line_no}: {e}")

    db.session.commit()

print(f"\nFinished: {added} added, {skipped} already present")
