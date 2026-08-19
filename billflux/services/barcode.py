"""Barcode helpers for Brazilian bank and collection (arrecadacao) bills."""

from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, Optional

_FACTOR_BASE = date(1997, 10, 7)
_VALUE_DIVISOR = Decimal("100")


def to_barcode(raw: str) -> Optional[str]:
    """Normalize a typed line into a 44-digit barcode.

    Accepts the 47-digit bank line and the 48-digit collection line, removing
    the check digits of each field. Returns None when the input does not form
    a valid barcode.
    """
    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 47:
        return (
            digits[:4]
            + digits[32]
            + digits[33:]
            + digits[4:9]
            + digits[10:20]
            + digits[21:31]
        )
    if len(digits) == 48:
        return digits[:11] + digits[12:23] + digits[24:35] + digits[36:47]
    if len(digits) == 44:
        return digits
    return None


def decode_barcode(raw: str) -> Optional[Dict[str, object]]:
    """Decode value and due date from a Brazilian barcode.

    Supports the Febraban collection layout (first digit "8") and the bank
    layout. Returns a dict with "value" (Decimal in reais, or None) and
    "vencimento" (date, or None) or None when the barcode is not valid.
    """
    code = to_barcode(raw)
    if not code or not _check_dv_geral(code):
        return None

    if code[0] == "8":
        value = None
        if code[2] in ("6", "8"):
            value = Decimal(code[4:15]) / _VALUE_DIVISOR
        vencimento = _date_from_aaaammdd(code[19:27])
    else:
        value = Decimal(code[9:19]) / _VALUE_DIVISOR
        vencimento = _date_from_factor(code[5:9])

    return {"value": value, "vencimento": vencimento}


def _check_dv_geral(code: str) -> bool:
    """Check the barcode general check digit (modulo 11, weights 2-9).

    The check digit sits at position 4 for collection (arrecadacao) codes and
    at position 5 for bank codes, both in the 44-digit barcode.
    """
    if len(code) != 44:
        return False
    dv_pos = 3 if code[0] == "8" else 4
    soma = sum(
        int(ch) * (i % 8 + 2)
        for i, ch in enumerate(reversed(code[:dv_pos] + code[dv_pos + 1 :]))
    )
    resto = soma % 11
    dv = 0 if resto in (0, 1) else 11 - resto
    return dv == int(code[dv_pos])


def _date_from_aaaammdd(text: str) -> Optional[date]:
    try:
        return date(int(text[0:4]), int(text[4:6]), int(text[6:8]))
    except ValueError:
        return None


def _date_from_factor(text: str) -> Optional[date]:
    try:
        factor = int(text)
    except ValueError:
        return None
    if not (1000 <= factor <= 9999):
        return None
    return _FACTOR_BASE + timedelta(days=factor - 1000)


def is_vencimento_autofillable(
    vencimento: Optional[date], max_days_past: int = 7
) -> bool:
    """Whether a decoded due date is plausible enough to autofill.

    Real boletos are due today or in the future (occasionally a few days in
    the past). Dates further back than ``max_days_past`` usually mean the code
    is an example or has a stale factor, so we let the user fill it manually.
    """
    if vencimento is None:
        return False
    return date.today() - vencimento <= timedelta(days=max_days_past)
