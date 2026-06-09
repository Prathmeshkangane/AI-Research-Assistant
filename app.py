from flask import Flask
from config import Config
from models import db
from models.user import User
from routes.auth import auth_bp
from flask import render_template
from flask import session
from models.paper import Paper
from routes.search import search_bp

app = Flask(__name__)

app.config.from_object(Config)

db.init_app(app)
app.register_blueprint(auth_bp)
app.register_blueprint(search_bp)

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

    return f"Welcome {session['username']}"

if __name__ == "__main__":
    app.run(debug=True)