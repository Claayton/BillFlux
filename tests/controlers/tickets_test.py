"""Testes para a rota tickets"""


def test_tickets_1(client):
    """Testando a rota tickets"""

    url = "/tickets"

    response = client.get(url)

    assert response.status_code == 200


def test_tickets_2(client):
    """Testando a rota tickets"""

    url = "/tickets/"

    response = client.get(url)

    assert response.status_code == 200
