import { describe, it, expect, vi, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
  },
}))

vi.mock('@/api/client', () => ({ api: apiMock }))

import { useAuthStore } from '@/stores/auth'

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
})
