"""Geração da planilha do catálogo para revisão fiscal (somente leitura).

O arquivo é montado em memória a partir dos produtos já carregados: nenhum
registro é alterado e nada é gravado no servidor.
"""

from datetime import date
from io import BytesIO
from typing import Dict, Iterable, List, Optional, Tuple

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

#: (título da coluna, largura). Só entram campos que existem no modelo.
COLUMNS: List[Tuple[str, int]] = [
    ("ID", 8),
    ("Nome", 42),
    ("Categoria", 22),
    ("Código de barras / EAN", 24),
    ("Unidade", 14),
    ("NCM", 12),
    ("CEST", 10),
    ("CFOP", 8),
    ("CSOSN", 8),
    ("CST", 8),
    ("Origem", 9),
    ("Unidade fiscal", 14),
    ("Status", 10),
    ("Preço de venda", 15),
]

HEADER_FILL = PatternFill("solid", fgColor="1F4E79")
HEADER_FONT = Font(bold=True, color="FFFFFF")


def catalog_filename(today: Optional[date] = None) -> str:
    """Nome do arquivo com a data da exportação (ex.: catalogo-fiscal-...xlsx)."""

    return f"catalogo-fiscal-{(today or date.today()).isoformat()}.xlsx"


def _text(value) -> str:
    return "" if value is None else str(value)


def _default_unit(units) -> str:
    """Nome da apresentação padrão do produto (ex.: Unidade, caixa com 12)."""

    for unit in units or []:
        if unit.is_default:
            return unit.name or ""
    return units[0].name if units else ""


def _write(sheet, row: int, column: int, value):
    cell = sheet.cell(row=row, column=column, value=value)
    # openpyxl converteria "=..." em fórmula. Força texto para que o conteúdo
    # do cadastro (nome, código etc.) nunca seja executado ao abrir a planilha.
    if isinstance(value, str) and value.startswith("="):
        cell.data_type = "s"
    return cell


def _row_values(product, units) -> list:
    return [
        product.id,
        _text(product.name),
        _text(product.category_name),
        _text(product.barcode),
        _text(_default_unit(units)),
        _text(product.ncm),
        _text(product.cest),
        _text(product.cfop),
        _text(product.csosn),
        _text(product.cst),
        int(product.origem or 0),
        _text(product.fiscal_unit),
        "Ativo" if product.active else "Inativo",
        float(product.price or 0),
    ]


def build_catalog_workbook(
    products: Iterable,
    units_by_product: Dict[int, list],
) -> bytes:
    """Monta o .xlsx em memória e devolve os bytes (sem tocar no banco)."""

    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Catálogo fiscal"

    for index, (title, width) in enumerate(COLUMNS, start=1):
        cell = sheet.cell(row=1, column=index, value=title)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")
        sheet.column_dimensions[get_column_letter(index)].width = width

    row = 1
    for product in products:
        row += 1
        values = _row_values(product, units_by_product.get(product.id, []))
        for column, value in enumerate(values, start=1):
            cell = _write(sheet, row, column, value)
            if column == len(COLUMNS):
                cell.number_format = "#,##0.00"

    last_column = get_column_letter(len(COLUMNS))
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:{last_column}{max(row, 1)}"

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
