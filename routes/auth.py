from flask import (
    Blueprint,
    request,
    session,
    redirect,
    flash,
    render_template
)

from sqlalchemy.exc import IntegrityError

from models import db
from models.user import User

import bcrypt

auth_bp = Blueprint(
    "auth",
    __name__
)

@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    username = request.form["username"]
    email = request.form["email"]
    password = request.form["password"]

    existing_user = User.query.filter(
        (User.email == email) | (User.username == username)
    ).first()

    if existing_user:
        if existing_user.email == email:
            flash("Email already registered")
        else:
            flash("Username already taken")
        return redirect("/register")

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

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash("Username or email already registered")
        return redirect("/register")

    flash("Registration successful — please sign in.")
    return redirect("/login")


@auth_bp.route("/login", methods=["POST"])
def login():

    email = request.form["email"]
    password = request.form["password"]

    user = User.query.filter_by(email=email).first()

    if not user:
        flash("User not found")
        return redirect("/login")

    if bcrypt.checkpw(
        password.encode("utf-8"),
        user.password_hash.encode("utf-8")
    ):
        session["user_id"] = user.id
        session["username"] = user.username
        return redirect("/dashboard")

    flash("Invalid password")
    return redirect("/login")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")