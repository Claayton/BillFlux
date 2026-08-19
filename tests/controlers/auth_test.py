"""Tests from auth routes"""

import re

from billflux.infra.repository.user_repository import UserRepository


def _csrf(client, path="/login"):
    page = client.get(path)
    match = re.search(r'name="csrf_token" value="([^"]+)"', page.get_data(as_text=True))
    assert match, "CSRF token not found"
    return match.group(1)


def _signup(client, username="novo_usuario", password="segredo"):
    response = client.post(
        "/signin",
        data={
            "csrf_token": _csrf(client, "/signin"),
            "username": username,
            "email": "novo@exemplo.com",
            "password": password,
        },
    )
    return response


def test_login_page(client):
    response = client.get("/login")
    assert response.status_code == 200


def test_signin_page(client):
    response = client.get("/signin")
    assert response.status_code == 200


def test_signup_creates_user_and_allows_login(client):
    """After signing up, the new credentials must work on login."""

    response = _signup(client)
    assert response.status_code == 302

    user = UserRepository().get_user_by_username("novo_usuario")
    assert user is not None

    login_response = client.post(
        "/login",
        data={
            "csrf_token": _csrf(client),
            "username": "novo_usuario",
            "password": "segredo",
        },
    )
    assert login_response.status_code == 302
    assert client.get("/bills").status_code == 200


def test_signup_duplicate_username(client):
    _signup(client)

    response = _signup(client)
    assert response.status_code == 200
    assert b"j\xc3\xa1 existe" in response.data


def test_signup_short_password(client):
    response = _signup(client, password="12")
    assert response.status_code == 200
    assert b"pelo menos 4" in response.data


def test_login_valid(logged_client):
    response = logged_client.get("/bills")
    assert response.status_code == 200


def test_login_invalid(client):
    response = client.post(
        "/login",
        data={"csrf_token": _csrf(client), "username": "admin", "password": "errada"},
    )
    assert response.status_code == 200
    assert b"inv" in response.data.lower()


def test_login_redirects_when_already_logged(logged_client):
    response = logged_client.get("/login")
    assert response.status_code == 302


def test_logout(logged_client):
    response = logged_client.get("/logout")
    assert response.status_code == 302

    response = logged_client.get("/bills")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
