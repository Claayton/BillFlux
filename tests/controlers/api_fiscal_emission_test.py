"""Testes da emissão NFC-e (Fase 2) com provedor fake."""

import base64
from decimal import Decimal

import pytest

from billflux.infra.repository.customer_repository import CustomerRepository
from billflux.infra.repository.fiscal_document_repository import (
    FiscalDocumentRepository,
)
from billflux.infra.repository.order_repository import OrderRepository
from billflux.infra.repository.payment_method_repository import (
    PaymentMethodRepository,
)
from billflux.infra.repository.product_repository import ProductRepository
from billflux.infra.repository.settings_repository import SettingsRepository
from billflux.services.fiscal.base import (
    FiscalCancelResult,
    FiscalCancellationError,
    FiscalConnectionResult,
    FiscalProvider,
    FiscalQueryResult,
    FiscalResult,
    FiscalTransportError,
    FiscalValidationError,
    STATUS_AUTHORIZED,
    STATUS_CANCELLED,
    STATUS_PENDING,
    STATUS_REJECTED,
)
from billflux.services.fiscal.builder import only_digits, valid_gtin
from billflux.services.fiscal.brasilnfe import BrasilNFeProvider
from billflux.services.fiscal.config import FiscalConfig
from billflux.services.fiscal.service import FiscalService

ACCESS_KEY = "4" * 44


class FakeProvider(FiscalProvider):
    name = "fake"

    def __init__(self):
        self.emit_result = FiscalResult(
            ok=True,
            status=STATUS_AUTHORIZED,
            access_key=ACCESS_KEY,
            protocol="135260000000001",
            series=1,
            number=10,
            xml="<nfe><infNFeSupl><qrCode>https://qr.test/1</qrCode></infNFeSupl></nfe>",
            qr_code_url="https://qr.test/1",
        )
        self.cancel_result = FiscalCancelResult(
            ok=True, status=STATUS_CANCELLED, protocol="135260000000002"
        )
        self.query_result = None
        self.connection_result = FiscalConnectionResult(
            ok=True, code="107", message="Serviço em Operação"
        )
        self.emit_calls = []
        self.cancel_calls = []
        self.query_calls = []
        self.download_calls = []

    def emit(self, request):
        self.emit_calls.append(request)
        if isinstance(self.emit_result, Exception):
            raise self.emit_result
        return self.emit_result

    def cancel(self, access_key, justification):
        self.cancel_calls.append((access_key, justification))
        if isinstance(self.cancel_result, Exception):
            raise self.cancel_result
        return self.cancel_result

    def query(self, access_key="", identifier=""):
        self.query_calls.append((access_key, identifier))
        if isinstance(self.query_result, Exception):
            raise self.query_result
        return self.query_result or FiscalQueryResult(found=False)

    def download_xml(self, access_key):
        self.download_calls.append(("xml", access_key))
        return b"<nfe/>"

    def download_danfe(self, access_key):
        self.download_calls.append(("danfe", access_key))
        return b"%PDF-1.4 teste"

    def test_connection(self):
        if isinstance(self.connection_result, Exception):
            raise self.connection_result
        return self.connection_result


def _config(**overrides):
    data = {
        "provider": "brasilnfe",
        "environment": "homologacao",
        "token": "token-de-teste",
        "cnpj": "11.222.333/0001-81",
        "ie": "1234567890",
        "crt": "1",
        "print_mode": "thermal",
        "auto_retry": True,
    }
    data.update(overrides)
    return FiscalConfig(**data)


def _make_order(
    name="Item NFC-e",
    price="10.00",
    qty=2,
    ncm="12345678",
    barcode=None,
    customer_id=None,
    payments=None,
    discount=None,
):
    product = ProductRepository().insert_product(
        name=name,
        price=Decimal(price),
        stock_quantity=10,
        ncm=ncm,
        cfop="5102",
        csosn="102",
        fiscal_unit="UN",
        barcode=barcode,
    )
    method = PaymentMethodRepository().get_active_methods()[0]
    order = OrderRepository().create_order(
        [(product.id, qty)],
        method.id,
        payments=payments,
        customer_id=customer_id,
        discount=discount,
    )
    return product, method, order


def _csrf(client):
    return client.get("/api/auth/csrf").get_json()["csrf_token"]


def _prepare_api(monkeypatch, provider):
    monkeypatch.setenv("BRASILNFE_TOKEN", "token-de-teste")
    SettingsRepository().set_many(
        {
            "company.cnpj": "11.222.333/0001-81",
            "fiscal.ie": "1234567890",
            "fiscal.crt": "1",
            "fiscal.environment": "homologacao",
            "fiscal.auto_retry": "true",
        }
    )
    monkeypatch.setattr(
        "billflux.services.fiscal.service.get_provider",
        lambda config: provider,
    )


