"""Testes de contrato do adapter Brasil NFe (sem chamar a SEFAZ)."""

import base64
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from billflux.services.fiscal.base import (
    FiscalItem,
    FiscalPayment,
    FiscalRequest,
    FiscalTransportError,
    STATUS_AUTHORIZED,
    STATUS_AWAITING,
    STATUS_DENIED,
    STATUS_REJECTED,
)
from billflux.services.fiscal.brasilnfe import BrasilNFeProvider, _extract_qr_code

ACCESS_KEY = "4" * 44
XML = "<nfe><infNFeSupl><qrCode>https://qr.test/nota</qrCode></infNFeSupl></nfe>"


class Transport:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def __call__(self, url, headers, body, timeout):
        self.calls.append(
            {
                "url": url,
                "headers": headers,
                "body": json.loads(body.decode("utf-8")),
            }
        )
        return self.responses.pop(0)


def _request():
    return FiscalRequest(
        order_id=7,
        identifier="VENDA-7",
        environment="homologacao",
        emitted_at=datetime(2026, 11, 10, 14, 30, tzinfo=timezone(timedelta(hours=-3))),
        items=[
            FiscalItem(
                code="1",
                description="Refrigerante",
                quantity=Decimal("2"),
                unit_price=Decimal("5.50"),
                total=Decimal("11.00"),
                ncm="22021000",
                cfop="5102",
                csosn="102",
            )
        ],
        payments=[FiscalPayment(code="01", amount=Decimal("11.00"))],
        total=Decimal("11.00"),
    )


def test_emit_authorized_decodes_xml_and_qr_code():
    transport = Transport(
        (
            200,
            json.dumps(
                {
                    "Base64Xml": base64.b64encode(XML.encode()).decode(),
                    "Base64File": base64.b64encode(b"%PDF-1.4").decode(),
                    "ReturnNF": {
                        "Ok": True,
                        "ChaveNF": ACCESS_KEY,
                        "NumeroProtocolo": "135260000000001",
                        "Serie": 1,
                        "Numero": 42,
                        "CodStatusRespostaSefaz": 100,
                        "DsStatusRespostaSefaz": "Autorizado o uso da NF-e",
                    },
                    "Avisos": [],
                }
            ),
        )
    )
    provider = BrasilNFeProvider(token="token", transport=transport)

    result = provider.emit(_request())

    assert result.ok is True
    assert result.status == STATUS_AUTHORIZED
    assert result.access_key == ACCESS_KEY
    assert result.number == 42
    assert result.xml == XML
    assert result.qr_code_url == "https://qr.test/nota"
    assert result.danfe == base64.b64encode(b"%PDF-1.4").decode()

    call = transport.calls[0]
    assert call["url"].endswith("/fiscal/EnviarNotaFiscal")
    assert call["headers"]["Token"] == "token"
    assert call["body"]["ModeloDocumento"] == 65
    assert call["body"]["TipoAmbiente"] == 2
    assert call["body"]["Produtos"][0]["NCM"] == "22021000"
    imposto = call["body"]["Produtos"][0]["Imposto"]
    assert imposto["PIS"] == {"CodSituacaoTributaria": "49"}
    assert imposto["COFINS"] == {"CodSituacaoTributaria": "49"}


def test_qr_code_remove_cdata_do_xml():
    xml = (
        "<nfe><infNFeSupl><qrCode>"
        "<![CDATA[https://qr.test/nota?a=1&b=2]]>"
        "</qrCode></infNFeSupl></nfe>"
    )

    assert _extract_qr_code(xml) == "https://qr.test/nota?a=1&b=2"


def test_item_payload_regime_normal_destaca_pis_cofins():
    item = FiscalItem(
        code="1",
        description="Refrigerante",
        quantity=Decimal("2"),
        unit_price=Decimal("5.50"),
        total=Decimal("11.00"),
        ncm="22021000",
        cfop="5102",
        cst="00",
    )

    payload = BrasilNFeProvider._item_payload(item)

    assert payload["Imposto"]["PIS"] == {
        "CodSituacaoTributaria": "01",
        "Aliquota": 0.65,
    }
    assert payload["Imposto"]["COFINS"] == {
        "CodSituacaoTributaria": "01",
        "Aliquota": 3.0,
    }


