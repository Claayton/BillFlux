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


def test_home_dashboard_logged_in(logged_client):
    """Logged-in users should see the dashboard instead of the hero."""

    response = logged_client.get("/home")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert "Visão geral" in page
    assert "Vendas hoje" in page
    assert "Contas em aberto" in page
    assert 'class="hero"' not in page
