/** Cache local del catálogo del PDV en localStorage, invalidado por stamp. */
const KEY = 'pdv:payload'
const STAMP_KEY = 'pdv:stamp'
// Tope de seguridad por si el stamp falla o algo cambia sin bump (2h).
const TTL_MS = 2 * 60 * 60 * 1000

export function readPdvCache(stamp) {
  try {
    const stored = JSON.parse(localStorage.getItem(KEY) || 'null')
    if (!stored || !stored.stamp || !stored.savedAt) return null
    if (stamp && stored.stamp !== stamp) return null
    if (Date.now() - stored.savedAt > TTL_MS) return null
    return stored.payload
  } catch {
    return null
  }
}

export function writePdvCache(stamp, payload) {
  try {
    localStorage.setItem(KEY, JSON.stringify({ stamp, savedAt: Date.now(), payload }))
    localStorage.setItem(STAMP_KEY, stamp)
  } catch {
    /* almacenamiento lleno/privado: seguimos sin cache */
  }
}

export function getPdvStamp() {
  try {
    return localStorage.getItem(STAMP_KEY)
  } catch {
    return null
  }
}

export function clearPdvCache() {
  try {
    localStorage.removeItem(KEY)
    localStorage.removeItem(STAMP_KEY)
  } catch {
    /* ignorar */
  }
}