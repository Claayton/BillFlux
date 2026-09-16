/**
 * Remove acentos/diacríticos de uma string.
 * 'Saída' → 'Saida', 'Império' → 'Imperio'
 */
export function stripAccents(text) {
  if (!text) return text
  return text.normalize('NFD').replace(/[\u0300-\u036f]/g, '')
}

/**
 * Normaliza para busca: sem acento + lowercase.
 */
export function normalizeForSearch(text) {
  return stripAccents((text || '').toLowerCase())
}
