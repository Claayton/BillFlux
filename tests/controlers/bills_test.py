"""Tests from bills route"""


def test_bills_1(client):
    """Testing /bills route"""

    url = "/bills"

    response = client.get(url)

    assert response.status_code == 200


def test_bills_2(client):
    """Testing /bills/ route"""

    url = "/bills/"

    response = client.get(url)

    assert response.status_code == 200
