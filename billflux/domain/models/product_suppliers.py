"""Domain model for ProductSupplier"""

from typing import NamedTuple


class ProductSupplier(NamedTuple):
    id: int
    product_id: int
    supplier_id: int
    supplier_name: str
    product_name: str
    delivery_day: int
    lead_time: int
    is_primary: bool
    frequency: str = "semanal"
    week_parity: int = 0
