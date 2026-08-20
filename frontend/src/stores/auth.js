import { defineStore } from 'pinia'
import { api } from '@/api/client'

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
      return data
    },
    async logout() {
      await api.post('/auth/logout', {})
      this.user = null
    },
  },
})