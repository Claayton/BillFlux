"""Tests for the app layout (sidebar vs public header)"""


def test_sidebar_present_when_logged_in(logged_client):
    """Authenticated pages should render the sidebar + topbar layout."""

    response = logged_client.get("/bills")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'class="app-mode"' in page
    assert 'class="sidebar"' in page
    assert 'class="topbar"' in page
    assert "Visão geral" in page
    assert "Plano de contas" in page


def test_public_layout_without_sidebar(client):
    """Public pages should keep the top header and no sidebar."""

    response = client.get("/")

    assert response.status_code == 200
    page = response.get_data(as_text=True)
    assert 'class="app-mode"' not in page
    assert 'class="sidebar"' not in page
    assert 'class="topbar"' not in page
    assert 'class="site-header"' in page
