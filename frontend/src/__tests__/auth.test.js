import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { apiMock, resetCsrfMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
  },
  resetCsrfMock: vi.fn(),
}))

vi.mock('@/api/client', () => ({ api: apiMock, resetCsrf: resetCsrfMock }))

import { clearHadSession, hadPreviousSession, useAuthStore } from '@/stores/auth'

function mockSessionStorage() {
  let store = {}
  global.sessionStorage = {
    getItem: (key) => (key in store ? store[key] : null),
    setItem: (key, value) => {
      store[key] = String(value)
    },
    removeItem: (key) => {
      delete store[key]
    },
    clear: () => {
      store = {}
    },
  }
}

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    apiMock.get.mockReset()
    apiMock.post.mockReset()
  })

  it('hydrate autentica e carrega flags', async () => {
    apiMock.get.mockResolvedValue({ user: 'coqueiral', allow_signup: true })
    const store = useAuthStore()
    await store.hydrate()
    expect(store.user).toBe('coqueiral')
    expect(store.allowSignup).toBe(true)
    expect(store.loading).toBe(false)
    expect(store.isAuthenticated).toBe(true)
  })

  it('hydrate com 401 deixa deslogado', async () => {
    const error = new Error('não autorizado')
    error.status = 401
    apiMock.get.mockRejectedValue(error)
    const store = useAuthStore()
    await store.hydrate()
    expect(store.user).toBe(null)
    expect(store.loading).toBe(false)
    expect(store.isAuthenticated).toBe(false)
  })

  it('login guarda o usuário', async () => {
    apiMock.post.mockResolvedValue({ user: 'admin', allow_signup: false })
    const store = useAuthStore()
    await store.login('admin', 'admin')
    expect(apiMock.post).toHaveBeenCalledWith('/auth/login', {
      username: 'admin',
      password: 'admin',
    })
    expect(store.user).toBe('admin')
  })

  it('logout limpa o usuário', async () => {
    apiMock.post.mockResolvedValue({})
    const store = useAuthStore()
    store.user = 'admin'
    await store.logout()
    expect(store.user).toBe(null)
  })

  it('login marca e logout limpa o flag de sessão da aba', async () => {
    mockSessionStorage()
    global.sessionStorage.clear()
    clearHadSession()
    expect(hadPreviousSession()).toBe(false)

    apiMock.post.mockResolvedValue({ user: 'admin', allow_signup: false })
    const store = useAuthStore()
    await store.login('admin', 'admin')
    expect(hadPreviousSession()).toBe(true)

    apiMock.post.mockResolvedValue({})
    await store.logout()
    expect(hadPreviousSession()).toBe(false)

    delete global.sessionStorage
  })

  it('sem sessionStorage (node) não quebra login/logout', async () => {
    expect(hadPreviousSession()).toBe(false)
    apiMock.post.mockResolvedValue({ user: 'admin', allow_signup: false })
    const store = useAuthStore()
    await store.login('admin', 'admin')
    expect(store.user).toBe('admin')
    clearHadSession()
  })
})
