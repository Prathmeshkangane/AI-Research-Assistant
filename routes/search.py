from flask import Blueprint, render_template, request, session
from models.paper import Paper
from models.saved_paper import SavedPaper
from services.faiss_recommendation import get_similar_papers_faiss
from services.semantic_search import semantic_search

search_bp = Blueprint("search", __name__)

@search_bp.route("/search")
def search():

    query = request.args.get("q", "").strip()

    papers = []

    if query:

        papers = semantic_search(
            query,
            top_k=20
        )

    return render_template(
        "search.html",
        papers=papers,
        query=query
    )

@search_bp.route("/paper/<paper_id>")
def paper_detail(paper_id):

    paper = Paper.query.get_or_404(paper_id)

    recommendations = get_similar_papers_faiss(
        paper,
        top_k=5
    )

    # lets the page show "Saved · remove" instead of "Save" for papers already in the library
    is_saved = False
    if "user_id" in session:
        is_saved = SavedPaper.query.filter_by(
            user_id=session["user_id"],
            paper_id=paper_id
        ).first() is not None

    return render_template(
        "paper_detail.html",
        paper=paper,
        recommendations=recommendations,
        is_saved=is_saved
    )
