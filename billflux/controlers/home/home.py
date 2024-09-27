"""Controllers and Routes from Home"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, current_user
from sqlmodel import create_engine, select
from billflux.infra.config.database import get_session
from billflux.infra.entities import User as UserModel
from billflux.infra.repository.users_repository import UserRepository
from billflux.security.password_hash import PasswordHash
from billflux.config import settings

bp = Blueprint("bp_home", __name__)

database_url = settings["development"].DATABASE_URL


@bp.route("/")
@bp.route("/home/")
@bp.route("/home")
def index():
    """Index Route"""

    if current_user.is_authenticated:
        return redirect(url_for("bp_get_bills.bills"))
    return render_template("home.html")


@bp.route("/login", methods=["GET", "POST"])
def login():
    """Login Route"""

    engine = create_engine(database_url)

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        with get_session(engine) as session:

            user = session.exec(
                select(UserModel).where(UserModel.email == email)
            ).one_or_none()

        password_hash = PasswordHash()

        if not user:
            # Login falhou
            flash("Invalid email or password", "error")
            return redirect(url_for("bp_home.index"))

        correct_password = password_hash.verify(
            password=password, password_hashed=user.password_hash
        )

        if correct_password:
            login_user(user)
            flash(f"Logged in as {email}", "success")
            return redirect(url_for("bp_get_bills.bills"))

    flash("Invalid email or password", "error")
    return redirect(url_for("bp_home.index"))


@bp.route("/signup", methods=["POST"])
def signup():
    """Signup Route"""

    user_repository = UserRepository(database_url=database_url)
    password_hash = PasswordHash()

    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")

    user_exists = user_repository.get_user(email=email)

    if user_exists:

        # Usuário já existe
        flash("User already exists", "error")
        return redirect(url_for("bp_home.index"))

    if password != confirm_password:

        # Senhas não coincidem
        flash("Passwords do not match", "error")
        return redirect(url_for("bp_home.index"))

    # Adiciona o novo usuário ao "banco de dados"
    user_repository.insert_user(email=email, password_hash=password_hash.hash(password))
    flash(f"User {email} created successfully", "success")
    return redirect(url_for("bp_home.index"))
