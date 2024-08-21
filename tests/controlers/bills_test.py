"""Tests from bills route"""


def test_bills_1(client):
    """Testando a rota bills"""

    url = "/bills"

    response = client.get(url)

    assert response.status_code == 200


def test_bills_2(client):
    """Testando a rota bills"""

    url = "/bills/"

    response = client.get(url)

    assert response.status_code == 200


def test_bills_3(client):
    pass
