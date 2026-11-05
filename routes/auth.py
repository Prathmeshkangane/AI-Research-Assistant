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

MIN_PASSWORD_LENGTH = 8


@auth_bp.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("register.html")

    username = request.form.get("username", "").strip()
    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    if not username or not email or not password:
        flash("All fields are required")
        return redirect("/register")

    if len(password) < MIN_PASSWORD_LENGTH:
        flash(f"Password must be at least {MIN_PASSWORD_LENGTH} characters")
        return redirect("/register")

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

    email = request.form.get("email", "").strip().lower()
    password = request.form.get("password", "")

    user = User.query.filter_by(email=email).first()

    # FIX: one generic message, so attackers cannot discover which emails are registered
    if not user or not bcrypt.checkpw(
        password.encode("utf-8"),
        user.password_hash.encode("utf-8")
    ):
        flash("Invalid email or password")
        return redirect("/login")

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    return redirect("/dashboard")


@auth_bp.route("/logout")
def logout():
    session.clear()
    return redirect("/")
