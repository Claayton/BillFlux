"""Versionado ligero de los datos del PDV para cache local del navegador.

El PDV descarga todo el catálogo (productos, presentaciones, clientes) en cada
carga. Para evitarlo el front guarda en localStorage el payload de ``/pdv``
junto a un ``stamp`` de versión; cuando el stamp cambia, recarga.

El stamp combina:
- ``setting.pdv.version``: contador que se incrementa al editar productos o
  presentaciones (precio/costo/nombre/factor/activo) — cambios que NO generan
  movimiento ni fila nueva.
- máx(id)/count de productos, presentaciones, movimientos, clientes y formas
  de pago (cubre altas y movimientos de stock de ventas/compras/comandas).
"""

from sqlmodel import select

from billflux.infra.config.database import get_session
from billflux.infra.entities.setting import Setting as SettingModel

PDV_VERSION_KEY = "pdv.version"


def bump_pdv_version():
    """Incrementa el contador que invalida el cache del PDV."""
    session = get_session()
    try:
        with session:
            row = session.get(SettingModel, PDV_VERSION_KEY)
            current = int(row.value or "0") if row and row.value else 0
            value = str(current + 1)
            if row is None:
                row = SettingModel(key=PDV_VERSION_KEY, value=value)
            else:
                row.value = value
            session.add(row)
            session.commit()
    finally:
        session.close()


def get_pdv_version() -> int:
    session = get_session()
    try:
        with session:
            row = session.get(SettingModel, PDV_VERSION_KEY)
            if not row or not row.value:
                return 0
            try:
                return int(row.value)
            except (TypeError, ValueError):
                return 0
    finally:
        session.close()
