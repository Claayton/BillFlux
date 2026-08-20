let csrfToken = null

async function ensureCsrf() {
  if (csrfToken) return csrfToken
  const res = await fetch('/api/auth/csrf', { credentials: 'same-origin' })
  if (!res.ok) throw new Error('Falha ao obter token de segurança.')
  const data = await res.json()
  csrfToken = data.csrf_token
  return csrfToken
}

export async function apiRequest(method, path, body) {
  const headers = { 'Content-Type': 'application/json' }
  if (method !== 'GET' && method !== 'HEAD') {
    headers['X-CSRFToken'] = await ensureCsrf()
  }
  const options = { method, headers, credentials: 'same-origin' }
  if (body !== undefined) options.body = JSON.stringify(body)

  const res = await fetch(`/api${path}`, options)
  const text = await res.text()
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
  }
  if (!res.ok) {
    const error = new Error((data && data.error) || `Erro ${res.status}`)
    error.status = res.status
    error.data = data
    throw error
  }
  return data
}

export const api = {
  get: (path) => apiRequest('GET', path),
  post: (path, body) => apiRequest('POST', path, body),
  put: (path, body) => apiRequest('PUT', path, body),
  del: (path) => apiRequest('DELETE', path),
}