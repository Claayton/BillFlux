"""Tests for the barcode service"""

from datetime import date, timedelta
from decimal import Decimal

from billflux.services.barcode import (
    decode_barcode,
    is_vencimento_autofillable,
    to_barcode,
)

DAS_LINE = "85860000003 9 01290328262 7 43071726226 7 28154024101 5"
DAS_CODE = "85860000003012903282624307172622628154024101"

BANK_LINE = "23790448095616862379336011058009740430000124020"
BANK_CODE = "23797404300001240200448056168623793601105800"


def test_to_barcode_from_48_digit_das():
    assert to_barcode(DAS_LINE) == DAS_CODE


def test_to_barcode_from_47_digit_bank_line():
    assert to_barcode(BANK_LINE) == BANK_CODE


def test_to_barcode_keeps_44_digits():
    assert to_barcode(DAS_CODE) == DAS_CODE


def test_to_barcode_ignores_spaces():
    spaced = " ".join(DAS_CODE[i : i + 11] for i in range(0, 44, 11))
    assert to_barcode(spaced) == DAS_CODE


def test_to_barcode_invalid():
    assert to_barcode("123") is None
    assert to_barcode("") is None
    assert to_barcode("abc") is None


def test_decode_das_value():
    assert decode_barcode(DAS_LINE)["value"] == Decimal("301.29")


def test_decode_das_has_no_due_date():
    assert decode_barcode(DAS_LINE)["vencimento"] is None


def test_decode_das_value_with_six_identifier():
    code = "8" + "1" + "6" + "1" + "00000030129" + "0328" + "2026072000000000000000000"
    assert decode_barcode(code)["value"] == Decimal("301.29")
    assert decode_barcode(code)["vencimento"] == date(2026, 7, 20)


def test_decode_bank_value_and_factor():
    assert decode_barcode(BANK_LINE)["value"] == Decimal("1240.20")
    assert decode_barcode(BANK_LINE)["vencimento"] == date(2006, 2, 5)


def test_decode_bank_value_without_factor():
    code = "0019" + "7" + "0000" + "0000001500" + "0000000000000000000000000"
    assert decode_barcode(code)["value"] == Decimal("15.00")
    assert decode_barcode(code)["vencimento"] is None


def test_decode_invalid():
    assert decode_barcode("123") is None
    assert decode_barcode("") is None


def test_decode_rejects_invalid_check_digit():
    line = "34195.17515 23456.787128 34123.456005 1 10541000002603"
    assert to_barcode(line) is not None
    assert decode_barcode(line) is None


def test_is_vencimento_autofillable():
    today = date.today()
    assert is_vencimento_autofillable(today) is True
    assert is_vencimento_autofillable(today + timedelta(days=30)) is True
    assert is_vencimento_autofillable(today - timedelta(days=7)) is True
    assert is_vencimento_autofillable(today - timedelta(days=8)) is False
    assert is_vencimento_autofillable(date(1999, 3, 4)) is False
    assert is_vencimento_autofillable(None) is False
