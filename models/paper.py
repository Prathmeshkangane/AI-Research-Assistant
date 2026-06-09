from models import db

class Paper(db.Model):
    __tablename__ = "papers"

    id = db.Column(
        db.String(50),
        primary_key=True
    )

    title = db.Column(
        db.String(1000),
        nullable=False
    )

    authors = db.Column(
        db.Text,
        nullable=False
    )

    abstract = db.Column(
        db.Text,
        nullable=False
    )

    categories = db.Column(
        db.String(255),
        nullable=False
    )

    update_date = db.Column(
        db.String(20)
    )

    def __repr__(self):
        return f"<Paper {self.title}>"