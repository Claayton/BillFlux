<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const sidebarOpen = ref(false)

const navSections = [
  {
    items: [
      { name: 'sales', label: 'Vendas', icon: 'fas fa-cash-register', to: '/sales' },
      { name: 'caixa', label: 'Caixa', icon: 'fas fa-cash-register', to: '/caixa' },
    ]
  },
  {
    items: [
      { name: 'products', label: 'Produtos', icon: 'fas fa-box-open', to: '/products' },
      { name: 'suppliers', label: 'Fornecedores', icon: 'fas fa-truck', to: '/suppliers' },
      { name: 'purchases', label: 'Compras', icon: 'fas fa-truck-loading', to: '/purchases' },
      { name: 'schedule', label: 'Agenda de pedidos', icon: 'fas fa-calendar-alt', to: '/schedule' },
    ]
  },
  {
    items: [
      { name: 'customers', label: 'Clientes', icon: 'fas fa-users', to: '/customers' },
      { name: 'categories', label: 'Categorias', icon: 'fas fa-tags', to: '/categories' },
      { name: 'payments', label: 'Formas de pagamento', icon: 'fas fa-credit-card', to: '/payments' },
      { name: 'bills', label: 'Contas', icon: 'fas fa-file-invoice', to: '/bills' },
      { name: 'accounts', label: 'Plano de contas', icon: 'fas fa-list-ul', to: '/accounts' },
    ]
  },
  {
    items: [
      { name: 'home', label: 'Visão geral', icon: 'fas fa-th-large', to: '/home' },
    ]
  },
]

function isActive(item) {
  return route.name === item.name
}

function closeSidebar() {
  sidebarOpen.value = false
}

async function logout() {
  await auth.logout()
  router.push('/')
}
</script>

<template>
  <div class="app-mode">
    <aside class="sidebar" :class="{ 'is-open': sidebarOpen }">
      <a class="logo" href="/">
        <span class="logo-mark">BF</span>
        <span class="logo-text">BillFlux</span>
      </a>
      <nav class="sidebar-nav" aria-label="Navegação principal">
        <template v-for="(section, sIdx) in navSections" :key="sIdx">
          <ul>
            <li v-for="item in section.items" :key="item.name">
              <router-link
                :to="item.to"
                :class="{ 'is-active': isActive(item) }"
              >
                <i :class="item.icon"></i> {{ item.label }}
              </router-link>
            </li>
          </ul>
          <div v-if="sIdx < navSections.length - 1" class="sidebar-divider"></div>
        </template>
      </nav>
      <div class="sidebar-user">
        <span class="avatar">{{ (auth.user || '?')[0].toUpperCase() }}</span>
        <span class="user-name">{{ auth.user }}</span>
        <a href="#" @click.prevent="logout" title="Sair" aria-label="Sair">
          <i class="fas fa-sign-out-alt"></i>
        </a>
      </div>
    </aside>

    <div class="app-shell">
      <header class="topbar">
        <button
          type="button"
          class="icon-btn app-hamburger"
          aria-label="Abrir menu"
          aria-expanded="false"
          @click="sidebarOpen = !sidebarOpen"
        >
          <i class="fas fa-bars"></i>
        </button>
        <router-link class="btn btn-primary btn-sm" to="/pdv">
          <i class="fas fa-cash-register"></i> Abrir PDV
        </router-link>
        <div class="topbar-spacer"></div>
        <button type="button" class="icon-btn" title="Notificações" aria-label="Notificações">
          <i class="fas fa-bell"></i>
        </button>
      </header>
      <main class="site-main">
        <slot />
      </main>
    </div>

    <div v-if="sidebarOpen" class="sidebar-overlay" @click="closeSidebar"></div>
  </div>
</template>