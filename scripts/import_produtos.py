"""Importa produtos do XLS exportado do NX1 para o BillFlux."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import xlrd  # noqa: E402
from decimal import Decimal, InvalidOperation  # noqa: E402
from sqlmodel import select  # noqa: E402
from sqlalchemy.exc import IntegrityError  # noqa: E402
from billflux.infra.config.database import get_session  # noqa: E402
from billflux.infra.entities.category import Category  # noqa: E402
from billflux.infra.entities.product import Product  # noqa: E402
from billflux.infra.entities.product_movement import ProductMovement  # noqa: E402

XLS_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "produtos.xls"
)

CATEGORY_MAP = {
    "água": "Água",
    "biscoito": "Biscoito",
    "bomboniere": "Bomboniere",
    "cachaça": "Cachaça",
    "carvão": "Carvão",
    "chocolate": "Chocolate",
    "cigarro": "Cigarro",
    "conhaque": "Conhaque",
    "conveniência": "Conveniência",
    "dose": "Dose",
    "energetico": "Energético",
    "espumante": "Espumante",
    "essencia": "Essência",
    "gelo": "Gelo",
    "ice": "Ice",
    "licor": "Licor",
    "refrigerante": "Refrigerante",
    "rum": "Rum",
    "seda": "Seda",
    "suco": "Suco",
    "vinho": "Vinho",
}


def parse_decimal(value):
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value).strip().replace(",", "."))
    except (InvalidOperation, ValueError):
        return None


def parse_int(value):
    if value is None or value == "":
        return 0
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 0


def parse_barcode(value):
    if value is None or value == "":
        return None
    s = str(value).strip()
    if s.endswith(".0"):
        s = s[:-2]
    s = s.lstrip("0") or "0"
    if len(s) < 8:
        return None
    return s


def load_or_create_categories(session, xls_categories):
    existing = {c.name.lower(): c.id for c in session.exec(select(Category)).all()}
    created = 0
    cat_map = {}
    for raw_name in xls_categories:
        if not raw_name or not raw_name.strip():
            continue
        display_name = CATEGORY_MAP.get(raw_name.strip().lower(), raw_name.strip())
        key = display_name.lower()
        if key in existing:
            cat_map[raw_name.strip()] = existing[key]
        else:
            cat = Category(name=display_name, active=True)
            session.add(cat)
            session.flush()
            existing[key] = cat.id
            cat_map[raw_name.strip()] = cat.id
            created += 1
    session.commit()
    return cat_map, created


def main():
    print(f"Lendo {XLS_PATH}...")
    wb = xlrd.open_workbook(XLS_PATH)
    ws = wb.sheet_by_name("Sheet1")
    print(f"  {ws.nrows - 1} produtos encontrados")

    from billflux.infra.config.database import create_db
    create_db()

    xls_categories = set()
    for r in range(1, ws.nrows):
        cat = str(ws.cell_value(r, 10)).strip()
        if cat:
            xls_categories.add(cat)

    session = get_session()
    try:
        print(f"  {len(xls_categories)} categorias únicas no XLS")
        cat_map, created = load_or_create_categories(session, xls_categories)
        print(f"  {created} categorias criadas, {len(cat_map) - created} já existiam")
    finally:
        session.close()

    used_barcodes = set()
    imported = 0
    skipped = 0
    errors = 0

    for r in range(1, ws.nrows):
        session = get_session()
        try:
            name = str(ws.cell_value(r, 3)).strip()
            if not name:
                skipped += 1
                continue

            price_raw = parse_decimal(ws.cell_value(r, 5))
            price = price_raw if price_raw is not None else Decimal("0")
            stock = parse_int(ws.cell_value(r, 6))
            min_stock = parse_int(ws.cell_value(r, 16))
            barcode = parse_barcode(ws.cell_value(r, 38))
            active = str(ws.cell_value(r, 36)).strip() == "Ativo"
            cat_name_raw = str(ws.cell_value(r, 10)).strip()
            unidade = str(ws.cell_value(r, 12)).strip()

            if barcode and barcode in used_barcodes:
                barcode = None
            if barcode:
                used_barcodes.add(barcode)

            category_id = cat_map.get(cat_name_raw)

            obs_parts = []
            ncm = str(ws.cell_value(r, 23)).strip()
            if ncm and ncm != "0":
                obs_parts.append(f"NCM: {ncm}")
            estoque_raw = parse_decimal(ws.cell_value(r, 6))
            if stock < 0:
                obs_parts.append(f"Estoque NX1: {estoque_raw}")

            product = Product(
                name=name,
                price=price,
                cost=Decimal("0"),
                barcode=barcode,
                secondary_code=None,
                category_id=category_id,
                suppliers=unidade if unidade else None,
                supplier_id=None,
                stock_quantity=max(stock, 0),
                min_stock=min_stock,
                active=active,
                obs="; ".join(obs_parts) if obs_parts else None,
            )
            session.add(product)
            session.flush()

            if stock > 0:
                session.add(
                    ProductMovement(
                        product_id=product.id,
                        movement_type="entrada",
                        quantity=stock,
                        obs="Estoque inicial (importação NX1)",
                    )
                )

            session.commit()
            imported += 1
        except IntegrityError:
            session.rollback()
            errors += 1
        except Exception as e:
            session.rollback()
            errors += 1
            print(f"  ERRO linha {r + 1}: {e}")
        finally:
            session.close()

    print(f"\nResultado: {imported} importados, {skipped} pulados, {errors} erros")


if __name__ == "__main__":
    main()
