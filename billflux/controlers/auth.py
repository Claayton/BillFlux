"""Module to instantiate the blueprint for authentication"""

from functools import wraps

from flask import flash, redirect, render_template, request, session, url_for
from flask.blueprints import Blueprint
from werkzeug.security import check_password_hash, generate_password_hash

from billflux.infra.repository.user_repository import UserRepository

bp = Blueprint("bp_auth", __name__)


def login_required(view):
    """Redirects unauthenticated users to the login page."""

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user"):
            return redirect(url_for("bp_auth.login"))
        return view(*args, **kwargs)

    return wrapped


@bp.route("/login/", methods=["GET", "POST"])
@bp.route("/login", methods=["GET", "POST"])
def login():
    """Login page route"""

    if session.get("user"):
        return redirect(url_for("bp_bills.bills"))

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")

        user = UserRepository().get_user_by_username(username)

        if user and check_password_hash(user.password_hash, password):
            session["user"] = user.username
            flash(f"Bem-vindo, {user.username}!", "success")
            return redirect(url_for("bp_bills.bills"))

        flash("Usuário ou senha inválidos.", "error")

    return render_template("login.html")


@bp.route("/signin/", methods=["GET", "POST"])
@bp.route("/signin", methods=["GET", "POST"])
def signin():
    """Sign in page route"""

    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if len(username) < 3:
            flash("O usuário deve ter pelo menos 3 caracteres.", "error")
            return render_template("signin.html")

        if len(password) < 4:
            flash("A senha deve ter pelo menos 4 caracteres.", "error")
            return render_template("signin.html")

        repository = UserRepository()

        if repository.get_user_by_username(username):
            flash("Este usuário já existe.", "error")
            return render_template("signin.html")

        repository.create_user(
            username=username,
            email=email or None,
            password_hash=generate_password_hash(password),
        )
        flash("Conta criada com sucesso! Faça login para continuar.", "success")
        return redirect(url_for("bp_auth.login"))

    return render_template("signin.html")


@bp.route("/logout")
def logout():
    """Logout route"""

    session.pop("user", None)
    flash("Você saiu da sua conta.", "info")
    return redirect(url_for("bp_home.index"))
