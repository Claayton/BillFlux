import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/',
    name: 'landing',
    component: () => import('@/views/LandingView.vue'),
    meta: { public: true },
  },
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true },
  },
  {
    path: '/signin',
    name: 'signin',
    component: () => import('@/views/SigninView.vue'),
    meta: { public: true },
  },
  {
    path: '/home',
    name: 'home',
    component: () => import('@/views/DashboardView.vue'),
    meta: { auth: true },
  },
  {
    path: '/sales',
    name: 'sales',
    component: () => import('@/views/SalesView.vue'),
    meta: { auth: true },
  },
  {
    path: '/pdv',
    name: 'pdv',
    component: () => import('@/views/PdvView.vue'),
    meta: { auth: true },
  },
  {
    path: '/pdv/recibo/:id',
    name: 'receipt',
    component: () => import('@/views/ReceiptView.vue'),
    meta: { auth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (auth.loading) {
    try {
      await auth.hydrate()
    } catch {
      /* erro de servidor → segue deslogado */
    }
  }
  if (to.meta.auth && !auth.isAuthenticated) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.public && auth.isAuthenticated && to.name !== 'landing') {
    return { name: 'sales' }
  }
  if (to.name === 'landing' && auth.isAuthenticated) {
    return { name: 'sales' }
  }
  return true
})

export default router