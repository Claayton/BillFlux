const MONTHS = [
  'jan',
  'fev',
  'mar',
  'abr',
  'mai',
  'jun',
  'jul',
  'ago',
  'set',
  'out',
  'nov',
  'dez',
]

function toNumber(value) {
  if (value === null || value === undefined || value === '') return NaN
  if (typeof value === 'number') return value
  const text = String(value).trim()
  if (text.includes(',')) {
    return Number(text.replace(/\./g, '').replace(',', '.'))
  }
  const dots = (text.match(/\./g) || []).length
  if (dots > 1) {
    return Number(text.replace(/\./g, ''))
  }
  return Number(text)
}

export function brl(value) {
  const n = toNumber(value)
  if (Number.isNaN(n)) return '—'
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(n)
}

export function brdate(value) {
  if (!value) return '—'
  const d = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  })
}

export function brdateShort(value) {
  if (!value) return '—'
  const d = typeof value === 'string' ? new Date(value) : value
  if (Number.isNaN(d.getTime())) return '—'
  return `${String(d.getDate()).padStart(2, '0')} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`
}

// Máscara de moeda BR enquanto digita: "15050" -> "150,50".
export function maskMoney(value) {
  const digits = String(value).replace(/\D/g, '')
  if (!digits) return ''
  const padded = digits.padStart(3, '0')
  const cents = padded.slice(-2)
  const integer = padded.slice(0, -2).replace(/^0+/, '') || '0'
  return integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ',' + cents
}

export function moneyToDecimal(value) {
  if (value === null || value === undefined) return null
  const cleaned = String(value).trim().replace(/\./g, '').replace(',', '.')
  const n = Number(cleaned)
  return Number.isNaN(n) ? null : n
}