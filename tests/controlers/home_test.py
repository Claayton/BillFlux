"""Tests from home routes"""


def test_home_route_1(client):
    """Testing the / rote"""

    url = """/"""

    response = client.get(url)

    assert response.status_code == 200


def test_home_rotue_2(client):
    """Testing the /home route"""

    url = """/home"""

    response = client.get(url)

    assert response.status_code == 200


def test_home_rotue_3(client):
    """Testing the /home/ route"""

    url = """/home/"""

    response = client.get(url)

    assert response.status_code == 200
