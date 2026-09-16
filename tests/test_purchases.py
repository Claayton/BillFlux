"""Tests for PurchaseRepository and Purchase API endpoints."""

import pytest
from decimal import Decimal


def _csrf(client):
    return client.get("/api/auth/csrf").get_json()["csrf_token"]


def _open_register():
    from billflux.infra.config.database import get_session
    from billflux.infra.entities.cash_register import CashRegister

    session = get_session()
    reg = CashRegister(
        opened_by="test",
        opened_at="2026-08-26 00:00:00",
        opening_amount=0,
        status="open",
    )
    session.add(reg)
    session.commit()
    session.close()


def _make_supplier():
    from billflux.infra.config.database import get_session
    from billflux.infra.entities.supplier import Supplier

    session = get_session()
    s = Supplier(name="Fornecedor Teste", cnpj="12345678000190", active=True)
    session.add(s)
    session.commit()
    sid = s.id
    session.close()
    return sid


def _make_product():
    from billflux.infra.config.database import get_session
    from billflux.infra.entities.product import Product

    session = get_session()
    p = Product(
        name="Produto X",
        price=Decimal("10"),
        cost=Decimal("5"),
        stock_quantity=0,
        active=True,
    )
    session.add(p)
    session.commit()
    pid = p.id
    session.close()
    return pid


SAMPLE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">'
    '<infNFe Id="NFe35260812345678000199550010000100011234567001">'
    "<ide><nNF>100</nNF><serie>1</serie><mod>55</mod></ide>"
    "<emit><CNPJ>12345678000190</CNPJ><xNome>Fornecedor X</xNome></emit>"
    "<total><ICMSTot><vNF>100.00</vNF><vFrete>10.00</vFrete></ICMSTot></total>"
    '<det nItem="1"><prod><xProd>Produto A</xProd><qCom>2</qCom>'
    "<vUnCom>50.00</vUnCom><vProd>100.00</vProd>"
    "<cEANTrib></cEANTrib><CFOP>5102</CFOP><NCM>1234</NCM></prod></det>"
    "</infNFe></nfeProc>"
)


