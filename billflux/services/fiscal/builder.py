"""Monta o DTO fiscal a partir de uma venda do PDV."""

import re
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Dict, Optional

from billflux.services.credit import is_fiado_name
from billflux.services.fiscal.base import (
    FiscalCustomer,
    FiscalItem,
    FiscalPayment,
    FiscalRequest,
    FiscalValidationError,
)
from billflux.services.text_normalize import strip_accents

#: Fuso de Brasília/Paraná (sem horário de verão desde 2019).
BRT = timezone(timedelta(hours=-3))

DEFAULT_CFOP = "5102"
DEFAULT_CFOP_ST = "5405"
DEFAULT_CSOSN = "102"
DEFAULT_CST = "00"
DEFAULT_ORIGIN = 0
DEFAULT_UNIT = "UN"

ST_TAX_CODES = {"201", "202", "203", "500", "900", "10", "30", "60", "70", "90"}

PAYMENT_CODES = {
    "dinheiro": "01",
    "cheque": "02",
    "cartao de credito": "03",
    "cartao credito": "03",
    "credito": "03",
    "cartao de debito": "04",
    "cartao debito": "04",
    "debito": "04",
    "cartao da loja": "05",
    "vale alimentacao": "10",
    "vale refeicao": "11",
    "vr": "11",
    "va": "11",
    "vr/va": "11",
    "vale combustivel": "13",
    "boleto": "15",
    "deposito": "16",
    "deposito bancario": "16",
    "pix dinamico": "17",
    "transferencia": "18",
    "transferencia bancaria": "18",
    "ted": "18",
    "doc": "18",
    "pix": "20",
    "credito em loja": "21",
    "fiado": "99",
    "crediario": "99",
}


def normalize_name(value: Optional[str]) -> str:
    return re.sub(r"\s+", " ", strip_accents(value or "").strip().lower())


def payment_code(name: Optional[str]) -> str:
    return PAYMENT_CODES.get(normalize_name(name), "99")


def only_digits(value: Optional[str]) -> str:
    return re.sub(r"\D", "", str(value or ""))


def valid_gtin(value: Optional[str]) -> Optional[str]:
    """Devolve o GTIN quando o dígito verificador confere; senão None."""

    digits = only_digits(value)
    if len(digits) not in (8, 12, 13, 14):
        return None
    body, check = digits[:-1], int(digits[-1])
    total = 0
    for index, char in enumerate(reversed(body)):
        total += int(char) * (3 if index % 2 == 0 else 1)
    return digits if (10 - total % 10) % 10 == check else None


def default_emission_time() -> datetime:
    return datetime.now(BRT)


def build_request(
    order,
    items,
    products: Dict[int, object],
    methods: Dict[int, object],
    customer: Optional[object],
    config,
    payment_rows: Optional[list] = None,
    emitted_at: Optional[datetime] = None,
) -> FiscalRequest:
    """Valida a venda e devolve a nota pronta para o provedor.

    Somente o NCM bloqueia a emissão: CFOP/CSOSN/origem/unidade têm padrões.
    """

    missing_ncm = []
    fiscal_items = []

    for item in items:
        product = products.get(item.product_id)
        if product is None:
            raise FiscalValidationError(
                "Há um item da venda cujo produto não existe mais."
            )

        ncm = only_digits(getattr(product, "ncm", ""))
        if len(ncm) != 8:
            missing_ncm.append(product.name)
            continue

        quantity = Decimal(str(item.quantity or 0))
        unit_price = Decimal(str(item.unit_price or 0))

        if config.crt in ("1", "4"):
            tax_code = only_digits(getattr(product, "csosn", "")) or DEFAULT_CSOSN
            csosn, cst = tax_code, ""
        else:
            tax_code = only_digits(getattr(product, "cst", "")) or DEFAULT_CST
            csosn, cst = "", tax_code

        cfop = only_digits(getattr(product, "cfop", ""))
        if len(cfop) != 4:
            cfop = DEFAULT_CFOP_ST if tax_code in ST_TAX_CODES else DEFAULT_CFOP

        unit = (getattr(product, "fiscal_unit", "") or DEFAULT_UNIT).strip().upper()
        if not unit or len(unit) > 6:
            unit = DEFAULT_UNIT

        cest = only_digits(getattr(product, "cest", ""))
        origin = int(getattr(product, "origem", DEFAULT_ORIGIN) or DEFAULT_ORIGIN)
        if origin < 0 or origin > 8:
            origin = DEFAULT_ORIGIN

        fiscal_items.append(
            FiscalItem(
                code=str(product.id),
                description=product.name,
                quantity=quantity,
                unit_price=unit_price,
                total=(unit_price * quantity).quantize(Decimal("0.01")),
                ncm=ncm,
                cfop=cfop,
                unit=unit,
                ean=valid_gtin(getattr(product, "barcode", "")) or "SEM GTIN",
                cest=cest if len(cest) == 7 else "",
                csosn=csosn,
                cst=cst,
                origin=origin,
            )
        )

    if missing_ncm:
        names = ", ".join(missing_ncm)
        raise FiscalValidationError(
            f"Produtos sem NCM não podem ser emitidos: {names}."
        )
    if not fiscal_items:
        raise FiscalValidationError("A venda não possui itens para emitir.")

    subtotal = sum((item.total for item in fiscal_items), Decimal("0"))
    discount = Decimal(str(order.discount or 0))
    if discount < 0:
        discount = Decimal("0")
    if discount > subtotal:
        discount = subtotal

    if not payment_rows:
        payment_rows = [(order.payment_method_id, order.total)]

    payments = []
    for method_id, amount in payment_rows:
        method = methods.get(method_id)
        name = method.name if method else ""
        payments.append(
            FiscalPayment(
                code=payment_code(name),
                amount=Decimal(str(amount or 0)),
                description=name if payment_code(name) == "99" else "",
                at_sight=not is_fiado_name(name),
            )
        )

    recipient = None
    if customer is not None:
        document = only_digits(getattr(customer, "cpf_cnpj", ""))
        if len(document) in (11, 14):
            recipient = FiscalCustomer(
                name=customer.name or "Consumidor final",
                document=document,
                email=(customer.email or "").strip(),
                phone=only_digits(customer.phone),
            )

    return FiscalRequest(
        order_id=order.id,
        identifier=f"VENDA-{order.id}",
        environment=config.environment,
        emitted_at=emitted_at or default_emission_time(),
        items=fiscal_items,
        payments=payments,
        total=Decimal(str(order.total or 0)),
        discount=discount,
        customer=recipient,
        notes=(order.obs or "").strip(),
    )
