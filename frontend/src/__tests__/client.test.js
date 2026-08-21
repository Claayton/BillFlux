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
  beforeEach(() => {
    vi.resetModules()
    vi.restoreAllMocks()
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

  it('GET com erro lança Error com status e mensagem', async () => {
    const { api } = await loadClient(async () =>
      mockResponse({ error: 'não autorizado' }, 401)
    )
    await expect(api.get('/sales')).rejects.toMatchObject({
      status: 401,
      message: 'não autorizado',
    })
  })

  it('GET com erro sem corpo usa status como mensagem', async () => {
    const { api } = await loadClient(async () => mockResponse('', 500))
    await expect(api.get('/sales')).rejects.toMatchObject({
      status: 500,
      message: 'Erro 500',
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
