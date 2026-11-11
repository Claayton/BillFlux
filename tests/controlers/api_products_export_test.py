"""Tests for the fiscal catalog Excel export (GET /api/products/export)."""

from decimal import Decimal
from io import BytesIO

from openpyxl import load_workbook

from billflux.infra.repository.product_repository import ProductRepository
from billflux.infra.repository.product_unit_repository import ProductUnitRepository

XLSX_MIMETYPE = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

EXPECTED_HEADERS = [
    "ID",
    "Nome",
    "Categoria",
    "Código de barras / EAN",
    "Unidade",
    "NCM",
    "CEST",
    "CFOP",
    "CSOSN",
    "CST",
    "Origem",
    "Unidade fiscal",
    "Status",
    "Preço de venda",
]


def _make_product(name="Produto", **fields):
    return ProductRepository().insert_product(
        name=name,
        price=Decimal("12.50"),
        stock_quantity=1,
        **fields,
    )


def _load_sheet(response):
    return load_workbook(BytesIO(response.data)).active


def test_export_requires_login(client):
    """Sem sessão, a exportação deve devolver 401 (não gerar arquivo)."""

    response = client.get("/api/products/export")

    assert response.status_code == 401
    assert not response.data.startswith(b"PK")


def test_export_full_catalog(logged_client):
    """Exporta todos os produtos com os dados fiscais preenchidos."""

    _make_product(
        "Refrigerante 2L",
        barcode="7900000000001",
        ncm="22021000",
        cest="0300100",
        cfop="5405",
        csosn="500",
        cst="",
        origem=0,
        fiscal_unit="UN",
    )

    response = logged_client.get("/api/products/export")

    assert response.status_code == 200
    assert response.mimetype == XLSX_MIMETYPE
    disposition = response.headers["Content-Disposition"]
    assert "attachment" in disposition
    assert "catalogo-fiscal-" in disposition
    assert disposition.rstrip('"').endswith(".xlsx")

    sheet = _load_sheet(response)
    assert [cell.value for cell in sheet[1]] == EXPECTED_HEADERS
    assert sheet.max_row == 2

    row = {
        header: sheet.cell(row=2, column=i + 1).value
        for i, header in enumerate(EXPECTED_HEADERS)
    }
    assert row["Nome"] == "Refrigerante 2L"
    assert row["Código de barras / EAN"] == "7900000000001"
    assert row["NCM"] == "22021000"
    assert row["CEST"] == "0300100"
    assert row["CFOP"] == "5405"
    assert row["CSOSN"] == "500"
    assert row["Unidade fiscal"] == "UN"
    assert row["Status"] == "Ativo"
    assert row["Preço de venda"] == 12.5


def test_export_preserves_empty_fiscal_fields(logged_client):
    """Campos fiscais não preenchidos saem vazios (não inventa valores)."""

    _make_product("Sem fiscal")

    response = logged_client.get("/api/products/export")

    assert response.status_code == 200
    sheet = _load_sheet(response)
    row = {
        header: sheet.cell(row=2, column=i + 1).value
        for i, header in enumerate(EXPECTED_HEADERS)
    }
    for field in ("Categoria", "CEST", "CFOP", "CSOSN", "CST", "Unidade fiscal"):
        assert row[field] in (None, "")
    assert row["NCM"] in (None, "")
    assert row["Nome"] == "Sem fiscal"


def test_export_empty_catalog_has_only_header(logged_client):
    """Catálogo vazio gera planilha com o cabeçalho e nenhuma linha de dado."""

    response = logged_client.get("/api/products/export")

    assert response.status_code == 200
    sheet = _load_sheet(response)
    assert sheet.max_row == 1
    assert [cell.value for cell in sheet[1]] == EXPECTED_HEADERS


def test_export_includes_inactive_products(logged_client):
    """A exportação não filtra por status: ativos e inativos entram."""

    _make_product("Ativo", active=True)
    _make_product("Inativo", active=False)

    response = logged_client.get("/api/products/export")

    sheet = _load_sheet(response)
    names = {sheet.cell(row=r, column=2).value for r in range(2, sheet.max_row + 1)}
    statuses = {sheet.cell(row=r, column=13).value for r in range(2, sheet.max_row + 1)}
    assert names == {"Ativo", "Inativo"}
    assert statuses == {"Ativo", "Inativo"}


def test_export_uses_default_unit_name(logged_client):
    """A coluna Unidade traz a apresentação padrão do produto."""

    product = _make_product("Com apresentação")
    units = ProductUnitRepository()
    units.upsert(product.id, "Unidade", factor=1)
    units.upsert(product.id, "Caixa com 12", factor=12, is_default=True)

    response = logged_client.get("/api/products/export")

    sheet = _load_sheet(response)
    assert sheet.cell(row=2, column=5).value == "Caixa com 12"


def test_export_treats_leading_equals_as_text(logged_client):
    """Nome iniciado por '=' não pode virar fórmula na planilha."""

    _make_product("=1+1")

    response = logged_client.get("/api/products/export")

    sheet = _load_sheet(response)
    cell = sheet.cell(row=2, column=2)
    assert cell.value == "=1+1"
    assert cell.data_type == "s"


def test_export_does_not_modify_database(logged_client):
    """A exportação é somente leitura: nada muda no catálogo."""

    _make_product("Intocado", ncm="22021000", cfop="5405", csosn="500")
    before = logged_client.get("/api/products").get_json()

    assert logged_client.get("/api/products/export").status_code == 200

    after = logged_client.get("/api/products").get_json()
    assert after == before
