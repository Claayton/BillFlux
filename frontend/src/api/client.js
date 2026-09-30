let csrfToken = null
let unauthorizedHandler = null

export const SESSION_EXPIRED_MESSAGE = 'Sua sessão expirou. Entre novamente.'
export const OFFLINE_MESSAGE =
  'Você está sem conexão com a internet. Verifique sua rede e tente novamente.'
export const SERVER_UNREACHABLE_MESSAGE =
  'Não conseguimos conectar ao servidor. Tente novamente em instantes.'
export const SERVER_ERROR_MESSAGE =
  'O servidor está indisponível no momento. Tente novamente em instantes.'

/** Registra o callback global de sessão expirada (main.js: redirect p/ login). */
export function setUnauthorizedHandler(fn) {
  unauthorizedHandler = fn
}

/** Descarta o CSRF cacheado (ex.: após 401 ou falha de CSRF). */
export function resetCsrf() {
  csrfToken = null
}

/**
 * Erro amigável quando a requisição nem completa (rede/servidor).
 * Usa `navigator.onLine` como pista pra diferenciar "cliente sem internet"
 * de "servidor inacessível" — é heurístico, mas acerta no caso comum.
 */
function connectionError() {
  const offline = typeof navigator !== 'undefined' && navigator.onLine === false
  return new Error(offline ? OFFLINE_MESSAGE : SERVER_UNREACHABLE_MESSAGE)
}

async function ensureCsrf() {
  if (csrfToken) return csrfToken
  let res
  try {
    res = await fetch('/api/auth/csrf', { credentials: 'same-origin' })
  } catch {
    throw connectionError()
  }
  if (!res.ok) throw new Error(SERVER_ERROR_MESSAGE)
  const data = await res.json()
  csrfToken = data.csrf_token
  return csrfToken
}

/** 401 no /auth/login é "senha errada" — não é sessão expirada. */
function isLoginAttempt(path) {
  return path === '/auth/login' || path.startsWith('/auth/login?')
}

/**
 * Falha de CSRF do Flask-WTF vem como 400 com corpo HTML (não JSON).
 * Nossos erros de validação sempre voltam como JSON {"error": ...}.
 */
function looksLikeCsrfFailure(status, data) {
  return status === 400 && data === null
}

async function doFetch(method, path, body, csrf) {
  const headers = { 'Content-Type': 'application/json' }
  if (method !== 'GET' && method !== 'HEAD') {
    headers['X-CSRFToken'] = csrf
  }
  const options = { method, headers, credentials: 'same-origin' }
  if (body !== undefined) options.body = JSON.stringify(body)

  let res
  let text
  try {
    res = await fetch(`/api${path}`, options)
    text = await res.text()
  } catch {
    throw connectionError()
  }
  let data = null
  if (text) {
    try {
      data = JSON.parse(text)
    } catch {
      data = null
    }
  }
  return { res, data }
}

function toError(res, data) {
  const message =
    (data && data.error) ||
    (res.status >= 500 ? SERVER_ERROR_MESSAGE : `Erro ${res.status}`)
  const error = new Error(message)
  error.status = res.status
  error.data = data
  return error
}

export async function apiRequest(method, path, body) {
  const needsCsrf = method !== 'GET' && method !== 'HEAD'
  let { res, data } = await doFetch(method, path, body, needsCsrf ? await ensureCsrf() : undefined)

  if (needsCsrf && looksLikeCsrfFailure(res.status, data)) {
    // Token CSRF velho (ex.: aba parada por horas): renova 1x e repete.
    resetCsrf()
    ;({ res, data } = await doFetch(method, path, body, await ensureCsrf()))
  }

  if (!res.ok) {
    const error = toError(res, data)
    if (res.status === 401 && !isLoginAttempt(path)) {
      // Sessão morta em rota protegida: avisa o app (redirect p/ login).
      resetCsrf()
      error.sessionExpired = true
      error.message = SESSION_EXPIRED_MESSAGE
      if (unauthorizedHandler) {
        try {
          unauthorizedHandler(error)
        } catch {
          /* handler nunca pode quebrar a chamada */
        }
      }
    }
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
