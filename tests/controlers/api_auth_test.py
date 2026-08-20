"""Tests for the JSON auth API consumed by the SPA."""


def _csrf(client):
    """Pega um token CSRF válido pela própria API."""
    response = client.get("/api/auth/csrf")
    assert response.status_code == 200
    return response.get_json()["csrf_token"]


def _login(client, username="admin", password="admin"):
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRFToken": _csrf(client)},
    )


def test_csrf_endpoint(client):
    """/api/auth/csrf deve devolver um token no formato esperado."""

    response = client.get("/api/auth/csrf")

    assert response.status_code == 200
    assert "csrf_token" in response.get_json()


def test_me_logged_out(client):
    """Sem sessão, /api/auth/me devolve user null."""

    response = client.get("/api/auth/me")

    assert response.status_code == 200
    data = response.get_json()
    assert data["user"] is None
    assert data["allow_signup"] is True


def test_login_success(client):
    """Credenciais corretas abrem sessão e devolvem o usuário."""

    response = _login(client)

    assert response.status_code == 200
    assert response.get_json()["user"] == "admin"

    me = client.get("/api/auth/me").get_json()
    assert me["user"] == "admin"


def test_login_wrong_password(client):
    """Senha errada deve devolver 401 JSON."""

    response = client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "errada"},
        headers={"X-CSRFToken": _csrf(client)},
    )

    assert response.status_code == 401
    assert response.get_json()["error"]


def test_login_unknown_user(client):
    """Usuário inexistente deve devolver 401 JSON."""

    response = client.post(
        "/api/auth/login",
        json={"username": "naoexiste", "password": "1234"},
        headers={"X-CSRFToken": _csrf(client)},
    )

    assert response.status_code == 401


def test_login_requires_csrf(client):
    """POST sem token CSRF deve ser rejeitado (CSRFProtect global)."""

    response = client.post(
        "/api/auth/login", json={"username": "admin", "password": "admin"}
    )

    assert response.status_code == 400


def test_logout(client):
    """Logout encerra a sessão e devolve ok."""

    assert _login(client).status_code == 200

    response = client.post(
        "/api/auth/logout", json={}, headers={"X-CSRFToken": _csrf(client)}
    )

    assert response.status_code == 200
    assert response.get_json()["ok"] is True
    assert client.get("/api/auth/me").get_json()["user"] is None


def test_signin_creates_account(client):
    """Signin cria a conta e devolve 201."""

    response = client.post(
        "/api/auth/signin",
        json={"username": "novouser", "password": "1234"},
        headers={"X-CSRFToken": _csrf(client)},
    )

    assert response.status_code == 201
    assert response.get_json()["ok"] is True

    login = _login(client, username="novouser", password="1234")
    assert login.status_code == 200


def test_signin_short_username(client):
    """Usuário com menos de 3 caracteres deve ser rejeitado."""

    response = client.post(
        "/api/auth/signin",
        json={"username": "ab", "password": "1234"},
        headers={"X-CSRFToken": _csrf(client)},
    )

    assert response.status_code == 400


def test_signin_duplicate_user(client):
    """Criar um usuário já existente deve devolver 400."""

    response = client.post(
        "/api/auth/signin",
        json={"username": "admin", "password": "1234"},
        headers={"X-CSRFToken": _csrf(client)},
    )

    assert response.status_code == 400
