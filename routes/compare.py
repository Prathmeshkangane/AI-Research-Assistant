from flask import Blueprint
from flask import render_template
from flask import request
from flask import session
from flask import redirect

from models.paper import Paper
from services.compare_service import compare_papers

compare_bp = Blueprint(
    "compare",
    __name__
)

@compare_bp.route("/compare")
def compare():

    if "user_id" not in session:
        return redirect("/login")

    paper1_id = request.args.get("paper1")
    paper2_id = request.args.get("paper2")

    if not paper1_id or not paper2_id:
        return "Please provide paper1 and paper2 ids"

    paper1 = Paper.query.get_or_404(paper1_id)
    paper2 = Paper.query.get_or_404(paper2_id)

    comparison = compare_papers(
        paper1,
        paper2
    )

    return render_template(
        "compare.html",
        paper1=paper1,
        paper2=paper2,
        comparison=comparison
    )