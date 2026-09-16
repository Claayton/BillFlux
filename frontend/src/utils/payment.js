const PAYMENT_ICONS = {
  dinheiro: 'fas fa-money-bill-wave',
  pix: 'fas fa-qrcode',
  credito: 'fas fa-credit-card',
  debito: 'fas fa-credit-card',
  vr: 'fas fa-utensils',
  va: 'fas fa-utensils',
  'vr/va': 'fas fa-utensils',
}

const PAYMENT_COLORS = {
  dinheiro: 'pi-dinheiro',
  pix: 'pi-pix',
  credito: 'pi-credito',
  debito: 'pi-debito',
  vr: 'pi-vr',
  va: 'pi-vr',
  'vr/va': 'pi-vr',
}

export function normalizeKey(text) {
  return (text || '')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .trim()
}

export function paymentIcon(payment) {
  return PAYMENT_ICONS[normalizeKey(payment)] || 'fas fa-credit-card'
}

export function paymentColor(payment) {
  return PAYMENT_COLORS[normalizeKey(payment)] || ''
}
