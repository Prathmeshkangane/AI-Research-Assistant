import pickle

from app import app
from models import db
from models.paper import Paper

with app.app_context():
    ids = pickle.load(open("embeddings/paper_ids.pkl", "rb"))
    db_ids = {row[0] for row in db.session.query(Paper.id).all()}

    print("Papers in DB:", len(db_ids))
    print("IDs in pickle:", len(ids))
    print("Pickle IDs found in DB:", len(set(ids) & db_ids))