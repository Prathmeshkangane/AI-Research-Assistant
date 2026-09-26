from flask import Blueprint, render_template, request
from flask import session
from models.chat_history import ChatHistory
from models import db
from services.rag_service import answer_question

ask_bp = Blueprint(
    "ask",
    __name__
)

@ask_bp.route(
    "/ask",
    methods=["GET", "POST"]
)
def ask():

    answer = None
    papers = []
    question = ""

    if request.method == "POST":

        question = request.form.get(
            "question",
            ""
        )

        if question:

            answer, papers = answer_question(
                question
            )
        if "user_id" in session:

            chat = ChatHistory(
                user_id=session["user_id"],
                question=question,
                answer=answer
            )

            db.session.add(chat)
            db.session.commit()

    return render_template(
        "ask.html",
        question=question,
        answer=answer,
        papers=papers
    )