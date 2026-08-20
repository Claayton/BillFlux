<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'

const router = useRouter()

const products = ref([])
const methods = ref([])
const search = ref('')
const suggestions = ref([])
const highlighted = ref(-1)
const selectedMethod = ref(null)
const obs = ref('')
const finishing = ref(false)
const attention = ref(false)

const searchInput = ref(null)
const cart = ref(new Map())

const cartItems = computed(() => Array.from(cart.value.values()))
const cartCount = computed(() => cartItems.value.reduce((sum, item) => sum + item.qty, 0))
const cartTotal = computed(() => cartItems.value.reduce((sum, item) => sum + item.price * item.qty, 0))
const countLabel = computed(() => cartCount.value + (cartCount.value === 1 ? ' item' : ' itens'))

function formatBRL(value) {
  return (
    'R$ ' +
    value
      .toFixed(2)
      .replace('.', ',')
      .replace(/\B(?=(\d{3})+(?!\d))/g, '.')
  )
}

async function load() {
  try {
    const data = await api.get('/pdv')
    products.value = data.products
    methods.value = data.methods
    searchInput.value?.focus()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function byId(productId) {
  return products.value.find((p) => p.id === productId)
}

function incQty(productId) {
  const product = byId(productId)
  if (!product || product.stock <= 0) return
  const item = cart.value.get(productId)
  if (item) {
    if (item.qty < product.stock) item.qty += 1
  } else {
    cart.value.set(productId, {
      id: product.id,
      name: product.name,
      price: product.price,
      stock: product.stock,
      qty: 1,
    })
  }
}

function setQty(productId, quantity) {
  const product = byId(productId)
  if (!product || product.stock <= 0) return
  const target = Math.min(Math.max(1, quantity), product.stock)
  cart.value.set(productId, {
    id: product.id,
    name: product.name,
    price: product.price,
    stock: product.stock,
    qty: target,
  })
}

function changeQty(productId, delta) {
  const item = cart.value.get(productId)
  if (!item) return
  const next = item.qty + delta
  if (next < 1 || next > item.stock) return
  item.qty = next
}

function removeItem(productId) {
  cart.value.delete(productId)
}

// ---------- Busca / sugestões ----------
function buildSuggestions(term) {
  const lower = term.toLowerCase()
  return products.value.filter(
    (p) => p.name.toLowerCase().includes(lower) || p.barcode.toLowerCase().includes(lower)
  )
}

function showSuggestions() {
  suggestions.value = buildSuggestions(search.value.trim())
  highlighted.value = suggestions.value.length ? 0 : -1
}

function setHighlight(index) {
  highlighted.value = index
}

function clearSearch() {
  search.value = ''
  suggestions.value = []
  highlighted.value = -1
  searchInput.value?.focus()
}

function addFromSuggestion(product) {
  incQty(product.id)
  clearSearch()
}

function handleEnter() {
  const raw = search.value.trim()
  if (!raw) return

  const multiply = raw.match(/^(\d+)\s*\*\s*(.+)$/)
  if (multiply) {
    const n = parseInt(multiply[1], 10)
    const term = multiply[2].trim().toLowerCase()
    const product =
      products.value.find((p) => p.barcode === term) ||
      products.value.find((p) => p.name.toLowerCase() === term)
    if (product) {
      setQty(product.id, n)
      clearSearch()
      return
    }
  }

  const lower = raw.toLowerCase()
  const byBarcode = products.value.find((p) => p.barcode === lower)
  if (byBarcode) {
    incQty(byBarcode.id)
    clearSearch()
    return
  }

  if (highlighted.value >= 0 && suggestions.value[highlighted.value]) {
    incQty(suggestions.value[highlighted.value].id)
    clearSearch()
    return
  }

  if (suggestions.value.length === 1) {
    incQty(suggestions.value[0].id)
    clearSearch()
  }
}

function onSearchInput() {
  showSuggestions()
}

function onSearchKeydown(event) {
  if (event.key === 'Enter') {
    event.preventDefault()
    handleEnter()
  } else if (event.key === 'ArrowDown') {
    event.preventDefault()
    if (suggestions.value.length) {
      setHighlight((highlighted.value + 1) % suggestions.value.length)
    }
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    if (suggestions.value.length) {
      setHighlight((highlighted.value - 1 + suggestions.value.length) % suggestions.value.length)
    }
  } else if (event.key === 'Escape') {
    suggestions.value = []
  }
}

function hideSuggestions() {
  setTimeout(() => {
    suggestions.value = []
  }, 150)
}

// ---------- Finalizar venda ----------
async function finishSale() {
  if (cart.value.size === 0) return
  if (!selectedMethod.value) {
    attention.value = true
    setTimeout(() => {
      attention.value = false
    }, 1200)
    return
  }
  finishing.value = true
  try {
    const items = cartItems.value.map((item) => ({
      product_id: item.id,
      quantity: item.qty,
    }))
    const data = await api.post('/pdv/complete', {
      method_id: selectedMethod.value,
      obs: obs.value,
      items,
    })
    cart.value.clear()
    router.push(`/pdv/recibo/${data.order.order_id}`)
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    finishing.value = false
  }
}

function onGlobalKeydown(event) {
  if (event.key !== 'F2') return
  event.preventDefault()
  finishSale()
}

onMounted(() => {
  load()
  document.addEventListener('keydown', onGlobalKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onGlobalKeydown)
})
</script>

<template>
  <div class="pdv-screen">
    <header class="pdv-topbar">
      <router-link class="pdv-brand" to="/pdv" aria-label="Ponto de venda">
        <span class="pdv-brand-mark">BF</span>
        <span class="pdv-brand-text">BillFlux</span>
      </router-link>

      <div class="pdv-search-wrap">
        <i class="fas fa-search pdv-search-icon"></i>
        <input
          ref="searchInput"
          id="pdv-search"
          v-model="search"
          class="pdv-search"
          type="text"
          placeholder="Digite o código de barras ou o nome do produto..."
          autocomplete="off"
          spellcheck="false"
          @input="onSearchInput"
          @keydown="onSearchKeydown"
          @blur="hideSuggestions"
        />
        <div id="pdv-suggestions" class="pdv-suggestions" :hidden="!suggestions.length">
          <button
            v-for="(p, i) in suggestions"
            :key="p.id"
            type="button"
            class="pdv-suggestion"
            :class="{ 'is-highlighted': i === highlighted }"
            @mousedown.prevent="addFromSuggestion(p)"
          >
            <span class="pdv-suggestion-info">
              <span class="pdv-suggestion-name">{{ p.name }}</span>
              <span class="pdv-suggestion-sub">{{ p.barcode ? 'Cód.: ' + p.barcode : 'Sem código de barras' }}</span>
            </span>
            <span class="pdv-suggestion-price">{{ formatBRL(p.price) }}</span>
            <span class="pdv-suggestion-stock" :class="{ 'is-out': p.stock <= 0 }">
              {{ p.stock <= 0 ? 'Esgotado' : p.stock + ' un' }}
            </span>
          </button>
        </div>
      </div>

      <router-link class="pdv-exit" to="/home" title="Sair do PDV" aria-label="Sair do PDV">
        <i class="fas fa-arrow-left"></i>
      </router-link>
    </header>

    <main class="pdv-main">
      <section class="pdv-items" id="pdv-items">
        <div class="pdv-items-head">
          <span>Itens do carrinho</span>
          <span class="pdv-items-count" id="cart-count">{{ countLabel }}</span>
        </div>

        <div class="pdv-list" id="cart-items">
          <div v-if="!cartItems.length" class="pdv-empty">
            <div class="pdv-empty-icon"><i class="fas fa-shopping-cart"></i></div>
            <h2>Carrinho vazio</h2>
            <p>Digite o código de barras ou o nome do produto para começar.</p>
          </div>

          <div v-for="item in cartItems" :key="item.id" class="pdv-row">
            <span class="pdv-row-num">#{{ item.id }}</span>
            <span class="pdv-row-qty">{{ item.qty }}</span>
            <span class="pdv-row-info">
              <span class="pdv-row-name">{{ item.name }}</span>
              <span class="pdv-row-sub">{{ formatBRL(item.price) }} / un</span>
            </span>
            <span class="pdv-row-price">{{ formatBRL(item.price * item.qty) }}</span>
            <span class="pdv-row-qty-ctrl">
              <button
                type="button"
                :aria-label="'Diminuir quantidade de ' + item.name"
                :disabled="item.qty <= 1"
                @click="changeQty(item.id, -1)"
              >
                &minus;
              </button>
              <button
                type="button"
                :aria-label="'Aumentar quantidade de ' + item.name"
                :disabled="item.qty >= item.stock"
                @click="changeQty(item.id, 1)"
              >
                +
              </button>
            </span>
            <span class="pdv-row-remove">
              <button type="button" class="pdv-row-remove-btn" :aria-label="'Remover ' + item.name" @click="removeItem(item.id)">
                <i class="fas fa-times"></i>
              </button>
            </span>
          </div>
        </div>
      </section>

      <aside class="pdv-panel">
        <div class="pdv-panel-block" :class="{ 'is-attention': attention }">
          <h3>Forma de pagamento</h3>
          <div class="pdv-methods" id="pdv-methods">
            <button
              v-for="m in methods"
              :key="m.id"
              type="button"
              class="pdv-method"
              :class="{ 'is-selected': selectedMethod === m.id }"
              @click="selectedMethod = m.id"
            >
              {{ m.name }}
            </button>
            <p v-if="!methods.length" class="pdv-panel-note">
              Nenhuma forma ativa. Configure em
              <router-link to="/payments">Formas de pagamento</router-link>.
            </p>
          </div>
        </div>

        <div class="pdv-panel-block" :class="{ 'is-attention': attention }">
          <h3>Observações</h3>
          <input id="pdv_obs" v-model="obs" type="text" placeholder="Opcional..." autocomplete="off" />
        </div>

        <div class="pdv-panel-block" :class="{ 'is-attention': attention }">
          <h3>Atalhos</h3>
          <ul class="pdv-shortcuts">
            <li><kbd>F2</kbd> <span>Concluir venda</span></li>
            <li><kbd>N*</kbd> <span>Multiplicar (ex: 3*7890001)</span></li>
            <li><kbd>+ / −</kbd> <span>Alterar quantidade</span></li>
          </ul>
          <router-link class="pdv-panel-link" to="/payments">
            <i class="fas fa-credit-card"></i> Gerenciar formas de pagamento
          </router-link>
        </div>
      </aside>
    </main>

    <footer class="pdv-footer">
      <div class="pdv-footer-totals">
        <span class="pdv-footer-count" id="footer-count">{{ countLabel }}</span>
        <span class="pdv-footer-total" id="cart-total">{{ formatBRL(cartTotal) }}</span>
      </div>
      <button
        type="button"
        id="pdv-finish"
        class="btn btn-primary pdv-finish"
        :disabled="cartCount === 0 || finishing"
        @click="finishSale"
      >
        <i class="fas fa-check-circle"></i> {{ finishing ? 'Concluindo…' : 'Concluir venda' }}
        <kbd>F2</kbd>
      </button>
    </footer>
  </div>
</template>

<style scoped>
.pdv-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #ffffff;
  color: #111827;
}
.pdv-row-remove-btn {
  border: none;
  background: transparent;
  color: var(--text-muted);
  font-size: 15px;
  cursor: pointer;
  padding: 6px 10px;
  border-radius: var(--radius-sm);
}
.pdv-row-remove-btn:hover {
  color: var(--danger);
  background: var(--surface-hover);
}
</style>