class TestPurchaseRepository:
    def test_insert_and_get(self):
        _open_register()
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        repo = PurchaseRepository()

        po = repo.insert_purchase(
            nf_number="100",
            nf_serie="1",
            total=Decimal("100"),
            freight=Decimal("10"),
            discount=Decimal("5"),
            net_total=Decimal("105"),
            status="rascunho",
            items=[
                {
                    "product_id": None,
                    "quantity": 2,
                    "unit_cost": Decimal("50"),
                    "total": Decimal("100"),
                    "barcode": None,
                    "product_name": "Item A",
                }
            ],
        )
        assert po.id is not None
        assert po.nf_number == "100"
        assert po.status == "rascunho"
        assert po.total == Decimal("100")
        assert po.net_total == Decimal("105")

        fetched = repo.get_purchase(po.id)
        assert fetched is not None
        assert fetched.nf_number == "100"

    def test_get_items(self):
        _open_register()
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        repo = PurchaseRepository()

        po = repo.insert_purchase(
            items=[
                {
                    "product_id": None,
                    "quantity": 1,
                    "unit_cost": Decimal("10"),
                    "total": Decimal("10"),
                    "barcode": None,
                    "product_name": "A",
                },
                {
                    "product_id": None,
                    "quantity": 3,
                    "unit_cost": Decimal("5"),
                    "total": Decimal("15"),
                    "barcode": None,
                    "product_name": "B",
                },
            ],
        )
        items = repo.get_purchase_items(po.id)
        assert len(items) == 2
        assert items[0].product_name == "A"
        assert items[1].quantity == 3

    def test_confirm_updates_stock(self):
        _open_register()
        supplier_id = _make_supplier()
        product_id = _make_product()
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        repo = PurchaseRepository()

        po = repo.insert_purchase(
            supplier_id=supplier_id,
            items=[
                {
                    "product_id": product_id,
                    "quantity": 5,
                    "unit_cost": Decimal("8"),
                    "total": Decimal("40"),
                    "barcode": None,
                    "product_name": "Produto X",
                }
            ],
            total=Decimal("40"),
            net_total=Decimal("40"),
        )
        result = repo.confirm_purchase(po.id)
        assert result.status == "confirmada"
        assert result.bill_id is not None

        from billflux.infra.config.database import get_session
        from billflux.infra.entities.product import Product

        session = get_session()
        updated = session.get(Product, product_id)
        assert updated.stock_quantity == 5
        assert updated.cost == Decimal("8")
        session.close()

    def test_cancel_reverts_stock(self):
        _open_register()
        supplier_id = _make_supplier()
        product_id = _make_product()
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        repo = PurchaseRepository()

        po = repo.insert_purchase(
            supplier_id=supplier_id,
            items=[
                {
                    "product_id": product_id,
                    "quantity": 3,
                    "unit_cost": Decimal("10"),
                    "total": Decimal("30"),
                    "barcode": None,
                    "product_name": "Produto X",
                }
            ],
            total=Decimal("30"),
            net_total=Decimal("30"),
        )
        repo.confirm_purchase(po.id)
        from billflux.infra.config.database import get_session
        from billflux.infra.entities.product import Product

        session = get_session()
        p1 = session.get(Product, product_id)
        assert p1.stock_quantity == 3
        session.close()

        repo.cancel_purchase(po.id)
        session = get_session()
        p2 = session.get(Product, product_id)
        assert p2.stock_quantity == 0
        session.close()

    def test_delete_rascunho_only(self):
        _open_register()
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        repo = PurchaseRepository()

        po = repo.insert_purchase(
            items=[
                {
                    "product_id": None,
                    "quantity": 1,
                    "unit_cost": Decimal("10"),
                    "total": Decimal("10"),
                    "barcode": None,
                    "product_name": "X",
                }
            ],
        )
        assert repo.delete_purchase(po.id) is True
        assert repo.get_purchase(po.id) is None

        po2 = repo.insert_purchase(
            items=[
                {
                    "product_id": None,
                    "quantity": 1,
                    "unit_cost": Decimal("10"),
                    "total": Decimal("10"),
                    "barcode": None,
                    "product_name": "Y",
                }
            ],
        )
        repo.confirm_purchase(po2.id)
        assert repo.delete_purchase(po2.id) is False

    def test_get_by_nf_chave(self):
        _open_register()
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        repo = PurchaseRepository()

        po = repo.insert_purchase(
            nf_chave="35260812345678000199550010000100011234567890"
        )
        found = repo.get_purchase_by_nf_chave(
            "35260812345678000199550010000100011234567890"
        )
        assert found is not None
        assert found.id == po.id

        not_found = repo.get_purchase_by_nf_chave(
            "99999999999999999999999999999999999999999999"
        )
        assert not_found is None

    def test_upsert_and_delete_item(self):
        _open_register()
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        repo = PurchaseRepository()

        po = repo.insert_purchase(
            items=[
                {
                    "product_id": None,
                    "quantity": 1,
                    "unit_cost": Decimal("10"),
                    "total": Decimal("10"),
                    "barcode": None,
                    "product_name": "X",
                }
            ],
        )
        items = repo.get_purchase_items(po.id)
        assert len(items) == 1

        updated = repo.upsert_item(
            po.id,
            item_id=items[0].id,
            quantity=5,
            unit_cost=Decimal("20"),
            product_name="Y",
        )
        assert updated.quantity == 5
        assert updated.total == Decimal("100")

        assert repo.delete_item(items[0].id) is True
        assert len(repo.get_purchase_items(po.id)) == 0


