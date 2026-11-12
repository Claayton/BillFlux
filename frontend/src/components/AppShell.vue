<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import logoUrl from '@/assets/logo.png'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const sidebarOpen = ref(false)

const GROUPS_KEY = 'billflux.sidebar.groups'

const nav = [
  { kind: 'link', name: 'home', label: 'Visão geral', icon: 'fas fa-th-large', to: '/home' },
  { kind: 'link', name: 'sales', label: 'Vendas', icon: 'fas fa-cash-register', to: '/sales' },
  { kind: 'link', name: 'caixa', label: 'Caixa', icon: 'fas fa-money-bill-wave', to: '/caixa' },
  {
    kind: 'group',
    id: 'produtos',
    label: 'Produtos',
    icon: 'fas fa-box-open',
    items: [
      { name: 'products', label: 'Produtos', icon: 'fas fa-box-open', to: '/products', active: () => route.name === 'products' && route.query.fiscal !== 'pending' },
      { name: 'categories', label: 'Categorias', icon: 'fas fa-tags', to: '/categories' },
      { name: 'suppliers', label: 'Fornecedores', icon: 'fas fa-truck', to: '/suppliers' },
      { name: 'purchases', label: 'Compras', icon: 'fas fa-truck-loading', to: '/purchases' },
      {
        name: 'schedule',
        label: 'Agenda de pedidos',
        icon: 'fas fa-calendar-alt',
        to: '/schedule',
      },
    ],
  },
  {
    kind: 'group',
    id: 'clientes',
    label: 'Clientes',
    icon: 'fas fa-users',
    items: [
      { name: 'customers', label: 'Clientes', icon: 'fas fa-users', to: '/customers' },
      { name: 'fiado', label: 'Fiado', icon: 'fas fa-hand-holding-usd', to: '/fiado' },
    ],
  },
  {
    kind: 'group',
    id: 'financeiro',
    label: 'Financeiro',
    icon: 'fas fa-chart-pie',
    items: [
      { name: 'bills', label: 'Contas', icon: 'fas fa-file-invoice', to: '/bills' },
      { name: 'accounts', label: 'Plano de contas', icon: 'fas fa-list-ul', to: '/accounts' },
      {
        name: 'payments',
        label: 'Formas de pagamento',
        icon: 'fas fa-credit-card',
        to: '/payments',
      },
      { name: 'reports', label: 'Relatórios', icon: 'fas fa-chart-bar', to: '/reports' },
    ],
  },
  {
    kind: 'group',
    id: 'fiscal',
    label: 'Fiscal',
    icon: 'fas fa-file-invoice-dollar',
    items: [
      {
        name: 'fiscal-pending',
        label: 'Pendências fiscais',
        icon: 'fas fa-list-check',
        to: '/products?fiscal=pending',
        active: () => route.name === 'products' && route.query.fiscal === 'pending',
      },
      {
        name: 'fiscal-config',
        label: 'Configuração fiscal',
        icon: 'fas fa-sliders',
        to: '/config?tab=fiscal',
        active: () => route.name === 'config' && route.query.tab === 'fiscal',
      },
    ],
  },
  {
    kind: 'link',
    name: 'config',
    label: 'Configurações',
    icon: 'fas fa-cog',
    to: '/config',
    active: () => route.name === 'config' && !route.query.tab,
  },
]

function readGroups() {
  try {
    const stored = JSON.parse(localStorage.getItem(GROUPS_KEY) || '{}')
    return stored && typeof stored === 'object' ? stored : {}
  } catch {
    return {}
  }
}

const openGroups = ref(readGroups())

function persistGroups() {
  try {
    localStorage.setItem(GROUPS_KEY, JSON.stringify(openGroups.value))
  } catch {
    /* armazenamento indisponível: mantém só em memória */
  }
}

function toggleGroup(id) {
  openGroups.value = { ...openGroups.value, [id]: !openGroups.value[id] }
  persistGroups()
}

function isLinkActive(item) {
  if (typeof item.active === 'function') return item.active()
  return route.name === item.name
}

function isGroupActive(group) {
  return group.items.some(isLinkActive)
}