# --------------------------------------------------------------- Service core
def test_emit_authorized_persists_protocol_and_xml():
    provider = FakeProvider()
    service = FiscalService(provider=provider, config=_config())
    _, method, order = _make_order()

    document = service.emitir(order.id)

    assert document.status == STATUS_AUTHORIZED
    assert document.access_key == ACCESS_KEY
    assert document.protocol == "135260000000001"
    assert document.xml.startswith("<nfe>")
    assert document.authorized_at is not None

    request = provider.emit_calls[0]
    assert request.identifier == f"VENDA-{order.id}"
    assert request.environment == "homologacao"
    assert request.items[0].ncm == "12345678"
    assert request.items[0].cfop == "5102"
    assert request.items[0].csosn == "102"
    assert request.items[0].ean == "SEM GTIN"
    assert request.payments[0].code == "01"
    assert request.total == Decimal("20.00")
    assert method.name == "Dinheiro"


def test_emit_without_ncm_stays_pending_and_does_not_call_provider():
    provider = FakeProvider()
    service = FiscalService(provider=provider, config=_config())
    product, _, order = _make_order(ncm=None)

    document = service.emitir(order.id)

    assert document.status == STATUS_PENDING
    assert "NCM" in document.error_message
    assert product.name in document.error_message
    assert provider.emit_calls == []
    assert FiscalDocumentRepository().get_by_order(order.id).id == document.id


def test_emit_rejected_records_sefaz_error():
    provider = FakeProvider()
    provider.emit_result = FiscalResult(
        ok=False,
        status=STATUS_REJECTED,
        error_code="539",
        error_message="Rejeição: duplicidade de NF-e",
    )
    service = FiscalService(provider=provider, config=_config())
    _, _, order = _make_order()

    document = service.emitir(order.id)

    assert document.status == STATUS_REJECTED
    assert document.error_code == "539"
    assert "duplicidade" in document.error_message
    assert document.retry_count == 1


def test_emit_transport_error_then_query_avoids_duplicate():
    provider = FakeProvider()
    provider.emit_result = FiscalTransportError("timeout")
    service = FiscalService(provider=provider, config=_config())
    _, _, order = _make_order()

    pending = service.emitir(order.id)
    assert pending.status == STATUS_PENDING
    assert pending.retry_count == 1

    # A nota foi autorizada no provedor, mas a resposta se perdeu.
    provider.query_result = FiscalQueryResult(
        found=True,
        status=STATUS_AUTHORIZED,
        access_key=ACCESS_KEY,
        protocol="135260000000003",
        series=1,
        number=11,
        xml="<nfe/>",
    )

    document = service.reenviar(pending.id)

    assert document.status == STATUS_AUTHORIZED
    assert document.protocol == "135260000000003"
    assert len(provider.emit_calls) == 1
    assert provider.query_calls[-1] == ("", f"VENDA-{order.id}")


def test_cancel_authorized_note():
    provider = FakeProvider()
    service = FiscalService(provider=provider, config=_config())
    _, _, order = _make_order()
    document = service.emitir(order.id)

    cancelled = service.cancelar(document.id, "Cliente desistiu da compra do produto.")

    assert cancelled.status == STATUS_CANCELLED
    assert cancelled.cancelled_at is not None
    assert "desistiu" in cancelled.cancel_reason
    assert provider.cancel_calls == [
        (ACCESS_KEY, "Cliente desistiu da compra do produto.")
    ]


def test_cancel_refused_by_sefaz_keeps_note_authorized():
    provider = FakeProvider()
    service = FiscalService(provider=provider, config=_config())
    _, _, order = _make_order()
    document = service.emitir(order.id)

    provider.cancel_result = FiscalCancelResult(
        ok=False,
        status=STATUS_REJECTED,
        error_code="501",
        error_message="Prazo de cancelamento expirado.",
    )

    with pytest.raises(FiscalCancellationError, match="Prazo"):
        service.cancelar(document.id, "Cliente desistiu da compra do produto.")

    assert FiscalDocumentRepository().get(document.id).status == STATUS_AUTHORIZED


def test_cancel_requires_minimum_justification():
    provider = FakeProvider()
    service = FiscalService(provider=provider, config=_config())
    _, _, order = _make_order()
    document = service.emitir(order.id)

    with pytest.raises(FiscalValidationError, match="15 caracteres"):
        service.cancelar(document.id, "curta")


