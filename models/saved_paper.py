from models import db
from datetime import datetime

class SavedPaper(db.Model):

    __tablename__ = "saved_papers"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey("users.id"),
        nullable=False
    )

    paper_id = db.Column(
        db.String(50),
        db.ForeignKey("papers.id"),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )