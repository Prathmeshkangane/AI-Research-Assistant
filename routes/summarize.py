from flask import Blueprint
from flask import render_template
from flask import session
from flask import redirect

from models.paper import Paper
from services.summary_service import summarize_paper

summarize_bp = Blueprint(
    "summarize",
    __name__
)

@summarize_bp.route("/summarize/<paper_id>")
def summarize(paper_id):

    if "user_id" not in session:
        return redirect("/login")

    paper = Paper.query.get_or_404(paper_id)

    summary = summarize_paper(paper)

    return render_template(
        "summary.html",
        paper=paper,
        summary=summary
    )