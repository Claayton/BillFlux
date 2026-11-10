"""Adapter Brasil NFe (API 2.0) para NFC-e.

Contrato: https://www.brasilnfe.com.br/api
Autenticação: header ``Token`` com o token da empresa.
"""

import base64
import html
import json
import re
import urllib.error
import urllib.request
from decimal import Decimal
from typing import Optional

from billflux.services.fiscal.base import (
    FiscalCancelResult,
    FiscalConnectionResult,
    FiscalProvider,
    FiscalQueryResult,
    FiscalRequest,
    FiscalResult,
    FiscalTransportError,
    STATUS_AUTHORIZED,
    STATUS_AWAITING,
    STATUS_CANCELLED,
    STATUS_DENIED,
    STATUS_REJECTED,
)

BASE_URL = "https://api.brasilnfe.com.br/services"
DEFAULT_TIMEOUT = 60

#: Códigos da SEFAZ que ainda não são resultado final.
PROCESSING_CODES = {103, 105, 108, 109}
#: Códigos de uso denegado.
DENIED_CODES = {110, 301, 302}

_CANCEL_OK_CODES = {135, 155}
_QR_CODE_RE = re.compile(r"<qrCode>(.*?)</qrCode>", re.DOTALL)


def _money(value) -> float:
    return float(Decimal(str(value or 0)).quantize(Decimal("0.01")))


def _quantity(value) -> float:
    return float(Decimal(str(value or 0)).quantize(Decimal("0.0001")))


