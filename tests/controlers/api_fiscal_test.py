"""Tests for the fiscal configuration API (NFC-e phase 1)."""


def _make_product(name="Sem fiscal", ncm=None, cfop=None, csosn=None):
    from decimal import Decimal

    from billflux.infra.repository.product_repository import ProductRepository

    return ProductRepository().insert_product(
        name=name,
        price=Decimal("10"),
        stock_quantity=1,
        ncm=ncm,
        cfop=cfop,
        csosn=csosn,
    )


def test_fiscal_status_requires_login(client):
    assert client.get("/api/fiscal/status").status_code == 401
    assert client.get("/api/fiscal/pending-products").status_code == 401


def test_fiscal_status_reports_missing_config(logged_client, monkeypatch):
    """Sem token/IE e com produto sem NCM, não está pronto para emitir."""

    monkeypatch.delenv("BRASILNFE_TOKEN", raising=False)
    _make_product("Sem NCM")

    payload = logged_client.get("/api/fiscal/status").get_json()

    assert payload["provider"] == "brasilnfe"
    assert payload["environment"] == "homologacao"
    assert payload["token_configured"] is False
    assert payload["ready"] is False
    assert "token" in payload["missing"]
    assert "produtos_sem_dados_fiscais" in payload["missing"]
    assert payload["pending_products"] >= 1


def test_fiscal_status_ready_when_everything_is_set(logged_client, monkeypatch):
    """Com token, CNPJ, IE e produtos fiscais completos, fica pronto."""

    monkeypatch.setenv("BRASILNFE_TOKEN", "token-de-teste")
    _make_product("Completo", ncm="22021000", cfop="5102", csosn="102")

    from billflux.infra.repository.settings_repository import SettingsRepository

    SettingsRepository().set_many(
        {
            "company.cnpj": "11.222.333/0001-81",
            "fiscal.ie": "1234567890",
            "fiscal.crt": "1",
        }
    )

    payload = logged_client.get("/api/fiscal/status").get_json()

    assert payload["token_configured"] is True
    assert payload["emitente"]["cnpj"] == "11.222.333/0001-81"
    assert payload["emitente"]["ie"] == "1234567890"
    assert payload["ready"] is True
    assert payload["missing"] == []
    assert payload["pending_products"] == 0


def test_fiscal_pending_products_lists_only_ncm(logged_client):
    complete = _make_product("Só NCM", ncm="22021000")
    missing = _make_product("Sem NCM")

    payload = logged_client.get("/api/fiscal/pending-products").get_json()

    ids = {entry["id"]: entry for entry in payload["products"]}
    assert complete.id not in ids
    assert ids[missing.id]["missing"] == ["ncm"]


def test_fiscal_pending_products_flags_invalid_ncm(logged_client):
    """NCM fora da tabela vigente também entra como pendência."""

    invalid = _make_product("NCM inexistente", ncm="12345678")

    payload = logged_client.get("/api/fiscal/pending-products").get_json()

    ids = {entry["id"]: entry for entry in payload["products"]}
    assert ids[invalid.id]["missing"] == ["ncm_invalido"]
