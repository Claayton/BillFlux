"""Teste para a Rota Home"""


def test_home_route_1(client):
    """Testando a rota /"""

    url = """/"""

    response = client.get(url)

    assert response.status_code == 200


def test_home_rotue_2(client):
    """Testando a rota /home"""

    url = """/home"""

    response = client.get(url)

    assert response.status_code == 200


def test_home_rotue_3(client):
    """Testando a rota /home/"""

    url = """/home/"""

    response = client.get(url)

    assert response.status_code == 200
