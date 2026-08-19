"""Tests from bills route"""


def test_bills_1(logged_client):
    """Testing /bills route"""

    response = logged_client.get("/bills")

    assert response.status_code == 200
    assert "pay-modal" in response.get_data(as_text=True)
    assert "JsBarcode" in response.get_data(as_text=True)
    assert "pay-pane-pix" in response.get_data(as_text=True)
    assert "qrcode-generator" in response.get_data(as_text=True)
    assert "jsQR" not in response.get_data(as_text=True)
    assert "@zxing" not in response.get_data(as_text=True)
    assert 'id="pix_key"' in response.get_data(as_text=True)
    assert 'id="edit_pix_key"' in response.get_data(as_text=True)
    assert 'id="pix_payload"' in response.get_data(as_text=True)
    assert 'id="pix_qr_image"' in response.get_data(as_text=True)
    assert 'id="pix_image"' in response.get_data(as_text=True)
    assert 'id="edit_pix_image"' in response.get_data(as_text=True)


def test_bills_2(logged_client):
    """Testing /bills/ route"""

    response = logged_client.get("/bills/")

    assert response.status_code == 200


def test_bills_requires_login(client):
    """Unauthenticated users should be redirected to login"""

    response = client.get("/bills")

    assert response.status_code == 302
    assert "/login" in response.headers["Location"]
