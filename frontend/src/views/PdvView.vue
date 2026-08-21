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
const finishing = ref(false)

const checkoutOpen = ref(false)
const checkoutMethod = ref(null)
const checkoutObs = ref('')

const discountOpen = ref(false)
const discountType = ref('percent')
const discountInput = ref('')
const discount = ref(null)

const searchInput = ref(null)
const cart = ref(new Map())

const cartItems = computed(() => Array.from(cart.value.values()))
const cartCount = computed(() => cartItems.value.reduce((sum, item) => sum + item.qty, 0))
const cartTotal = computed(() => cartItems.value.reduce((sum, item) => sum + item.price * item.qty, 0))
const countLabel = computed(() => cartCount.value + (cartCount.value === 1 ? ' item' : ' itens'))
const cartTotalAfter = computed(() => Math.max(0, cartTotal.value - (discount.value || 0)))

const discountPreview = computed(() => {
  if (cartTotal.value <= 0) return 0
  const raw = parseFloat(
    (discountInput.value || '').replace(/[^\d.,]/g, '').replace(',', '.')
  )
  if (Number.isNaN(raw) || raw <= 0) return 0
  const value =
    discountType.value === 'percent' ? (cartTotal.value * raw) / 100 : raw
  return Math.min(Math.max(0, value), cartTotal.value)
})

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
  if (cart.value.size === 0) discount.value = null
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

// ---------- Desconto (F3) ----------
function openDiscount() {
  if (cart.value.size === 0) return
  discountInput.value = discount.value ? String(discount.value) : ''
  discountType.value = discount.value ? 'value' : 'percent'
  discountOpen.value = true
}

function applyDiscount() {
  discount.value = Math.round(discountPreview.value * 100) / 100 || null
  discountOpen.value = false
}

function clearDiscount() {
  discount.value = null
  discountInput.value = ''
  discountOpen.value = false
}

// ---------- Finalizar venda (F2) ----------
function finishSale() {
  if (cart.value.size === 0) return
  checkoutMethod.value = null
  checkoutObs.value = ''
  checkoutOpen.value = true
}

async function confirmCheckout() {
  if (!checkoutMethod.value) {
    ElMessage.warning('Selecione a forma de pagamento.')
    return
  }
  finishing.value = true
  try {
    const items = cartItems.value.map((item) => ({
      product_id: item.id,
      quantity: item.qty,
    }))
    const data = await api.post('/pdv/complete', {
      method_id: checkoutMethod.value,
      obs: checkoutObs.value || null,
      items,
      discount: discount.value || 0,
    })
    cart.value.clear()
    discount.value = null
    checkoutOpen.value = false
    router.push(`/pdv/recibo/${data.order.order_id}`)
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    finishing.value = false
  }
}

