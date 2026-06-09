from flask import Blueprint, request
from models import db
from models.user import User
import bcrypt
from flask import Blueprint, request, session
from flask import redirect

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/register", methods=["POST"])
def register():

    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]

    existing_user = User.query.filter_by(
        email=email
    ).first()

    if existing_user:
        return "Email already registered"

    hashed_password = bcrypt.hashpw(
        password.encode("utf-8"),
        bcrypt.gensalt()
    ).decode("utf-8")

    user = User(
        username=username,
        email=email,
        password_hash=hashed_password
    )

    db.session.add(user)
    db.session.commit()

    return "Registration Successful"

@auth_bp.route("/login", methods=["POST"])
def login():

    email = request.form["email"]
    password = request.form["password"]

    user = User.query.filter_by(
        email=email
    ).first()

    if not user:
        return "User not found"

    if bcrypt.checkpw(
        password.encode("utf-8"),
        user.password_hash.encode("utf-8")
    ):

        session["user_id"] = user.id
        session["username"] = user.username

        return redirect("/dashboard")
    return "Invalid Password"
@auth_bp.route("/logout")
def logout():

    session.clear()

    return "Logged Out"
    