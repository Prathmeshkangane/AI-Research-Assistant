from flask import Blueprint
from flask import session
from flask import redirect

from models import db
from models.saved_paper import SavedPaper

saved_bp = Blueprint(
    "saved",
    __name__
)

@saved_bp.route("/save/<paper_id>")
def save_paper(paper_id):

    if "user_id" not in session:
        return redirect("/login")

    existing = SavedPaper.query.filter_by(
        user_id=session["user_id"],
        paper_id=paper_id
    ).first()

    if not existing:

        saved = SavedPaper(
            user_id=session["user_id"],
            paper_id=paper_id
        )

        db.session.add(saved)
        db.session.commit()

    return redirect(f"/paper/{paper_id}")

@saved_bp.route("/unsave/<paper_id>")
def unsave_paper(paper_id):

    if "user_id" not in session:
        return redirect("/login")

    saved = SavedPaper.query.filter_by(
        user_id=session["user_id"],
        paper_id=paper_id
    ).first()

    if saved:

        db.session.delete(saved)
        db.session.commit()

    return redirect("/saved-papers")