from flask import Blueprint, render_template, request
from models.paper import Paper
from services.faiss_recommendation import get_similar_papers_faiss
from services.semantic_search import semantic_search

search_bp = Blueprint("search", __name__)

@search_bp.route("/search")
def search():

    query = request.args.get("q", "")

    papers = []

    if query:

        papers = semantic_search(
            query,
            top_k=20
        )

        print("Semantic Query:", query)
        print("Results Found:", len(papers))

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

    return render_template(
        "paper_detail.html",
        paper=paper,
        recommendations=recommendations
    )