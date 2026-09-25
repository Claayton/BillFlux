import { defineStore } from 'pinia'
import { api, resetCsrf } from '@/api/client'

const HAD_SESSION_KEY = 'beeflux.hadSession'

function storageGet(key) {
  try {
    return sessionStorage.getItem(key)
  } catch {
    return null
  }
}

function storageSet(key, value) {
  try {
    sessionStorage.setItem(key, value)
  } catch {
    /* sem storage (ex.: testes) */
  }
}

function storageRemove(key) {
  try {
    sessionStorage.removeItem(key)
  } catch {
    /* sem storage (ex.: testes) */
  }
}

/** Houve login nesta aba (mesmo que a sessão já tenha morrido). */
export function hadPreviousSession() {
  return storageGet(HAD_SESSION_KEY) === '1'
}

export function clearHadSession() {
  storageRemove(HAD_SESSION_KEY)
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    allowSignup: false,
    loading: true,
  }),
  getters: {
    isAuthenticated: (state) => Boolean(state.user),
  },
  actions: {
    async hydrate() {
      try {
        const data = await api.get('/auth/me')
        this.user = data.user
        this.allowSignup = data.allow_signup
      } catch (error) {
        if (error.status !== 401) throw error
        this.user = null
      } finally {
        this.loading = false
      }
    },
    async login(username, password) {
      const data = await api.post('/auth/login', { username, password })
      this.user = data.user
      this.allowSignup = data.allow_signup
      storageSet(HAD_SESSION_KEY, '1')
      // O login invalida a sessão anterior: descarta o CSRF cacheado.
      resetCsrf()
      return data
    },
    async logout() {
      try {
        await api.post('/auth/logout', {})
      } finally {
        this.user = null
        clearHadSession()
        resetCsrf()
      }
    },
  },
})