const activeGroupId = computed(() => {
  const group = nav.find((entry) => entry.kind === 'group' && isGroupActive(entry))
  return group ? group.id : null
})

// O grupo do item ativo abre sozinho (sem sobrescrever o que o usuário fechou).
watch(
  activeGroupId,
  (id) => {
    if (id && !openGroups.value[id]) {
      openGroups.value = { ...openGroups.value, [id]: true }
      persistGroups()
    }
  },
  { immediate: true }
)

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
        <img class="logo-mark" :src="logoUrl" alt="BeeFlux" />
        <span class="logo-text">eeFlux</span>
      </a>
      <nav class="sidebar-nav" aria-label="Navegação principal">
        <template v-for="entry in nav" :key="entry.id || entry.name">
          <router-link
            v-if="entry.kind === 'link'"
            :to="entry.to"
            :class="{ 'is-active': isLinkActive(entry) }"
            @click="closeSidebar"
          >
            <i :class="entry.icon"></i> {{ entry.label }}
          </router-link>

          <div v-else class="sidebar-group">
            <button
              type="button"
              class="sidebar-group-toggle"
              :class="{ 'is-active': isGroupActive(entry), 'is-open': openGroups[entry.id] }"
              :aria-expanded="openGroups[entry.id] ? 'true' : 'false'"
              @click="toggleGroup(entry.id)"
            >
              <i :class="entry.icon"></i>
              <span class="sidebar-group-label">{{ entry.label }}</span>
              <i class="fas fa-chevron-down sidebar-chevron"></i>
            </button>

            <ul v-show="openGroups[entry.id]" class="sidebar-submenu">
              <li v-for="child in entry.items" :key="child.name">
                <router-link
                  :to="child.to"
                  :class="{ 'is-active': isLinkActive(child) }"
                  @click="closeSidebar"
                >
                  <i :class="child.icon"></i> {{ child.label }}
                </router-link>
              </li>
            </ul>
          </div>
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

<style scoped>
.sidebar-group {
  display: flex;
  flex-direction: column;
  margin-bottom: 3px;
}

/* Mantém a marca do item ativo visível mesmo com rolagem no menu. */
.sidebar-nav {
  overflow-y: auto;
  margin-left: -14px;
  padding-left: 14px;
  padding-bottom: 8px;
  scrollbar-width: thin;
}

.sidebar-nav > a {
  margin-bottom: 3px;
}

.sidebar-group-toggle {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  border: 0;
  border-radius: var(--radius);
  background: transparent;
  color: var(--text-secondary);
  font-family: inherit;
  font-size: 14px;
  font-weight: 500;
  text-align: left;
  cursor: pointer;
  transition: color 150ms ease, background-color 150ms ease;
}

.sidebar-group-toggle > i:first-child {
  width: 20px;
  text-align: center;
  font-size: 15px;
  color: var(--text-muted);
  transition: color 150ms ease;
}

.sidebar-group-toggle:hover {
  color: var(--text);
  background: var(--surface-hover);
}

.sidebar-group-toggle:hover > i:first-child {
  color: var(--primary);
}

.sidebar-group-toggle.is-active {
  color: var(--primary-hover);
  font-weight: 700;
}

.sidebar-group-toggle.is-active > i:first-child {
  color: var(--primary);
}

.sidebar-group-label {
  flex: 1;
  min-width: 0;
}

.sidebar-chevron {
  width: auto !important;
  font-size: 10px !important;
  color: var(--text-muted);
  transition: transform 150ms ease;
}

.sidebar-group-toggle.is-open .sidebar-chevron {
  transform: rotate(180deg);
}

.sidebar-group-toggle:focus-visible {
  outline: none;
  box-shadow: var(--focus-ring);
}

.sidebar-submenu {
  display: flex;
  flex-direction: column;
  gap: 2px;
  list-style: none;
  margin: 2px 0 4px 21px;
  padding-left: 12px;
  border-left: 1px solid var(--border);
}

.sidebar-nav .sidebar-submenu a {
  padding: 8px 10px;
  font-size: 13px;
}

.sidebar-nav .sidebar-submenu a i {
  width: 16px;
  font-size: 12px;
}

.sidebar-nav .sidebar-submenu a.is-active::before {
  display: none;
}
</style>
