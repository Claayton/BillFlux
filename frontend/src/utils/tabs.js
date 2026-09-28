/** Status possíveis de uma comanda (espelha billflux/domain/enums.py). */
export const TAB_STATUS = {
  OPEN: 'open',
  CLOSED: 'closed',
  CANCELED: 'canceled',
}

/** Rótulo da comanda: 47 -> "#0047". */
export function tabLabel(number) {
  return '#' + String(number ?? 0).padStart(4, '0')
}