function onGlobalKeydown(event) {
  if (event.key === 'F2') {
    event.preventDefault()
    finishSale()
  } else if (event.key === 'F3') {
    event.preventDefault()
    openDiscount()
  } else if (event.key === 'F9') {
    event.preventDefault()
    ElMessage.info('Entrega disponível em breve.')
  }
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

      <span class="pdv-topbar-spacer"></span>

      <router-link class="pdv-exit" to="/home" title="Sair do PDV" aria-label="Sair do PDV">
        <i class="fas fa-arrow-left"></i>
      </router-link>
    </header>

    <main class="pdv-main">
      <section class="pdv-items" id="pdv-items">
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

        <div class="pdv-footer-inline">
          <div class="pdv-footer-left">
            <button
              type="button"
              class="btn btn-ghost btn-sm pdv-discount-btn"
              :disabled="cartCount === 0"
              @click="openDiscount"
            >
              <i class="fas fa-tags"></i> Desconto <kbd>F3</kbd>
            </button>
            <div class="pdv-footer-totals">
              <span class="pdv-footer-count" id="footer-count">{{ countLabel }}</span>
              <span class="pdv-footer-subtotal">Subtotal {{ formatBRL(cartTotal) }}</span>
              <span v-if="discount" class="pdv-footer-discount">
                Desconto &minus;{{ formatBRL(discount) }}
              </span>
              <span class="pdv-footer-total" id="cart-total">{{ formatBRL(cartTotalAfter) }}</span>
            </div>
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
        </div>
      </section>

      <aside class="pdv-panel">
        <div class="pdv-panel-block">
          <h3>Atalhos</h3>
          <ul class="pdv-shortcuts">
            <li><kbd>F2</kbd> <span>Concluir venda</span></li>
            <li><kbd>F3</kbd> <span>Desconto</span></li>
            <li><kbd>F9</kbd> <span>Entrega</span></li>
            <li><kbd>N*</kbd> <span>Multiplicar (ex: 3*7890001)</span></li>
            <li><kbd>+ / −</kbd> <span>Alterar quantidade</span></li>
          </ul>
        </div>
      </aside>
    </main>

    <!-- Desconto -->
    <div class="modal" :class="{ 'is-open': discountOpen }">
      <div class="modal-content modal-content-sm">
        <div class="modal-header">
          <h2>Desconto</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="discountOpen = false">&times;</button>
        </div>
        <div class="pdv-modal-body">
          <div class="pdv-discount-type" role="group" aria-label="Tipo de desconto">
            <button
              type="button"
              :class="{ 'is-active': discountType === 'percent' }"
              @click="discountType = 'percent'"
            >
              %
            </button>
            <button
              type="button"
              :class="{ 'is-active': discountType === 'value' }"
              @click="discountType = 'value'"
            >
              R$
            </button>
          </div>
          <div class="form-field">
            <label :for="'discount_input'">Desconto {{ discountType === 'percent' ? '(%)' : '(R$)' }}</label>
            <input
              id="discount_input"
              v-model="discountInput"
              type="text"
              :placeholder="discountType === 'percent' ? 'Ex: 10' : 'Ex: 5,00'"
              inputmode="decimal"
              autofocus
            />
          </div>
          <div class="pdv-discount-summary">
            <div class="pdv-discount-line">
              <span>Subtotal</span>
              <strong>{{ formatBRL(cartTotal) }}</strong>
            </div>
            <div class="pdv-discount-line" v-if="discountPreview">
              <span>Desconto</span>
              <strong class="is-negative">&minus;{{ formatBRL(discountPreview) }}</strong>
            </div>
            <div class="pdv-discount-line is-total">
              <span>Total</span>
              <strong>{{ formatBRL(cartTotal - discountPreview) }}</strong>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button v-if="discount" type="button" class="btn btn-ghost" @click="clearDiscount">
            <i class="fas fa-times"></i> Remover
          </button>
          <button type="button" class="btn btn-ghost modal-cancel" @click="discountOpen = false">Cancelar</button>
          <button type="button" class="btn btn-primary" :disabled="discountPreview <= 0" @click="applyDiscount">
            <i class="fas fa-check"></i> Aplicar
          </button>
        </div>
      </div>
    </div>

    <!-- Finalizar venda -->
    <div class="modal" :class="{ 'is-open': checkoutOpen }">
      <div class="modal-content pdv-checkout-modal">
        <div class="modal-header">
          <h2>Finalizar venda</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="checkoutOpen = false">&times;</button>
        </div>
        <div class="pdv-modal-body">
          <div class="pdv-checkout-summary">
            <div class="pdv-discount-line">
              <span>Itens</span>
              <strong>{{ countLabel }}</strong>
            </div>
            <div class="pdv-discount-line">
              <span>Subtotal</span>
              <strong>{{ formatBRL(cartTotal) }}</strong>
            </div>
            <div class="pdv-discount-line" v-if="discount">
              <span>Desconto</span>
              <strong class="is-negative">&minus;{{ formatBRL(discount) }}</strong>
            </div>
            <div class="pdv-discount-line is-total">
              <span>Total</span>
              <strong>{{ formatBRL(cartTotalAfter) }}</strong>
            </div>
          </div>

          <div class="pdv-checkout-block">
            <h3>Forma de pagamento</h3>
            <div class="pdv-methods">
              <button
                v-for="m in methods"
                :key="m.id"
                type="button"
                class="pdv-method"
                :class="{ 'is-selected': checkoutMethod === m.id }"
                @click="checkoutMethod = m.id"
              >
                {{ m.name }}
              </button>
              <p v-if="!methods.length" class="pdv-panel-note">
                Nenhuma forma ativa. Configure em
                <router-link to="/payments">Formas de pagamento</router-link>.
              </p>
            </div>
          </div>

          <div class="pdv-checkout-block">
            <h3>Observações</h3>
            <input v-model="checkoutObs" type="text" placeholder="Opcional..." autocomplete="off" />
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-ghost modal-cancel" @click="checkoutOpen = false">Cancelar</button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="finishing || !checkoutMethod"
            @click="confirmCheckout"
          >
            <i class="fas fa-check-circle"></i> {{ finishing ? 'Concluindo…' : 'Confirmar venda' }}
          </button>
        </div>
      </div>
    </div>
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
.modal-footer {
  margin-top: 0;
  padding: 16px 24px 20px;
}
</style>