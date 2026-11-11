"""Contratos da emissão fiscal (NFC-e).

O restante do sistema conversa apenas com :class:`FiscalProvider`. Trocar de
provedor significa escrever outro adapter e mudar ``fiscal.provider``.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import List, Optional

MODEL_NFCE = 65

STATUS_PENDING = "pendente"
STATUS_AWAITING = "pendente_autorizacao"
STATUS_AUTHORIZED = "autorizada"
STATUS_REJECTED = "rejeitada"
STATUS_CANCELLED = "cancelada"
STATUS_DENIED = "denegada"

PENDING_STATUSES = frozenset({STATUS_PENDING, STATUS_AWAITING})
ACTIVE_STATUSES = frozenset({STATUS_AUTHORIZED, STATUS_AWAITING})
FINAL_STATUSES = frozenset(
    {STATUS_AUTHORIZED, STATUS_REJECTED, STATUS_CANCELLED, STATUS_DENIED}
)


class FiscalError(Exception):
    """Erro base da camada fiscal."""


class FiscalConfigError(FiscalError):
    """Configuração fiscal incompleta (token, CNPJ, IE, provedor...)."""

    def __init__(self, missing):
        self.missing = list(missing or [])
        message = "Configuração fiscal incompleta: " + ", ".join(self.missing)
        super().__init__(message)


class FiscalValidationError(FiscalError):
    """Dados da venda/produto impedem a emissão (ex.: NCM ausente)."""


class FiscalTransportError(FiscalError):
    """Falha de comunicação com o provedor (rede, HTTP, resposta inválida)."""


class FiscalCancellationError(FiscalError):
    """O provedor/SEFAZ recusou o cancelamento da nota."""


@dataclass
class FiscalPayment:
    """Uma linha de pagamento da nota (tPag)."""

    code: str
    amount: Decimal
    description: str = ""
    at_sight: bool = True
    change: Decimal = Decimal("0")


@dataclass
class FiscalItem:
    """Item da nota, já com os dados fiscais resolvidos."""

    code: str
    description: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    ncm: str
    cfop: str
    unit: str = "UN"
    ean: str = "SEM GTIN"
    cest: str = ""
    csosn: str = ""
    cst: str = ""
    origin: int = 0


@dataclass
class FiscalCustomer:
    """Destinatário identificado (CPF/CNPJ)."""

    name: str
    document: str
    email: str = ""
    phone: str = ""


@dataclass
class FiscalRequest:
    """Nota pronta para transmissão, independente do provedor."""

    order_id: int
    identifier: str
    environment: str
    emitted_at: datetime
    items: List[FiscalItem]
    payments: List[FiscalPayment]
    total: Decimal
    discount: Decimal = Decimal("0")
    customer: Optional[FiscalCustomer] = None
    notes: str = ""
    model: int = MODEL_NFCE


@dataclass
class FiscalResult:
    """Retorno de uma tentativa de emissão."""

    ok: bool
    status: str
    access_key: str = ""
    protocol: str = ""
    series: Optional[int] = None
    number: Optional[int] = None
    xml: Optional[str] = None
    danfe: Optional[str] = None  # PDF/DANFE em Base64
    qr_code_url: Optional[str] = None
    error_code: str = ""
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)


@dataclass
class FiscalCancelResult:
    """Retorno de um pedido de cancelamento."""

    ok: bool
    status: str = ""
    protocol: str = ""
    error_code: str = ""
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)


@dataclass
class FiscalQueryResult:
    """Situação de uma nota consultada no provedor."""

    found: bool
    status: str = ""
    access_key: str = ""
    protocol: str = ""
    series: Optional[int] = None
    number: Optional[int] = None
    xml: Optional[str] = None
    danfe: Optional[str] = None
    qr_code_url: Optional[str] = None
    error_code: str = ""
    error_message: str = ""
    warnings: List[str] = field(default_factory=list)


@dataclass
class FiscalConnectionResult:
    """Resultado do botão "Testar conexão"."""

    ok: bool
    code: str = ""
    message: str = ""
    warnings: List[str] = field(default_factory=list)


class FiscalProvider(ABC):
    """Interface que todo provedor de documentos fiscais deve implementar."""

    name = "base"

    @abstractmethod
    def emit(self, request: FiscalRequest) -> FiscalResult:
        """Transmite a nota e devolve o resultado da SEFAZ."""

    @abstractmethod
    def cancel(self, access_key: str, justification: str) -> FiscalCancelResult:
        """Cancela uma nota autorizada."""

    @abstractmethod
    def query(self, access_key: str = "", identifier: str = "") -> FiscalQueryResult:
        """Consulta uma nota por chave ou identificador interno."""

    @abstractmethod
    def download_xml(self, access_key: str) -> bytes:
        """Baixa o XML autorizado."""

    @abstractmethod
    def download_danfe(self, access_key: str) -> bytes:
        """Baixa o DANFE (PDF ou HTML)."""

    @abstractmethod
    def test_connection(self) -> FiscalConnectionResult:
        """Consulta o status do serviço na SEFAZ."""
