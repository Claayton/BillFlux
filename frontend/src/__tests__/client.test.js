import { describe, it, expect, vi, beforeEach } from 'vitest'

function mockResponse(data, status = 200) {
  const body = typeof data === 'string' ? data : JSON.stringify(data)
  return {
    ok: status >= 200 && status < 300,
    status,
    text: async () => body,
    json: async () => JSON.parse(body),
  }
}

describe('api client', () => {
  function setOnLine(value) {
    Object.defineProperty(navigator, 'onLine', {
      configurable: true,
      get: () => value,
    })
  }

  beforeEach(() => {
    vi.resetModules()
    vi.restoreAllMocks()
    setOnLine(true)
  })

  async function loadClient(fetchImpl) {
    global.fetch = vi.fn(fetchImpl)
    return import('@/api/client')
  }

  it('GET devolve o JSON parseado', async () => {
    const { api } = await loadClient(async () =>
      mockResponse({ ok: true, total: 20 })
    )
    const data = await api.get('/sales')
    expect(data).toEqual({ ok: true, total: 20 })
    expect(global.fetch).toHaveBeenCalledWith('/api/sales', expect.anything())
  })

  it('401 em rota protegida marca sessão expirada e chama o handler', async () => {
    const handler = vi.fn()
    const mod = await loadClient(async () =>
      mockResponse({ error: 'Não autenticado.' }, 401)
    )
    mod.setUnauthorizedHandler(handler)

    await expect(mod.api.get('/sales')).rejects.toMatchObject({
      status: 401,
      sessionExpired: true,
      message: mod.SESSION_EXPIRED_MESSAGE,
    })
    expect(handler).toHaveBeenCalledTimes(1)
  })

  it('401 no login (senha errada) não dispara o handler de sessão', async () => {
    const handler = vi.fn()
    const mod = await loadClient(async (url) => {
      if (url === '/api/auth/csrf') return mockResponse({ csrf_token: 'tok' })
      return mockResponse({ error: 'Usuário ou senha inválidos.' }, 401)
    })
    mod.setUnauthorizedHandler(handler)

    await expect(
      mod.api.post('/auth/login', { username: 'admin', password: 'x' })
    ).rejects.toMatchObject({
      status: 401,
      message: 'Usuário ou senha inválidos.',
    })
    expect(handler).not.toHaveBeenCalled()
  })

  it('POST com 400 sem JSON (CSRF velho) renova o token e repete 1x', async () => {
    const calls = []
    const mod = await loadClient(async (url, opts) => {
      calls.push({ url, opts })
      if (url === '/api/auth/csrf') {
        return mockResponse({ csrf_token: `tok${calls.length}` })
      }
      if (calls.filter((c) => c.url === '/api/sales').length === 1) {
        return { ok: false, status: 400, text: async () => '<html>CSRF Failed</html>' }
      }
      return mockResponse({ ok: true })
    })

    const data = await mod.api.post('/sales', { total: 10 })

    expect(data).toEqual({ ok: true })
    expect(calls.filter((c) => c.url === '/api/auth/csrf')).toHaveLength(2)
    expect(calls.filter((c) => c.url === '/api/sales')).toHaveLength(2)
    expect(calls.at(-1).opts.headers['X-CSRFToken']).toBe('tok3')
  })

  it('POST com 400 JSON (validação) não repete a requisição', async () => {
    const calls = []
    const mod = await loadClient(async (url) => {
      calls.push(url)
      if (url === '/api/auth/csrf') {
        return mockResponse({ csrf_token: 'tok' })
      }
      return mockResponse({ error: 'Campo inválido.' }, 400)
    })

    await expect(mod.api.post('/sales', {})).rejects.toMatchObject({
      status: 400,
      message: 'Campo inválido.',
    })
    expect(calls.filter((c) => c === '/api/auth/csrf')).toHaveLength(1)
    expect(calls.filter((c) => c === '/api/sales')).toHaveLength(1)
  })

  it('GET com erro 500 sem corpo usa mensagem amigável de servidor', async () => {
    const mod = await loadClient(async () => mockResponse('', 500))
    await expect(mod.api.get('/sales')).rejects.toMatchObject({
      status: 500,
      message: mod.SERVER_ERROR_MESSAGE,
    })
  })

  it('GET com erro 4xx sem corpo mantém o status', async () => {
    const mod = await loadClient(async () => mockResponse('', 404))
    await expect(mod.api.get('/sales')).rejects.toMatchObject({
      status: 404,
      message: 'Erro 404',
    })
  })

  it('falha de rede com cliente offline → mensagem de sem conexão', async () => {
    setOnLine(false)
    const mod = await loadClient(async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(mod.api.get('/sales')).rejects.toMatchObject({
      message: mod.OFFLINE_MESSAGE,
    })
  })

  it('falha de rede estando online → mensagem de servidor inacessível', async () => {
    setOnLine(true)
    const mod = await loadClient(async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(mod.api.get('/sales')).rejects.toMatchObject({
      message: mod.SERVER_UNREACHABLE_MESSAGE,
    })
  })

  it('falha de rede na busca do CSRF também vira mensagem amigável', async () => {
    setOnLine(false)
    const mod = await loadClient(async () => {
      throw new TypeError('Failed to fetch')
    })
    await expect(mod.api.post('/sales', { total: 1 })).rejects.toMatchObject({
      message: mod.OFFLINE_MESSAGE,
    })
  })

  it('POST busca o CSRF uma vez e envia o token', async () => {
    const calls = []
    const { api } = await loadClient(async (url, opts) => {
      calls.push({ url, opts })
      if (url === '/api/auth/csrf') {
        return mockResponse({ csrf_token: 'tok' })
      }
      return mockResponse({ user: 'admin' })
    })

    await api.post('/auth/login', { username: 'admin' })

    expect(calls.map((c) => c.url)).toEqual(['/api/auth/csrf', '/api/auth/login'])
    expect(calls[1].opts.headers['X-CSRFToken']).toBe('tok')
    expect(calls[1].opts.headers['Content-Type']).toBe('application/json')
    expect(JSON.parse(calls[1].opts.body)).toEqual({ username: 'admin' })
  })
})
