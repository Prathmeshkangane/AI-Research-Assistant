from flask import Flask
from config import Config
from models import db
from models.user import User
from routes.auth import auth_bp
from flask import render_template
from flask import session
from models.paper import Paper
from routes.search import search_bp
from routes.ask import ask_bp
from models.chat_history import ChatHistory
from routes.history import history_bp
from models.saved_paper import SavedPaper
from routes.saved import saved_bp
from routes.saved_papers import saved_papers_bp
from routes.compare import compare_bp
from routes.summarize import summarize_bp


app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)
app.register_blueprint(auth_bp)
app.register_blueprint(search_bp)
app.register_blueprint(ask_bp)
app.register_blueprint(history_bp)
app.register_blueprint(saved_bp)
app.register_blueprint(saved_papers_bp)
app.register_blueprint(compare_bp)
app.register_blueprint(summarize_bp)

with app.app_context():
    db.create_all()

@app.route("/")
def home():
    return render_template("register.html")

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return "Please login first"

    paper_count = Paper.query.count()
    saved_count = SavedPaper.query.filter_by(user_id=session["user_id"]).count()

    return render_template(
        "dashboard.html",
        username=session["username"],
        paper_count=paper_count,
        saved_count=saved_count
    )

if __name__ == "__main__":
    app.run(debug=True)