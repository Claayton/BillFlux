"""Tests from bills route"""

from flask_login import login_user
from billflux.infra.entities import User


def test_bills_1_with_user_logged(client, fake_user):
    """Testing /bills route, with user logged"""

    url = "/bills"
    user = User(id=fake_user.id, email=fake_user.email)
    login_user(user)

    response = client.get(url)

    assert response.status_code == 200


def test_bills_1_without_user_logged(client):
    """Testing /bills route, without user logged"""

    url = "/bills"

    response = client.get(url)

    assert response.status_code == 302


def test_bills_2(client, fake_user):
    """Testing /bills/ route, with user loged"""

    url = "/bills/"
    user = User(id=fake_user.id, email=fake_user.email)
    login_user(user)

    response = client.get(url)

    assert response.status_code == 200


def test_bills_2_without_user_logged(client):
    """Testing /bills/ route, without user logged"""

    url = "/bills/"

    response = client.get(url)

    assert response.status_code == 302
