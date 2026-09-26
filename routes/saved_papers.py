from flask import Blueprint
from flask import render_template
from flask import session
from flask import redirect

from models.saved_paper import SavedPaper
from models.paper import Paper

saved_papers_bp = Blueprint(
    "saved_papers",
    __name__
)

@saved_papers_bp.route("/saved-papers")
def saved_papers():

    if "user_id" not in session:
        return redirect("/login")

    saved = SavedPaper.query.filter_by(
        user_id=session["user_id"]
    ).all()

    papers = []

    for item in saved:

        paper = Paper.query.get(item.paper_id)

        if paper:
            papers.append(paper)

    return render_template(
        "saved_papers.html",
        papers=papers
    )