# -------------------------------------------------------------- Payload mapping
def test_payload_maps_fiado_discount_and_customer():
    method = next(
        item for item in PaymentMethodRepository().get_methods() if item.name == "Fiado"
    )
    customer = CustomerRepository().insert_customer(
        name="Cliente Teste",
        cpf_cnpj="529.982.247-25",
        email="cliente@teste.com",
    )
    product, _, order = _make_order(
        price="10.00",
        qty=2,
        customer_id=customer.id,
        discount=Decimal("2.00"),
        payments=None,
    )
    # Reabre a venda com a forma fiado.
    OrderRepository().cancel_order(order.id)
    order = OrderRepository().create_order(
        [(product.id, 2)],
        method.id,
        customer_id=customer.id,
        discount=Decimal("2.00"),
    )

    service = FiscalService(
        provider=BrasilNFeProvider(token="token-de-teste"), config=_config()
    )
    request = service._build_request(order, service.config)
    payload = service.provider.build_payload(request)

    assert payload["ModeloDocumento"] == 65
    assert payload["TipoAmbiente"] == 2
    assert payload["ValorTotal"] == 18.0
    assert payload["ValorDesconto"] == 2.0
    assert payload["Cliente"]["CpfCnpj"] == "52998224725"
    assert payload["Pagamentos"][0]["FormaPagamento"] == "99"
    assert payload["Pagamentos"][0]["IndicadorPagamento"] == 1
    assert payload["Pagamentos"][0]["Descricao"] == "Fiado"
    assert payload["Produtos"][0]["CFOP"] == 5102
    assert payload["Produtos"][0]["Imposto"]["ICMS"]["CodSituacaoTributaria"] == "102"


def test_payload_split_payments_and_valid_gtin():
    methods = PaymentMethodRepository().get_active_methods()
    cash = next(item for item in methods if item.name == "Dinheiro")
    pix = next(item for item in methods if item.name == "PIX")
    product = ProductRepository().insert_product(
        name="Refrigerante",
        price=Decimal("10.00"),
        stock_quantity=10,
        ncm="22021000",
        cfop="5102",
        csosn="102",
        barcode="7891000315507",
    )
    order = OrderRepository().create_order(
        [(product.id, 2)],
        cash.id,
        payments=[(cash.id, Decimal("12.00")), (pix.id, Decimal("8.00"))],
    )

    service = FiscalService(
        provider=BrasilNFeProvider(token="token-de-teste"), config=_config()
    )
    request = service._build_request(order, service.config)
    payload = service.provider.build_payload(request)

    assert [p["FormaPagamento"] for p in payload["Pagamentos"]] == ["01", "20"]
    assert [p["VlPago"] for p in payload["Pagamentos"]] == [12.0, 8.0]
    assert payload["Produtos"][0]["EAN"] == "7891000315507"


def test_gtin_helpers():
    assert valid_gtin("7891000315507") == "7891000315507"
    assert valid_gtin("7891000315508") is None
    assert valid_gtin("123") is None
    assert only_digits("529.982.247-25") == "52998224725"