class TestPurchaseAPI:
    def test_list_purchases(self, logged_client):
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        repo = PurchaseRepository()
        repo.insert_purchase(
            nf_number="100", total=Decimal("50"), net_total=Decimal("50")
        )

        resp = logged_client.get("/api/purchases")
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["purchases"]) >= 1
        assert any(p["nf_number"] == "100" for p in data["purchases"])

    def test_create_purchase(self, logged_client):
        token = _csrf(logged_client)
        resp = logged_client.post(
            "/api/purchases",
            json={
                "nf_number": "200",
                "freight": "15",
                "discount": "5",
                "items": [
                    {
                        "product_id": None,
                        "quantity": 2,
                        "unit_cost": "25",
                        "total": "50",
                        "product_name": "Item Teste",
                    },
                ],
            },
            headers={"X-CSRFToken": token},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["purchase"]["nf_number"] == "200"
        assert data["purchase"]["status"] == "rascunho"

    def test_confirm_purchase(self, logged_client):
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        repo = PurchaseRepository()
        po = repo.insert_purchase(total=Decimal("100"), net_total=Decimal("100"))

        token = _csrf(logged_client)
        resp = logged_client.post(
            f"/api/purchases/{po.id}/confirm",
            json={
                "due_date": "2026-09-01",
                "create_bill": True,
            },
            headers={"X-CSRFToken": token},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["purchase"]["status"] == "confirmada"
        assert data["purchase"]["bill_id"] is not None

    def test_nfe_import(self, logged_client):
        token = _csrf(logged_client)
        resp = logged_client.post(
            "/api/purchases/nfe-import",
            json={"xml": SAMPLE_XML},
            headers={"X-CSRFToken": token},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["duplicate"] is False
        assert data["purchase"]["nf_number"] == "100"

    def test_nfe_import_duplicate(self, logged_client):
        token = _csrf(logged_client)
        DUPLICATE_XML = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">'
            '<infNFe Id="NFe35260812345678000199550010000100011234567002">'
            "<ide><nNF>999</nNF><serie>1</serie><mod>55</mod></ide>"
            "<emit><CNPJ>12345678000190</CNPJ><xNome>Fornecedor X</xNome></emit>"
            "<total><ICMSTot><vNF>50.00</vNF><vFrete>0</vFrete></ICMSTot></total>"
            '<det nItem="1"><prod><xProd>Produto B</xProd><qCom>1</qCom>'
            "<vUnCom>50.00</vUnCom><vProd>50.00</vProd>"
            "<cEANTrib></cEANTrib><CFOP>5102</CFOP><NCM>1234</NCM></prod></det>"
            "</infNFe></nfeProc>"
        )
        resp1 = logged_client.post(
            "/api/purchases/nfe-import",
            json={"xml": DUPLICATE_XML},
            headers={"X-CSRFToken": token},
        )
        assert resp1.status_code == 201
        resp2 = logged_client.post(
            "/api/purchases/nfe-import",
            json={"xml": DUPLICATE_XML},
            headers={"X-CSRFToken": token},
        )
        assert resp2.status_code == 200
        data = resp2.get_json()
        assert data["duplicate"] is True

    def test_nfe_import_with_chrome_prefix(self, logged_client):
        token = _csrf(logged_client)
        chrome_msg = (
            "This XML file does not appear to have any style "
            "information associated with it. The document tree is shown below."
        )
        chrome_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">'
            '<infNFe Id="NFe35260812345678000199550010000100011234567010">'
            "<ide><nNF>888</nNF><serie>1</serie><mod>55</mod></ide>"
            "<emit><CNPJ>12345678000190</CNPJ><xNome>Fornecedor Chrome</xNome></emit>"
            "<total><ICMSTot><vNF>75.00</vNF><vFrete>0</vFrete></ICMSTot></total>"
            '<det nItem="1"><prod><xProd>Produto Chrome</xProd><qCom>3</qCom>'
            "<vUnCom>25.00</vUnCom><vProd>75.00</vProd>"
            "<cEANTrib></cEANTrib><CFOP>5102</CFOP><NCM>1234</NCM></prod></det>"
            "</infNFe></nfeProc>"
        )
        resp = logged_client.post(
            "/api/purchases/nfe-import",
            json={"xml": chrome_msg + "\n" + chrome_xml},
            headers={"X-CSRFToken": token},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["purchase"]["nf_number"] == "888"

    def test_nfe_import_with_bom(self, logged_client):
        token = _csrf(logged_client)
        bom_xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe">'
            '<infNFe Id="NFe35260812345678000199550010000100011234567011">'
            "<ide><nNF>777</nNF><serie>1</serie><mod>55</mod></ide>"
            "<emit><CNPJ>12345678000190</CNPJ><xNome>Fornecedor BOM</xNome></emit>"
            "<total><ICMSTot><vNF>40.00</vNF><vFrete>0</vFrete></ICMSTot></total>"
            '<det nItem="1"><prod><xProd>Produto BOM</xProd><qCom>2</qCom>'
            "<vUnCom>20.00</vUnCom><vProd>40.00</vProd>"
            "<cEANTrib></cEANTrib><CFOP>5102</CFOP><NCM>1234</NCM></prod></det>"
            "</infNFe></nfeProc>"
        )
        resp = logged_client.post(
            "/api/purchases/nfe-import",
            json={"xml": "\ufeff" + bom_xml},
            headers={"X-CSRFToken": token},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["purchase"]["nf_number"] == "777"

    def test_nfe_import_nested_nfe_tag(self, logged_client):
        """XML com <NFe> intermediário (formato padrao SEFAZ)."""
        token = _csrf(logged_client)
        xml = (
            '<nfeProc xmlns="http://www.portalfiscal.inf.br/nfe" versao="4.00">'
            '<NFe xmlns="http://www.portalfiscal.inf.br/nfe">'
            '<infNFe Id="NFe41260861186888014496550050059860271046298992" versao="4.00">'
            "<ide><nNF>5986027</nNF><serie>5</serie><mod>55</mod></ide>"
            "<emit><CNPJ>61186888014496</CNPJ>"
            "<xNome>SPAL INDUSTRIA BRASILEIRA DE BEBIDAS S/A</xNome></emit>"
            "<total><ICMSTot><vNF>300.30</vNF><vFrete>0.00</vFrete></ICMSTot></total>"
            '<det nItem="1"><prod><xProd>D.V Mais Uva 1Litro 6</xProd>'
            "<qCom>1.0000</qCom><vUnCom>39.1100000000</vUnCom><vProd>39.11</vProd>"
            "<cEANTrib>7898341430098</cEANTrib><CFOP>5403</CFOP><NCM>22029900</NCM>"
            "</prod></det>"
            '<det nItem="2"><prod><xProd>FANTA LAR LATA 350ML CX C/06</xProd>'
            "<qCom>1.0000</qCom><vUnCom>15.3200000000</vUnCom><vProd>15.32</vProd>"
            "<cEANTrib>7894900030013</cEANTrib><CFOP>5401</CFOP><NCM>22021000</NCM>"
            "</prod></det>"
            "</infNFe></NFe></nfeProc>"
        )
        resp = logged_client.post(
            "/api/purchases/nfe-import",
            json={"xml": xml},
            headers={"X-CSRFToken": token},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["purchase"]["nf_number"] == "5986027"
        assert data["purchase"]["nf_serie"] == "5"
        assert (
            data["purchase"]["nf_chave"]
            == "41260861186888014496550050059860271046298992"
        )
        assert float(data["purchase"]["total"]) == 300.30

    def test_nfe_import_invalid_xml(self, logged_client):
        token = _csrf(logged_client)
        resp = logged_client.post(
            "/api/purchases/nfe-import",
            json={"xml": "this is not xml at all"},
            headers={"X-CSRFToken": token},
        )
        assert resp.status_code == 400
        assert "processar" in resp.get_json()["error"].lower()


class TestWeightedAverageCost:
    def test_first_purchase_sets_cost(self):
        _open_register()
        product_id = _make_product()
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        repo = PurchaseRepository()
        po = repo.insert_purchase(
            items=[
                {
                    "product_id": product_id,
                    "quantity": 20,
                    "unit_cost": Decimal("4.50"),
                    "total": Decimal("90"),
                    "barcode": None,
                    "product_name": "Produto X",
                }
            ],
            total=Decimal("90"),
            net_total=Decimal("90"),
        )
        repo.confirm_purchase(po.id)

        from billflux.infra.config.database import get_session
        from billflux.infra.entities.product import Product

        session = get_session()
        p = session.get(Product, product_id)
        assert p.stock_quantity == 20
        assert p.cost == Decimal("4.50")
        session.close()

    def test_weighted_average_calculation(self):
        _open_register()
        product_id = _make_product()
        from billflux.infra.config.database import get_session
        from billflux.infra.entities.product import Product
        from billflux.infra.repository.purchase_repository import PurchaseRepository

        session = get_session()
        p = session.get(Product, product_id)
        p.stock_quantity = 10
        p.cost = Decimal("5.00")
        session.add(p)
        session.commit()
        session.close()

        repo = PurchaseRepository()
        po = repo.insert_purchase(
            items=[
                {
                    "product_id": product_id,
                    "quantity": 20,
                    "unit_cost": Decimal("4.50"),
                    "total": Decimal("90"),
                    "barcode": None,
                    "product_name": "Produto X",
                }
            ],
            total=Decimal("90"),
            net_total=Decimal("90"),
        )
        repo.confirm_purchase(po.id)

        session = get_session()
        p = session.get(Product, product_id)
        assert p.stock_quantity == 30
        expected_cost = (
            Decimal("10") * Decimal("5.00") + Decimal("20") * Decimal("4.50")
        ) / Decimal("30")
        assert p.cost == expected_cost.quantize(Decimal("0.01"))
        session.close()


class TestProductBarcodeSearchAPI:
    def test_search_by_barcode(self, logged_client):
        from billflux.infra.repository.product_repository import ProductRepository

        repo = ProductRepository()
        repo.insert_product(
            name="Produto Barcode",
            price=Decimal("10"),
            barcode="7891234567890",
        )
        resp = logged_client.get("/api/products/barcode/7891234567890")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["product"]["name"] == "Produto Barcode"
        assert data["product"]["barcode"] == "7891234567890"

    def test_search_by_barcode_not_found(self, logged_client):
        resp = logged_client.get("/api/products/barcode/0000000000000")
        assert resp.status_code == 404

    def test_search_products_by_name(self, logged_client):
        from billflux.infra.repository.product_repository import ProductRepository

        repo = ProductRepository()
        repo.insert_product(name="Coca Cola 2L XYZSEARCH", price=Decimal("12"))
        repo.insert_product(name="Fanta Laranja 2L XYZSEARCH", price=Decimal("10"))
        resp = logged_client.get("/api/products/search?q=XYZSEARCH")
        assert resp.status_code == 200
        data = resp.get_json()
        names = [p["name"] for p in data["products"]]
        assert "Coca Cola 2L XYZSEARCH" in names
        assert "Fanta Laranja 2L XYZSEARCH" in names
        assert len(data["products"]) == 2
