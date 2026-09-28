"""Module for repository to Tab (comandas do PDV).

Toda a regra de estoque da comanda é centralizada aqui: baixa na abertura e
em cada adição de item, devolução na remoção/cancelamento, e NENHUMA baixa
ao fechar (o pedido final usa `decrement_stock=False`, evitando duplicidade).
"""

from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import List, Optional, Tuple

from sqlalchemy.exc import IntegrityError
from sqlmodel import func, select

from billflux.domain.enums import TabStatus
from billflux.domain.models.tab import Tab, TabItem
from billflux.infra.config.database import get_session
from billflux.infra.entities.product import Product as ProductModel
from billflux.infra.entities.product_movement import (
    ProductMovement as ProductMovementModel,
)
from billflux.infra.entities.product_unit import ProductUnit as ProductUnitModel
from billflux.infra.entities.tab import Tab as TabModel
from billflux.infra.entities.tab_item import TabItem as TabItemModel
from billflux.domain.models.orders import Order
from billflux.infra.repository.order_repository import OrderRepository


def tab_label(number: int) -> str:
    """Rótulo impresso/auditado da comanda (#0047)."""
    return f"#{number:04d}"


class TabRepository:
    """Tab table data manipulation"""

    # ---------- itens / estoque (internos, sempre na sessão do chamador) ----------

    @staticmethod
    def _resolve_items(session, items) -> List[dict]:
        """Valida o payload de itens e monta os snapshots (nome/preço/fator).

        Levanta ValueError para payload inválido; itens repetidos do mesmo
        produto+unidade são somados (o carrinho do PDV já agrupa)."""
        if not isinstance(items, list):
            raise ValueError("Itens da comanda inválidos.")
        resolved = {}
        for item in items:
            if not isinstance(item, dict):
                raise ValueError("Item da comanda inválido.")
            try:
                product_id = int(item.get("product_id"))
                quantity = int(item.get("quantity"))
            except (TypeError, ValueError):
                raise ValueError("Item da comanda inválido.") from None
            if quantity <= 0:
                raise ValueError("Quantidade inválida.")
            product = session.get(ProductModel, product_id)
            if not product or not product.active:
                raise ValueError("Produto não encontrado.")

            factor = 1
            unit_price = product.price
            unit_id = None
            raw_unit_id = item.get("unit_id")
            if raw_unit_id:
                try:
                    unit = session.get(ProductUnitModel, int(raw_unit_id))
                except (TypeError, ValueError):
                    unit = None
                if unit and unit.product_id == product.id:
                    factor = unit.factor or 1
                    unit_price = unit.price or product.price
                    unit_id = unit.id

            key = (product_id, unit_id or 0)
            if key in resolved:
                resolved[key]["quantity"] += quantity
                resolved[key]["total"] = (
                    resolved[key]["unit_price"] * resolved[key]["quantity"]
                )
                continue
            resolved[key] = {
                "product": product,
                "product_id": product_id,
                "unit_id": unit_id,
                "factor": factor,
                "quantity": quantity,
                "unit_price": unit_price,
                "total": unit_price * quantity,
                "name": product.name,
            }
        return list(resolved.values())

    @staticmethod
    def _move_stock(session, product, base_delta: int, obs: str):
        """Aplica delta de estoque em unidades base (não-decimal).

        base_delta > 0 baixa do estoque (saída); < 0 devolve (entrada);
        0 não faz nada. Estoque pode ficar negativo (mesma regra da venda)."""
        if not base_delta:
            return
        if base_delta > 0:
            product.stock_quantity -= base_delta
            movement_type = "saida"
            quantity = base_delta
        else:
            product.stock_quantity += -base_delta
            movement_type = "entrada"
            quantity = -base_delta
        session.add(product)
        session.add(
            ProductMovementModel(
                product_id=product.id,
                movement_type=movement_type,
                quantity=quantity,
                obs=obs,
            )
        )

    # ---------- consultas ----------

    def get_tab(self, tab_id: int) -> Optional[Tab]:
        session = get_session()
        try:
            tab = session.get(TabModel, tab_id)
            return Tab(**dict(tab)) if tab else None
        finally:
            session.close()

    def get_tab_items(self, tab_id: int) -> List[TabItem]:
        session = get_session()
        try:
            sql = (
                select(TabItemModel)
                .where(TabItemModel.tab_id == tab_id)
                .order_by(TabItemModel.id)
            )
            return [TabItem(**dict(item)) for item in session.exec(sql).all()]
        finally:
            session.close()

    def list_tabs(
        self, status: Optional[str] = "open", search: Optional[str] = None
    ) -> List[Tab]:
        """Lista comandas; `status` em open/closed/canceled ou None (todas).
        `search` casa número da comanda ou identificação."""
        session = get_session()
        try:
            sql = select(TabModel)
            if status in (TabStatus.OPEN, TabStatus.CLOSED, TabStatus.CANCELED):
                sql = sql.where(TabModel.status == status)
            if search:
                term = search.strip()
                try:
                    number = int(term.lstrip("#"))
                    sql = sql.where(
                        (TabModel.number == number)
                        | TabModel.identification.ilike(f"%{term}%")
                    )
                except ValueError:
                    sql = sql.where(TabModel.identification.ilike(f"%{term}%"))
            sql = sql.order_by(TabModel.opened_at.desc(), TabModel.id.desc())
            return [Tab(**dict(tab)) for tab in session.exec(sql).all()]
        finally:
            session.close()

    def items_counts(self, tab_ids: List[int]) -> dict:
        """{tab_id: (linhas, unidades)} para as comandas informadas."""
        if not tab_ids:
            return {}
        session = get_session()
        try:
            sql = (
                select(
                    TabItemModel.tab_id,
                    func.count(TabItemModel.id),
                    func.coalesce(func.sum(TabItemModel.quantity), 0),
                )
                .where(TabItemModel.tab_id.in_(tab_ids))
                .group_by(TabItemModel.tab_id)
            )
            return {row[0]: (row[1], int(row[2])) for row in session.exec(sql).all()}
        finally:
            session.close()

    # ---------- operações ----------

    def create_tab(
        self,
        identification: str,
        items: List[dict],
        opened_by: Optional[str] = None,
    ) -> Tab:
        """Cria a comanda com número sequencial, snapshots dos itens e baixa
        de estoque (unidades base), tudo numa única transação.

        Repete a transação se o número sequencial colidir (dois operadores
        abrindo comandas ao mesmo tempo)."""
        for _attempt in range(3):
            try:
                return self._create_tab_once(identification, items, opened_by)
            except IntegrityError:
                continue  # número do concurso acabou de ser usado: refaz
        raise ValueError("Não foi possível abrir a comanda. Tente novamente.")

    def _create_tab_once(
        self,
        identification: str,
        items: List[dict],
        opened_by: Optional[str] = None,
    ) -> Tab:
        identification = (identification or "").strip()
        if not identification:
            raise ValueError("Informe a identificação da comanda.")

        session = get_session()
        try:
            with session:
                resolved = self._resolve_items(session, items)
                if not resolved:
                    raise ValueError("Adicione ao menos um item à comanda.")

                last_number = session.exec(
                    select(TabModel.number).order_by(TabModel.number.desc())
                ).first()
                number = (last_number or 0) + 1
                label = tab_label(number)

                subtotal = Decimal("0")
                for entry in resolved:
                    subtotal += entry["total"]

                tab = TabModel(
                    number=number,
                    identification=identification,
                    status=TabStatus.OPEN,
                    subtotal=subtotal,
                    total=subtotal,
                    opened_by=opened_by,
                )
                session.add(tab)
                session.flush()

                for entry in resolved:
                    session.add(
                        TabItemModel(
                            tab_id=tab.id,
                            product_id=entry["product_id"],
                            unit_id=entry["unit_id"],
                            name=entry["name"],
                            quantity=entry["quantity"],
                            unit_price=entry["unit_price"],
                            total=entry["total"],
                            factor=entry["factor"],
                        )
                    )
                    self._move_stock(
                        session,
                        entry["product"],
                        entry["quantity"] * entry["factor"],
                        f"Comanda {label}",
                    )

                session.commit()
                session.refresh(tab)
                return Tab(**dict(tab))
        finally:
            session.close()

    def set_tab_items(self, tab_id: int, items: List[dict]) -> Optional[Tab]:
        """Substitui os itens da comanda aplicando o delta de estoque por
        produto (adicionado → baixa; removido/reduzido → devolução).
        Retorna None se a comanda não existe; ValueError se não está aberta."""
        session = get_session()
        try:
            with session:
                tab = session.get(TabModel, tab_id)
                if not tab:
                    return None
                if tab.status != TabStatus.OPEN:
                    raise ValueError("Apenas comandas abertas podem ser alteradas.")

                resolved = self._resolve_items(session, items)
                label = tab_label(tab.number)

                old_base = {}
                old_rows = session.exec(
                    select(TabItemModel).where(TabItemModel.tab_id == tab.id)
                ).all()
                for row in old_rows:
                    key = (row.product_id, row.unit_id or 0)
                    old_base[key] = old_base.get(key, 0) + row.quantity * (
                        row.factor or 1
                    )
                    session.delete(row)

                subtotal = Decimal("0")
                for entry in resolved:
                    key = (entry["product_id"], entry["unit_id"] or 0)
                    new_base = entry["quantity"] * entry["factor"]
                    delta = new_base - old_base.get(key, 0)
                    if delta:
                        self._move_stock(
                            session, entry["product"], delta, f"Comanda {label}"
                        )
                    old_base.pop(key, None)
                    subtotal += entry["total"]
                    session.add(
                        TabItemModel(
                            tab_id=tab.id,
                            product_id=entry["product_id"],
                            unit_id=entry["unit_id"],
                            name=entry["name"],
                            quantity=entry["quantity"],
                            unit_price=entry["unit_price"],
                            total=entry["total"],
                            factor=entry["factor"],
                        )
                    )

                # Itens que sumiram da comanda voltam pro estoque.
                for key, base in old_base.items():
                    product = session.get(ProductModel, key[0])
                    if product:
                        self._move_stock(
                            session, product, -base, f"Comanda {label} (item removido)"
                        )

                tab.subtotal = subtotal
                tab.total = subtotal
                tab.updated_at = datetime.now()
                session.add(tab)
                session.commit()
                session.refresh(tab)
                return Tab(**dict(tab))
        finally:
            session.close()

    def close_tab(
        self,
        tab_id: int,
        payment_method_id: Optional[int] = None,
        payments: Optional[List[tuple]] = None,
        discount: Optional[Decimal] = None,
        obs: Optional[str] = None,
        customer_id: Optional[int] = None,
        closed_by: Optional[str] = None,
    ) -> Optional[Tuple[Tab, Order]]:
        """Fecha a comanda criando o pedido definitivo SEM baixa de estoque
        (já baixado na abertura/adicação), preservando o preço dos snapshots
        e vinculando tab.order_id. Transação única: ou fecha tudo, ou nada
        (fechamento repetido recebe ValueError)."""
        session = get_session()
        try:
            with session:
                tab = session.get(TabModel, tab_id)
                if not tab:
                    return None
                if tab.status != TabStatus.OPEN:
                    raise ValueError("Comanda já finalizada.")

                rows = session.exec(
                    select(TabItemModel)
                    .where(TabItemModel.tab_id == tab.id)
                    .order_by(TabItemModel.id)
                ).all()
                if not rows:
                    raise ValueError("A comanda não possui itens.")

                cart = []
                for row in rows:
                    factor = row.factor or 1
                    # preço base do snapshot (por unidade), p/ o pedido gravar
                    # o mesmo valor da comanda mesmo se o produto mudar de preço
                    base_price = (row.unit_price / factor).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    cart.append((row.product_id, row.quantity * factor, base_price))

                order = OrderRepository._create_order_in_session(
                    session,
                    cart,
                    payment_method_id,
                    obs=obs,
                    discount=discount,
                    payments=payments,
                    customer_id=customer_id,
                    decrement_stock=False,
                    allow_inactive=True,
                )

                tab.status = TabStatus.CLOSED
                tab.order_id = order.id
                tab.closed_at = datetime.now()
                tab.closed_by = closed_by
                if discount is not None:
                    tab.discount = discount
                tab.total = order.total
                tab.updated_at = datetime.now()
                session.add(tab)
                session.commit()
                session.refresh(tab)
                session.refresh(order)
                return Tab(**dict(tab)), Order(**dict(order))
        finally:
            session.close()

    def cancel_tab(
        self, tab_id: int, canceled_by: Optional[str] = None
    ) -> Optional[Tab]:
        """Cancela a comanda devolvendo os itens ao estoque (registro
        mantido para histórico; nada é apagado)."""
        session = get_session()
        try:
            with session:
                tab = session.get(TabModel, tab_id)
                if not tab:
                    return None
                if tab.status != TabStatus.OPEN:
                    raise ValueError("Apenas comandas abertas podem ser canceladas.")

                label = tab_label(tab.number)
                rows = session.exec(
                    select(TabItemModel).where(TabItemModel.tab_id == tab.id)
                ).all()
                for row in rows:
                    product = session.get(ProductModel, row.product_id)
                    if product:
                        self._move_stock(
                            session,
                            product,
                            -(row.quantity * (row.factor or 1)),
                            f"Comanda {label} cancelada",
                        )

                tab.status = TabStatus.CANCELED
                tab.canceled_at = datetime.now()
                tab.canceled_by = canceled_by
                tab.updated_at = datetime.now()
                session.add(tab)
                session.commit()
                session.refresh(tab)
                return Tab(**dict(tab))
        finally:
            session.close()

    def register_print(self, tab_id: int) -> Optional[Tab]:
        """Registra (re)impressão da comanda para histórico."""
        session = get_session()
        try:
            with session:
                tab = session.get(TabModel, tab_id)
                if not tab:
                    return None
                tab.print_count = (tab.print_count or 0) + 1
                tab.updated_at = datetime.now()
                session.add(tab)
                session.commit()
                session.refresh(tab)
                return Tab(**dict(tab))
        finally:
            session.close()