# --------------------------------------------------------------------- API
def test_api_emit_and_query_document(logged_client, monkeypatch):
    provider = FakeProvider()
    _prepare_api(monkeypatch, provider)
    _, _, order = _make_order()

    response = logged_client.post(
        "/api/fiscal/emitir",
        json={"order_id": order.id},
        headers={"X-CSRFToken": _csrf(logged_client)},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert body["document"]["status"] == STATUS_AUTHORIZED
    assert body["document"]["has_xml"] is True

    by_order = logged_client.get(f"/api/fiscal/vendas/{order.id}").get_json()
    assert by_order["document"]["id"] == body["document"]["id"]


def test_api_pending_documents_and_reenviar(logged_client, monkeypatch):
    provider = FakeProvider()
    provider.emit_result = FiscalTransportError("rede fora")
    _prepare_api(monkeypatch, provider)
    _, _, order = _make_order()

    response = logged_client.post(
        "/api/fiscal/emitir",
        json={"order_id": order.id},
        headers={"X-CSRFToken": _csrf(logged_client)},
    )
    assert response.status_code == 200
    assert response.get_json()["ok"] is False

    pending = logged_client.get("/api/fiscal/pendentes").get_json()
    assert pending["count"] == 1
    assert pending["documents"][0]["order_id"] == order.id

    provider.emit_result = FiscalResult(
        ok=True,
        status=STATUS_AUTHORIZED,
        access_key=ACCESS_KEY,
        protocol="135",
        xml="<nfe/>",
    )
    document_id = pending["documents"][0]["id"]
    resent = logged_client.post(
        f"/api/fiscal/{document_id}/reenviar",
        headers={"X-CSRFToken": _csrf(logged_client)},
    )
    assert resent.status_code == 200
    assert resent.get_json()["document"]["status"] == STATUS_AUTHORIZED


def test_api_banner_includes_rejected_and_bulk_retries(logged_client, monkeypatch):
    provider = FakeProvider()
    provider.emit_result = FiscalResult(
        ok=False,
        status=STATUS_REJECTED,
        error_code="462",
        error_message="CSC não cadastrado",
    )
    _prepare_api(monkeypatch, provider)
    _, _, order = _make_order()

    response = logged_client.post(
        "/api/fiscal/emitir",
        json={"order_id": order.id},
        headers={"X-CSRFToken": _csrf(logged_client)},
    )
    assert response.status_code == 200
    assert response.get_json()["document"]["status"] == STATUS_REJECTED

    banner = logged_client.get("/api/fiscal/pendentes").get_json()
    assert banner["count"] == 1
    assert banner["documents"][0]["status"] == STATUS_REJECTED

    provider.emit_result = FiscalResult(
        ok=True,
        status=STATUS_AUTHORIZED,
        access_key=ACCESS_KEY,
        protocol="135",
        xml="<nfe/>",
    )
    resent = logged_client.post(
        "/api/fiscal/reenviar-pendentes",
        json={"limit": 50},
        headers={"X-CSRFToken": _csrf(logged_client)},
    )
    assert resent.status_code == 200
    assert resent.get_json()["authorized"] == 1


def test_api_cancel_validates_justification(logged_client, monkeypatch):
    provider = FakeProvider()
    _prepare_api(monkeypatch, provider)
    _, _, order = _make_order()
    document = FiscalService().emitir(order.id)

    response = logged_client.post(
        f"/api/fiscal/{document.id}/cancelar",
        json={"justificativa": "curta"},
        headers={"X-CSRFToken": _csrf(logged_client)},
    )
    assert response.status_code == 400
    assert "15 caracteres" in response.get_json()["error"]


def test_api_download_xml_and_danfe(logged_client, monkeypatch):
    provider = FakeProvider()
    _prepare_api(monkeypatch, provider)
    _, _, order = _make_order()
    document = FiscalService().emitir(order.id)
    FiscalDocumentRepository().update(document.id, xml=None, danfe=None)

    xml = logged_client.get(f"/api/fiscal/{document.id}/xml")
    assert xml.status_code == 200
    assert xml.data == b"<nfe/>"

    danfe = logged_client.get(f"/api/fiscal/{document.id}/danfe")
    assert danfe.status_code == 200
    assert danfe.data.startswith(b"%PDF")


def test_api_sale_cancel_cancels_note(logged_client, monkeypatch):
    provider = FakeProvider()
    _prepare_api(monkeypatch, provider)
    _, _, order = _make_order()
    document = FiscalService().emitir(order.id)

    response = logged_client.post(
        f"/api/sales/orders/{order.id}/cancel",
        json={"reason": "Cliente desistiu da compra do item."},
        headers={"X-CSRFToken": _csrf(logged_client)},
    )

    assert response.status_code == 200
    assert OrderRepository().get_order(order.id).cancelled is True
    assert FiscalDocumentRepository().get(document.id).status == STATUS_CANCELLED


def test_api_sale_cancel_blocked_when_sefaz_refuses(logged_client, monkeypatch):
    provider = FakeProvider()
    _prepare_api(monkeypatch, provider)
    _, _, order = _make_order()
    document = FiscalService().emitir(order.id)

    provider.cancel_result = FiscalCancelResult(
        ok=False,
        error_message="Prazo de cancelamento expirado.",
    )

    response = logged_client.post(
        f"/api/sales/orders/{order.id}/cancel",
        json={"reason": "Cliente desistiu da compra do item."},
        headers={"X-CSRFToken": _csrf(logged_client)},
    )

    assert response.status_code == 400
    assert "Prazo" in response.get_json()["error"]
    assert OrderRepository().get_order(order.id).cancelled is False
    assert FiscalDocumentRepository().get(document.id).status == STATUS_AUTHORIZED


def test_api_test_connection(logged_client, monkeypatch):
    provider = FakeProvider()
    _prepare_api(monkeypatch, provider)

    response = logged_client.post(
        "/api/fiscal/testar-conexao",
        headers={"X-CSRFToken": _csrf(logged_client)},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["ok"] is True
    assert body["code"] == "107"
