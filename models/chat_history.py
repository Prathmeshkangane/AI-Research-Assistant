from models import db


class ChatHistory(db.Model):

    __tablename__ = "chat_history"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    user_id = db.Column(
        db.Integer,
        nullable=False
    )

    question = db.Column(
        db.Text,
        nullable=False
    )

    answer = db.Column(
        db.Text,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        server_default=db.func.now()
    )