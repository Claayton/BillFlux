"""Endpoints de autenticação da API JSON."""

from flask import request, session
from flask_wtf.csrf import generate_csrf
from werkzeug.security import check_password_hash, generate_password_hash

from billflux.api import bp, api_error, api_response
from billflux.config import settings
from billflux.infra.repository.user_repository import UserRepository


def _auth_payload():
    return {
        "user": session.get("user"),
        "allow_signup": settings.auth.get("allow_signup", True),
    }


@bp.route("/auth/csrf")
def csrf_token():
    """Devolve um token CSRF para as requisições de escrita."""
    return api_response({"csrf_token": generate_csrf()})


@bp.route("/auth/me")
def me():
    """Identidade do usuário logado (ou null)."""
    return api_response(_auth_payload())


@bp.route("/auth/login", methods=["POST"])
def login():
    """Autentica e abre sessão."""
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    password = data.get("password") or ""

    repository = UserRepository()
    user = repository.get_user_by_username(username)
    if user and check_password_hash(user.password_hash, password):
        session["user"] = user.username
        return api_response(_auth_payload())

    return api_error("Usuário ou senha inválidos.", 401)


@bp.route("/auth/logout", methods=["POST"])
def logout():
    """Encerra a sessão."""
    session.pop("user", None)
    return api_response({"ok": True})


@bp.route("/auth/signin", methods=["POST"])
def signin():
    """Cria uma nova conta, se o cadastro estiver habilitado."""
    if not settings.auth.get("allow_signup", True):
        return api_error("O cadastro está desativado.", 403)

    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip()
    password = data.get("password") or ""

    if len(username) < 3:
        return api_error("O usuário deve ter pelo menos 3 caracteres.", 400)
    if len(password) < 4:
        return api_error("A senha deve ter pelo menos 4 caracteres.", 400)

    repository = UserRepository()
    if repository.get_user_by_username(username):
        return api_error("Este usuário já existe.", 400)

    repository.create_user(
        username=username,
        email=email or None,
        password_hash=generate_password_hash(password),
    )
    return api_response({"ok": True}, status=201)