def test_emit_rejection_comes_as_http_200():
    transport = Transport(
        (
            200,
            json.dumps(
                {
                    "ReturnNF": {
                        "Ok": False,
                        "CodStatusRespostaSefaz": 539,
                        "DsStatusRespostaSefaz": "Rejeição: duplicidade de NF-e",
                    },
                    "Error": "",
                }
            ),
        )
    )
    provider = BrasilNFeProvider(token="token", transport=transport)

    result = provider.emit(_request())

    assert result.ok is False
    assert result.status == STATUS_REJECTED
    assert result.error_code == "539"
    assert "duplicidade" in result.error_message


def test_emit_denied_and_processing_codes():
    denied = Transport(
        (
            200,
            json.dumps(
                {
                    "ReturnNF": {
                        "Ok": False,
                        "CodStatusRespostaSefaz": 110,
                        "DsStatusRespostaSefaz": "Uso denegado",
                    }
                }
            ),
        )
    )
    assert (
        BrasilNFeProvider(token="token", transport=denied).emit(_request()).status
        == STATUS_DENIED
    )

    processing = Transport(
        (
            200,
            json.dumps(
                {
                    "ReturnNF": {
                        "Ok": False,
                        "CodStatusRespostaSefaz": 105,
                        "DsStatusRespostaSefaz": "Lote em processamento",
                    }
                }
            ),
        )
    )
    assert (
        BrasilNFeProvider(token="token", transport=processing).emit(_request()).status
        == STATUS_AWAITING
    )


def test_http_error_raises_transport_error():
    provider = BrasilNFeProvider(
        token="token", transport=Transport((500, '{"Error": "instabilidade"}'))
    )

    with pytest.raises(FiscalTransportError, match="HTTP 500"):
        provider.emit(_request())


def test_cancel_reads_event_status():
    transport = Transport(
        (
            200,
            json.dumps(
                {
                    "Status": 1,
                    "CodStatusRespostaSefaz": 135,
                    "NuProtocolo": "135260000000009",
                    "DsMotivo": "Evento registrado e vinculado a NF-e",
                    "Error": "",
                }
            ),
        )
    )
    provider = BrasilNFeProvider(token="token", transport=transport)

    result = provider.cancel(ACCESS_KEY, "Cliente desistiu da compra do item.")

    assert result.ok is True
    assert result.protocol == "135260000000009"
    assert transport.calls[0]["body"] == {
        "ChaveNF": ACCESS_KEY,
        "Justificativa": "Cliente desistiu da compra do item.",
    }


def test_cancel_refused_returns_message():
    provider = BrasilNFeProvider(
        token="token",
        transport=Transport(
            (
                200,
                json.dumps(
                    {
                        "Status": 3,
                        "CodStatusRespostaSefaz": 501,
                        "Error": "Prazo de cancelamento expirado.",
                    }
                ),
            )
        ),
    )

    result = provider.cancel(ACCESS_KEY, "Cliente desistiu da compra do item.")

    assert result.ok is False
    assert "expirado" in result.error_message


def test_query_by_identifier_maps_status():
    transport = Transport(
        (
            200,
            json.dumps(
                {
                    "Encontrada": True,
                    "status": 1,
                    "Nota": {
                        "Status": 1,
                        "Chave": ACCESS_KEY,
                        "NumeroProtocolo": "135",
                        "Serie": 1,
                        "Numero": 10,
                        "Base64Xml": base64.b64encode(XML.encode()).decode(),
                    },
                }
            ),
        )
    )
    provider = BrasilNFeProvider(token="token", transport=transport)

    result = provider.query(identifier="VENDA-7")

    assert result.found is True
    assert result.status == STATUS_AUTHORIZED
    assert result.access_key == ACCESS_KEY
    assert result.qr_code_url == "https://qr.test/nota"
    assert transport.calls[0]["body"]["IdentificadorInterno"] == "VENDA-7"
    assert transport.calls[0]["body"]["RetornarArquivos"] is True


def test_download_accepts_raw_base64_string():
    transport = Transport((200, json.dumps(base64.b64encode(b"<nfe/>").decode())))
    provider = BrasilNFeProvider(token="token", transport=transport)

    assert provider.download_xml(ACCESS_KEY) == b"<nfe/>"
    assert transport.calls[0]["body"]["FileType"] == 1


def test_test_connection_reports_sefaz_status():
    transport = Transport(
        (
            200,
            json.dumps(
                {
                    "status": 0,
                    "CodStatusRespostaSefaz": 107,
                    "DsStatusRespostaSefaz": "Serviço em Operação",
                }
            ),
        )
    )
    provider = BrasilNFeProvider(token="token", transport=transport)

    result = provider.test_connection()

    assert result.ok is True
    assert result.code == "107"
    assert transport.calls[0]["body"] == {"ModeloDocumento": 65}
