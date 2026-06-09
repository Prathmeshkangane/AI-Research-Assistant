import json

from app import app
from models import db
from models.paper import Paper

LIMIT = 10000

count = 0

with app.app_context():

    # Optional: Clear existing papers before loading
    # Paper.query.delete()
    # db.session.commit()

    with open(
        r"C:\Users\Prathmesh\Downloads\archive (10)\arxiv-metadata-oai-snapshot.json",
        "r",
        encoding="utf-8"
    ) as file:

        for line in file:

            if count >= LIMIT:
                break

            try:
                data = json.loads(line)

                paper = Paper(
                    id=data.get("id", ""),
                    title=data.get("title", "").strip(),
                    authors=data.get("authors", "").strip(),
                    abstract=data.get("abstract", "").strip(),
                    categories=data.get("categories", "").strip(),
                    update_date=data.get("update_date", "")
                )

                db.session.add(paper)

                count += 1

                if count % 500 == 0:
                    db.session.commit()
                    print(f"{count} papers loaded")

            except Exception as e:
                print(f"Error processing record: {e}")

        db.session.commit()

print(f"\nFinished loading {count} papers")