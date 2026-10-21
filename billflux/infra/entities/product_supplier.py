"""Module for ProductSupplier (many-to-many: product ↔ supplier with schedule)"""

from typing import Optional

from sqlmodel import SQLModel, Field


class ProductSupplier(SQLModel, table=True):
    """Vínculo produto ↔ fornecedor com agenda de entrega"""

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", nullable=False, index=True)
    supplier_id: int = Field(foreign_key="supplier.id", nullable=False, index=True)
    delivery_day: int = Field(nullable=False, default=1)
    # Lista de dias (JSON: "[1, 3, 5]", 0=domingo ... 6=sábado). Mantém
    # delivery_day como o "primeiro dia" para retrocompatibilidade.
    delivery_days: Optional[str] = Field(default=None, nullable=True)
    lead_time: int = Field(nullable=False, default=1)
    is_primary: bool = Field(default=False)
    frequency: str = Field(nullable=False, default="semanal")
    week_parity: int = Field(nullable=False, default=0)