def _as_int(value) -> Optional[int]:
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _decode_xml(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        return base64.b64decode(value).decode("utf-8", errors="replace")
    except (ValueError, TypeError):
        return None


def _decode_base64(value) -> Optional[str]:
    raw = str(value or "").strip().strip('"')
    return raw or None


def _extract_qr_code(xml: Optional[str]) -> Optional[str]:
    if not xml:
        return None
    match = _QR_CODE_RE.search(xml)
    return html.unescape(match.group(1).strip()) if match else None


def _error_list(data) -> str:
    """Junta os erros de validação do Brasil NFe numa mensagem legível."""

    errors = data.get("erros") or data.get("Erros") or []
    messages = []
    for error in errors:
        if isinstance(error, dict):
            message = (error.get("descricao") or error.get("Descricao") or "").strip()
            correction = (error.get("correcao") or error.get("Correcao") or "").strip()
            if message and correction:
                message = f"{message} ({correction})"
            if message:
                messages.append(message)
        elif error:
            messages.append(str(error))
    return " | ".join(messages)


def _warnings(data) -> list:
    warnings = data.get("Avisos") or data.get("avisos") or []
    return [str(item) for item in warnings if item]


def _urllib_transport(url: str, headers: dict, body: bytes, timeout: int):
    """Transporte HTTP padrão (urllib, sem dependência extra)."""

    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")
        return error.code, detail
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise FiscalTransportError(
            f"Falha de comunicação com o Brasil NFe: {error}"
        ) from error


class BrasilNFeProvider(FiscalProvider):
    """Implementação do provedor Brasil NFe."""

    name = "brasilnfe"

    def __init__(
        self,
        token: str,
        transport=None,
        timeout: int = DEFAULT_TIMEOUT,
        base_url: str = BASE_URL,
    ):
        self.token = (token or "").strip()
        self.transport = transport or _urllib_transport
        self.timeout = timeout
        self.base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------ HTTP
    def _request_json(self, path: str, payload: dict):
        if not self.token:
            raise FiscalTransportError("Token do Brasil NFe não configurado.")

        url = f"{self.base_url}{path}"
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Token": self.token,
            "User-Agent": "BeeFlux/1.0",
        }
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")

        try:
            status, text = self.transport(url, headers, body, self.timeout)
        except FiscalTransportError:
            raise
        except Exception as error:  # transport injetado em testes
            raise FiscalTransportError(
                f"Falha de comunicação com o Brasil NFe: {error}"
            ) from error

        try:
            data = json.loads(text)
        except (TypeError, ValueError) as error:
            raise FiscalTransportError(
                "O Brasil NFe devolveu uma resposta inválida."
            ) from error

        if status >= 400:
            detail = ""
            if isinstance(data, dict):
                detail = (
                    data.get("Error") or _error_list(data) or data.get("error") or ""
                )
            detail = str(detail).strip()
            raise FiscalTransportError(
                f"O Brasil NFe respondeu HTTP {status}."
                + (f" {detail}" if detail else "")
            )

        return data

    def _post(self, path: str, payload: dict) -> dict:
        data = self._request_json(path, payload)
        if not isinstance(data, dict):
            raise FiscalTransportError("O Brasil NFe devolveu uma resposta inválida.")
        return data

    # --------------------------------------------------------------- Payload
    def build_payload(self, request: FiscalRequest) -> dict:
        """Converte o DTO do BeeFlux no JSON do provedor (testável isolado)."""

        payload = {
            "ModeloDocumento": request.model,
            "TipoAmbiente": 2 if request.environment == "homologacao" else 1,
            "Finalidade": 1,
            "ConsumidorFinal": True,
            "CalcularIBPT": True,
            "TipoDanfe": 4,
            "IndicadorPresenca": 1,
            "IdentificadorInterno": request.identifier,
            "DataEmissao": request.emitted_at.isoformat(timespec="seconds"),
            "NaturezaOperacao": "Venda de mercadoria",
            "Produtos": [self._item_payload(item) for item in request.items],
            "Pagamentos": [
                self._payment_payload(payment) for payment in request.payments
            ],
            "ValorTotal": _money(request.total),
        }

        if request.discount and request.discount > 0:
            payload["ValorDesconto"] = _money(request.discount)

        customer = request.customer
        if customer and customer.document:
            payload["Cliente"] = self._customer_payload(customer)

        if request.notes:
            payload["Observacao"] = request.notes

        return payload

    @staticmethod
    def _item_payload(item) -> dict:
        product = {
            "NmProduto": item.description,
            "CodProdutoServico": item.code,
            "EAN": item.ean or "SEM GTIN",
            "NCM": item.ncm,
            "UnidadeComercial": item.unit or "UN",
            "Quantidade": _quantity(item.quantity),
            "ValorUnitario": _money(item.unit_price),
            "ValorTotal": _money(item.total),
            "CFOP": _as_int(item.cfop) or 5102,
            "OrigemProduto": int(item.origin or 0),
            "Imposto": {
                "ICMS": {
                    "CodSituacaoTributaria": item.csosn or item.cst or "102",
                }
            },
        }
        if item.cest and (item.csosn or item.cst) in {
            "201",
            "202",
            "203",
            "500",
            "900",
            "10",
            "30",
            "60",
            "70",
            "90",
        }:
            product["CEST"] = item.cest
        return product

    @staticmethod
    def _payment_payload(payment) -> dict:
        data = {
            "FormaPagamento": payment.code,
            "VlPago": _money(payment.amount),
            "IndicadorPagamento": 0 if getattr(payment, "at_sight", True) else 1,
        }
        if payment.change:
            data["VlTroco"] = _money(payment.change)
        if payment.code == "99" and payment.description:
            data["Descricao"] = payment.description
        return data

    @staticmethod
    def _customer_payload(customer) -> dict:
        data = {
            "CpfCnpj": customer.document,
            "NmCliente": customer.name or "Consumidor final",
            "IndicadorIe": 9,
        }
        contact = {}
        if customer.phone:
            contact["Telefone"] = customer.phone
        if customer.email:
            contact["Email"] = customer.email
        if contact:
            data["Contato"] = contact
        return data

    # -------------------------------------------------------------- Operações
    def emit(self, request: FiscalRequest) -> FiscalResult:
        data = self._post("/fiscal/EnviarNotaFiscal", self.build_payload(request))

        return_nf = data.get("ReturnNF") or {}
        error = (data.get("Error") or "").strip()
        code = _as_int(return_nf.get("CodStatusRespostaSefaz"))
        message = (return_nf.get("DsStatusRespostaSefaz") or error or "").strip()
        access_key = (return_nf.get("ChaveNF") or "").strip()
        protocol = (return_nf.get("NumeroProtocolo") or "").strip()
        xml = _decode_xml(data.get("Base64Xml"))
        danfe = _decode_base64(data.get("Base64File"))
        warnings = _warnings(data)

        ok = bool(return_nf.get("Ok")) and not error
        if ok:
            status = STATUS_AUTHORIZED if access_key and protocol else STATUS_AWAITING
        elif code in DENIED_CODES:
            status = STATUS_DENIED
        elif code in PROCESSING_CODES:
            status = STATUS_AWAITING
        else:
            status = STATUS_REJECTED

        return FiscalResult(
            ok=status == STATUS_AUTHORIZED,
            status=status,
            access_key=access_key,
            protocol=protocol,
            series=_as_int(return_nf.get("Serie")),
            number=_as_int(return_nf.get("Numero")),
            xml=xml,
            danfe=danfe,
            qr_code_url=_extract_qr_code(xml),
            error_code=str(code or ""),
            error_message=message,
            warnings=warnings,
        )

    def cancel(self, access_key: str, justification: str) -> FiscalCancelResult:
        data = self._post(
            "/fiscal/CancelarNotaFiscal",
            {"ChaveNF": access_key, "Justificativa": justification},
        )
        error = (data.get("Error") or "").strip()
        code = _as_int(data.get("CodStatusRespostaSefaz"))
        event_status = _as_int(data.get("Status"))
        message = (data.get("DsMotivo") or error or "").strip()

        ok = (
            event_status == 1
            and not error
            and (code is None or code in _CANCEL_OK_CODES)
        )

        return FiscalCancelResult(
            ok=ok,
            status=STATUS_CANCELLED if ok else STATUS_REJECTED,
            protocol=(data.get("NuProtocolo") or "").strip(),
            error_code=str(code or ""),
            error_message="" if ok else (message or "A SEFAZ recusou o cancelamento."),
            warnings=_warnings(data),
        )

    def query(self, access_key: str = "", identifier: str = "") -> FiscalQueryResult:
        payload = {"RetornarArquivos": True}
        if access_key:
            payload["Chave"] = access_key
        elif identifier:
            payload["IdentificadorInterno"] = identifier
        else:
            raise FiscalTransportError("Informe a chave ou o identificador da nota.")

        data = self._post("/fiscal/ConsultarNotaFiscal", payload)

        if _as_int(data.get("status")) == 2:
            raise FiscalTransportError(
                _error_list(data) or "O Brasil NFe recusou a consulta."
            )

        found = bool(data.get("Encontrada"))
        note = data.get("Nota") or {}
        status_code = _as_int(note.get("Status"))
        status_map = {
            1: STATUS_AUTHORIZED,
            2: STATUS_CANCELLED,
            3: STATUS_REJECTED,
            4: STATUS_DENIED,
            5: STATUS_AWAITING,
        }
        message = (
            note.get("DsStatusResposta") or note.get("DsStatus") or _error_list(data)
        ).strip()
        xml = _decode_xml(note.get("Base64Xml"))
        return FiscalQueryResult(
            found=found,
            status=status_map.get(status_code, ""),
            access_key=(note.get("Chave") or access_key or "").strip(),
            protocol=(note.get("NumeroProtocolo") or "").strip(),
            series=_as_int(note.get("Serie")),
            number=_as_int(note.get("Numero")),
            xml=xml,
            danfe=_decode_base64(note.get("Base64File")),
            qr_code_url=_extract_qr_code(xml),
            error_code=str(_as_int(note.get("CodStatusResposta")) or ""),
            error_message=message,
            warnings=_warnings(data),
        )

    def _download_file(self, access_key: str, file_type: int) -> bytes:
        data = self._request_json(
            "/fiscal/ObterArquivoNotaFiscal",
            {
                "ChaveNF": access_key,
                "FileType": file_type,
                "TipoDocumentoFiscal": 1,
            },
        )

        if isinstance(data, str):
            raw = data
        else:
            raw = data.get("Base64File") or data.get("Base64Xml") or data.get("Arquivo")
        if not raw:
            error = data.get("Error") if isinstance(data, dict) else ""
            raise FiscalTransportError(
                error or "O Brasil NFe não devolveu o arquivo solicitado."
            )
        try:
            return base64.b64decode(str(raw).strip().strip('"'), validate=False)
        except (ValueError, TypeError) as error:
            raise FiscalTransportError(
                "Arquivo inválido devolvido pelo provedor."
            ) from error

    def download_xml(self, access_key: str) -> bytes:
        return self._download_file(access_key, 1)

    def download_danfe(self, access_key: str) -> bytes:
        return self._download_file(access_key, 2)

    def test_connection(self) -> FiscalConnectionResult:
        data = self._post("/fiscal/ConsultarStatusSefaz", {"ModeloDocumento": 65})
        code = _as_int(data.get("CodStatusRespostaSefaz"))
        message = (data.get("DsStatusRespostaSefaz") or "").strip()
        request_status = _as_int(data.get("status"))
        ok = request_status == 0 and code == 107
        if not message:
            message = _error_list(data) or "Não foi possível consultar a SEFAZ."
        return FiscalConnectionResult(
            ok=ok,
            code=str(code or ""),
            message=message,
            warnings=_warnings(data),
        )
