"""Module for ProductSupplier (many-to-many: product ↔ supplier with schedule)"""

from typing import Optional

from sqlmodel import SQLModel, Field


class ProductSupplier(SQLModel, table=True):
    """Vínculo produto ↔ fornecedor com agenda de entrega"""

    id: Optional[int] = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="product.id", nullable=False, index=True)
    supplier_id: int = Field(foreign_key="supplier.id", nullable=False, index=True)
    delivery_day: int = Field(nullable=False, default=1)
    lead_time: int = Field(nullable=False, default=1)
    is_primary: bool = Field(default=False)
    frequency: str = Field(nullable=False, default="semanal")
    week_parity: int = Field(nullable=False, default=0)
