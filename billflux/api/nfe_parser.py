"""Parser for NF-e XML (nfe_procNFe). Extracts header and items."""

import re
import xml.etree.ElementTree as ET
from decimal import Decimal, InvalidOperation
from typing import Optional


def _text(el, path):
    """Extract text from first matching child, or None."""
    child = el.find(path)
    return (child.text or "").strip() if child is not None and child.text else None


def _ns(tag):
    """Wrap tag with NFe namespace."""
    return f".//{{http://www.portalfiscal.inf.br/nfe}}{tag}"


def _clean_xml(raw: str) -> str:
    """Strip BOM, Chrome/browser prefix text, and leading whitespace."""
    cleaned = raw.lstrip("\ufeff")
    match = re.search(r"<[?!]?nfeProc|<[?!]?NFe", cleaned)
    if match:
        cleaned = cleaned[match.start() :]
    return cleaned.strip()


def parse_nfe_xml(xml_content: str) -> Optional[dict]:
    """Parse NF-e XML and return structured dict or None on failure."""
    cleaned = _clean_xml(xml_content)

    try:
        root = ET.fromstring(cleaned)
    except ET.ParseError:
        return None

    inf = root.find(_ns("infNFe"))
    if inf is None:
        return None

    ide = inf.find(_ns("ide"))
    emit = inf.find(_ns("emit"))
    total_el = inf.find(_ns("total"))

    result = {
        "nf_number": _text(ide, _ns("nNF")) if ide is not None else None,
        "nf_serie": _text(ide, _ns("serie")) if ide is not None else None,
        "nf_modelo": _text(ide, _ns("mod")) if ide is not None else None,
        "nf_chave": inf.get("Id", "").replace("NFe", "") if inf.get("Id") else None,
        "supplier_cnpj": _text(emit, _ns("CNPJ")) if emit is not None else None,
        "supplier_name": None,
        "total": Decimal("0"),
        "freight": Decimal("0"),
        "items": [],
    }

    if emit is not None:
        xnome = _text(emit, _ns("xNome"))
        xfant = _text(emit, _ns("xFant"))
        result["supplier_name"] = xnome or xfant

    if total_el is not None:
        icms_tot = total_el.find(_ns("ICMSTot"))
        if icms_tot is not None:
            vnf = _text(icms_tot, _ns("vNF"))
            vf = _text(icms_tot, _ns("vFrete"))
            try:
                result["total"] = Decimal(vnf or "0")
            except InvalidOperation:
                result["total"] = Decimal("0")
            try:
                result["freight"] = Decimal(vf or "0")
            except InvalidOperation:
                result["freight"] = Decimal("0")

    det_list = inf.findall(_ns("det"))
    for det in det_list:
        prod = det.find(_ns("prod"))
        if prod is None:
            continue
        try:
            qty_raw = _text(prod, _ns("qCom")) or "0"
            qty = int(float(qty_raw))
            vprod_raw = _text(prod, _ns("vProd")) or "0"
            vfrete_raw = _text(prod, _ns("vFrete")) or "0"
            vseg_raw = _text(prod, _ns("vSeg")) or "0"
            vdesc_raw = _text(prod, _ns("vDesc")) or "0"
            voutro_raw = _text(prod, _ns("vOutro")) or "0"
            vprod = Decimal(vprod_raw)
            vfrete = Decimal(vfrete_raw)
            vseg = Decimal(vseg_raw)
            vdesc = Decimal(vdesc_raw)
            voutro = Decimal(voutro_raw)
            imposto = det.find(_ns("imposto"))
            vst = Decimal("0")
            vfcpst = Decimal("0")
            vipi = Decimal("0")
            if imposto is not None:
                icms = imposto.find(_ns("ICMS"))
                if icms is not None:
                    icms_child = list(icms)
                    if icms_child:
                        vst_raw = (
                            _text(icms_child[0], _ns("vICMSST"))
                            or _text(icms_child[0], _ns("vST"))
                            or "0"
                        )
                        vfcpst_raw = _text(icms_child[0], _ns("vFCPST")) or "0"
                        vst = Decimal(vst_raw)
                        vfcpst = Decimal(vfcpst_raw)
                ipi = imposto.find(_ns("IPI"))
                if ipi is not None:
                    ipi_trib = ipi.find(_ns("IPITrib"))
                    if ipi_trib is not None:
                        vipi_raw = _text(ipi_trib, _ns("vIPI")) or "0"
                        vipi = Decimal(vipi_raw)
            effective_total = (
                vprod + vfrete + vseg + vst + vfcpst + vipi + voutro - vdesc
            )
            effective_unit = effective_total / qty if qty > 0 else Decimal("0")
            item = {
                "product_name": _text(prod, _ns("xProd")),
                "quantity": qty,
                "unit_cost": effective_unit,
                "total": effective_total,
                "barcode": _text(prod, _ns("cEANTrib")) or _text(prod, _ns("cEAN")),
                "cfop": _text(prod, _ns("CFOP")),
                "ncm": _text(prod, _ns("NCM")),
                "unit_com": _text(prod, _ns("uCom")),
            }
        except (InvalidOperation, ValueError):
            continue
        result["items"].append(item)

    return result
