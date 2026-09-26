from flask import (
    Blueprint,
    render_template,
    session
)

from models.chat_history import ChatHistory

history_bp = Blueprint(
    "history",
    __name__
)

@history_bp.route("/history")
def history():

    print(
        "HISTORY SESSION:",
        dict(session)
    )

    if "user_id" not in session:
        return "Please login first"

    chats = ChatHistory.query.filter_by(
        user_id=session["user_id"]
    ).order_by(
        ChatHistory.created_at.desc()
    ).all()

    return render_template(
        "history.html",
        chats=chats
    )
