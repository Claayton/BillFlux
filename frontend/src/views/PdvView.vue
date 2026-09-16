<script setup>
import { ref, computed, nextTick, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { maskMoney, moneyToDecimal } from '@/utils/format'
import { normalizeForSearch } from '@/utils/normalize'
import { paymentIcon, paymentColor } from '@/utils/payment'
import SaleReceiptModal from '@/views/SaleReceiptModal.vue'

const products = ref([])
const methods = ref([])
const customers = ref([])
const selectedCustomer = ref(null)
const customerSearch = ref('')
const showCustomerDropdown = ref(false)
const search = ref('')
const suggestions = ref([])
const highlighted = ref(-1)
const finishing = ref(false)
const receiptOrder = ref(null)
const caixaOpen = ref(false)

const checkoutOpen = ref(false)
const payAmounts = ref({})
const payInputs = ref([])

const discountOpen = ref(false)
const discountType = ref('percent')
const discountInput = ref('')
const discount = ref(null)

const searchInput = ref(null)
const cart = ref(new Map())

const cartItems = computed(() => Array.from(cart.value.values()))
const cartCount = computed(() => cartItems.value.reduce((sum, item) => sum + item.qty, 0))
const cartTotal = computed(() => Math.round(cartItems.value.reduce((sum, item) => sum + item.price * item.qty, 0) * 100) / 100)
const countLabel = computed(() => cartCount.value + (cartCount.value === 1 ? ' item' : ' itens'))
const cartTotalAfter = computed(() => Math.round(Math.max(0, cartTotal.value - (discount.value || 0)) * 100) / 100)

// Pagamentos preenchidos no fechamento (valor > 0).
const paymentsEntered = computed(() =>
  methods.value
    .map((m) => ({ method_id: m.id, amount: moneyToDecimal(payAmounts.value[m.id]) || 0 }))
    .filter((p) => p.amount > 0)
)
const paymentsTotal = computed(() =>
  Math.round(paymentsEntered.value.reduce((sum, p) => sum + p.amount, 0) * 100) / 100
)
const paymentDiff = computed(
  () => Math.round((paymentsTotal.value - cartTotalAfter.value) * 100) / 100
)
const canConfirm = computed(() => paymentsTotal.value >= cartTotalAfter.value && cartTotalAfter.value >= 0)

// Valor que "carrega" junto com o foco: pré-preenche o primeiro método e,
// enquanto não for digitado por cima, a seta move esse valor entre formas.
const defaultPayAmount = computed(() => maskMoney(String(Math.round(cartTotalAfter.value * 100))))

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
    const [pdvData, caixaData] = await Promise.all([
      api.get('/pdv'),
      api.get('/caixa').catch(() => ({ open: null })),
    ])
    products.value = pdvData.products
    methods.value = pdvData.methods
    customers.value = pdvData.customers || []
    caixaOpen.value = !!caixaData.open
    searchInput.value?.focus()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function byId(productId) {
  return products.value.find((p) => p.id === productId)
}

function findUnit(product, unitId) {
  if (!product || !product.units) return null
  return product.units.find((u) => u.id === unitId) || null
}

function defaultUnit(product) {
  if (!product || !product.units || !product.units.length) {
    return { id: 0, name: 'Unidade', factor: 1, price: product?.price || 0, is_default: true }
  }
  return product.units.find((u) => u.is_default) || product.units[0]
}

function cartKey(productId, unitId) {
  return productId + '_' + (unitId || 0)
}

// Estoque pode ficar negativo: sem bloqueio por estoque.
function addToCart(product, unit) {
  if (!product || !unit) return
  const key = cartKey(product.id, unit.id)
  const existing = cart.value.get(key)
  if (existing) {
    existing.qty += 1
  } else {
    cart.value.set(key, {
      id: product.id,
      key,
      name: product.name,
      unitName: unit.name,
      price: unit.price || product.price,
      stock: product.stock,
      qty: 1,
      factor: unit.factor,
      unitId: unit.id,
      hasMultipleUnits: (product.units || []).length > 1,
    })
  }
}

function setQty(key, quantity) {
  const item = cart.value.get(key)
  if (!item) return
  item.qty = Math.max(1, quantity)
}

function changeQty(key, delta) {
  const item = cart.value.get(key)
  if (!item) return
  const next = item.qty + delta
  if (next < 1) return
  item.qty = next
}

function removeItem(key) {
  cart.value.delete(key)
  if (cart.value.size === 0) discount.value = null
}

// ---------- Busca / sugestões ----------
function buildSuggestions(term) {
  const lower = normalizeForSearch(term)
  const results = []
  for (const p of products.value) {
    if (normalizeForSearch(p.name).includes(lower) || normalizeForSearch(p.barcode || '').includes(lower)) {
      if (p.units && p.units.length > 1) {
        for (const u of p.units) {
          results.push({ ...p, _unit: u, _suggestionKey: p.id + '_' + u.id })
        }
      } else {
        const u = defaultUnit(p)
        results.push({ ...p, _unit: u, _suggestionKey: p.id + '_' + u.id })
      }
    }
  }
  return results
}

function matchBarcode(raw) {
  const term = raw.trim().toLowerCase()
  for (const p of products.value) {
    if (p.barcode && p.barcode.toLowerCase() === term) {
      return { product: p, unit: defaultUnit(p) }
    }
    if (p.units) {
      for (const u of p.units) {
        if (u.barcode && u.barcode.toLowerCase() === term) {
          return { product: p, unit: u }
        }
      }
    }
  }
  return null
}

function matchName(raw) {
  const term = normalizeForSearch(raw)
  for (const p of products.value) {
    if (normalizeForSearch(p.name) === term) {
      return { product: p, unit: defaultUnit(p) }
    }
  }
  return null
}

// Adiciona um produto ao carrinho (estoque pode ficar negativo, sem bloqueio).
function tryAdd(product, unit) {
  if (!product) return false
  addToCart(product, unit || defaultUnit(product))
  return true
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

function addFromSuggestion(item) {
  if (tryAdd(item, item._unit)) clearSearch()
}

function handleEnter() {
  const raw = search.value.trim()
  if (!raw) return

  const multiply = raw.match(/^(\d+)\s*\*\s*(.+)$/)
  if (multiply) {
    const n = parseInt(multiply[1], 10)
    const match = matchBarcode(multiply[2].trim()) || matchName(multiply[2].trim())
    if (match) {
      for (let i = 0; i < n; i++) {
        addToCart(match.product, match.unit)
      }
      clearSearch()
      return
    }
  }

  const match = matchBarcode(raw)
  if (match) {
    addToCart(match.product, match.unit)
    clearSearch()
    return
  }

  if (highlighted.value >= 0 && suggestions.value[highlighted.value]) {
    const item = suggestions.value[highlighted.value]
    if (tryAdd(item, item._unit)) clearSearch()
    return
  }

  const exactMatch = matchName(raw)
  if (exactMatch) {
    addToCart(exactMatch.product, exactMatch.unit)
    clearSearch()
    return
  }

  if (suggestions.value.length === 1) {
    const item = suggestions.value[0]
    if (tryAdd(item, item._unit)) clearSearch()
    return
  }

  ElMessage.warning('Produto não encontrado.')
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

// ---------- Cliente ----------
const filteredCustomers = computed(() => {
  const q = normalizeForSearch(customerSearch.value)
  if (!q) return customers.value
  return customers.value.filter((c) =>
    normalizeForSearch(c.name).includes(q) ||
    normalizeForSearch(c.cpf_cnpj || '').includes(q)
  )
})

function selectCustomer(customer) {
  selectedCustomer.value = customer
  customerSearch.value = customer.name
  showCustomerDropdown.value = false
}

function clearCustomer() {
  selectedCustomer.value = null
  customerSearch.value = ''
}

function onCustomerInput(event) {
  customerSearch.value = event.target.value
  showCustomerDropdown.value = true
  if (!event.target.value) {
    selectedCustomer.value = null
  }
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
  if (!caixaOpen.value) {
    ElMessage.warning('Nenhum caixa aberto. Abra o caixa antes de registrar vendas.')
    return
  }
  if (cart.value.size === 0) return
  const amounts = {}
  methods.value.forEach((m) => {
    amounts[m.id] = ''
  })
  if (cartTotalAfter.value > 0 && methods.value.length) {
    // Dinheiro (primeira forma) já vem com o total, selecionado
    amounts[methods.value[0].id] = defaultPayAmount.value
  }
  payAmounts.value = amounts
  payInputs.value = []
  checkoutOpen.value = true
  nextTick(() => focusPayInput(0))
}

function focusPayInput(index) {
  const el = payInputs.value[index]
  if (!el) return
  el.focus()
  // se o campo ainda guarda o total padrão, deixa selecionado pra digitar
  // por cima (ex: nota de 10,00 na compra de 5,00)
  if (payAmounts.value[methods.value[index]?.id] === defaultPayAmount.value) {
    el.select()
  }
}

function onPayInput(event, methodId) {
  payAmounts.value[methodId] = maskMoney(event.target.value)
}

// Seta para baixo/cima navega entre as formas; se o campo ainda guarda o
// total padrão, o valor "pula" para a próxima forma.
function movePayAmount(fromIndex, toIndex) {
  const from = methods.value[fromIndex]
  const to = methods.value[toIndex]
  if (!from || !to) return
  if (payAmounts.value[from.id] === defaultPayAmount.value) {
    payAmounts.value[from.id] = ''
    payAmounts.value[to.id] = defaultPayAmount.value
  }
}

function onPayKeydown(event, index) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    if (index + 1 < methods.value.length) {
      movePayAmount(index, index + 1)
      focusPayInput(index + 1)
    }
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    if (index > 0) {
      movePayAmount(index, index - 1)
      focusPayInput(index - 1)
    }
  } else if (event.key === 'Enter') {
    event.preventDefault()
    confirmCheckout()
  }
}

async function confirmCheckout() {
  if (!methods.value.length) {
    ElMessage.warning('Nenhuma forma de pagamento ativa.')
    return
  }
  const items = cartItems.value.map((item) => ({
    product_id: item.id,
    quantity: item.qty,
    unit_id: item.unitId || null,
  }))
  const payload = {
    items,
    discount: discount.value || 0,
  }
  if (selectedCustomer.value) {
    payload.customer_id = selectedCustomer.value.id
  }
  if (cartTotalAfter.value <= 0) {
    // venda de valor zero: fecha na primeira forma sem valores
    payload.method_id = methods.value[0].id
  } else {
    if (!paymentsEntered.value.length) {
      ElMessage.warning('Informe o valor recebido.')
      focusPayInput(0)
      return
    }
    if (!canConfirm.value) {
      ElMessage.warning('Falta ' + formatBRL(Math.abs(paymentDiff.value)) + ' para fechar o valor.')
      return
    }
    payload.payments = paymentsEntered.value.map((p) => ({
      method_id: p.method_id,
      amount: p.amount.toFixed(2),
    }))
  }
  finishing.value = true
  try {
    const data = await api.post('/pdv/complete', payload)
    cart.value.clear()
    discount.value = null
    checkoutOpen.value = false
    receiptOrder.value = { id: data.order.order_id, kind: 'pdv' }
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    finishing.value = false
  }
}

function closeReceipt() {
  receiptOrder.value = null
  searchInput.value?.focus()
}

function onGlobalKeydown(event) {
  if (receiptOrder.value) return // recibo aberto: F2 imprime lá dentro
  if (event.key === 'F2') {
    event.preventDefault()
    if (checkoutOpen.value) {
      confirmCheckout()
    } else {
      finishSale()
    }
  } else if (event.key === 'F3' && !checkoutOpen.value) {
    event.preventDefault()
    openDiscount()
  } else if (event.key === 'F9') {
    event.preventDefault()
    ElMessage.info('Entrega disponível em breve.')
  } else if (event.key === 'Escape') {
    if (checkoutOpen.value) checkoutOpen.value = false
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

    <div v-if="!caixaOpen" class="pdv-caixa-warning">
      <i class="fas fa-exclamation-triangle"></i>
      <span>Caixa fechado — abra o caixa para iniciar as vendas.</span>
      <router-link to="/caixa" class="btn btn-sm btn-warning">Abrir caixa</router-link>
    </div>

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
              v-for="(item, i) in suggestions"
              :key="item._suggestionKey"
              type="button"
              class="pdv-suggestion"
              :class="{ 'is-highlighted': i === highlighted }"
              @mousedown.prevent="addFromSuggestion(item)"
            >
              <span class="pdv-suggestion-info">
                <span class="pdv-suggestion-name">{{ item.name }} <small v-if="(item.units || []).length > 1" class="pdv-unit-tag">{{ item._unit.name }}</small></span>
                <span class="pdv-suggestion-sub">{{ item.barcode ? 'Cód.: ' + item.barcode : (item._unit?.barcode ? 'Cód.: ' + item._unit.barcode : 'Sem código de barras') }}</span>
              </span>
              <span class="pdv-suggestion-price">{{ formatBRL(item._unit?.price || item.price) }}</span>
              <span class="pdv-suggestion-stock" :class="{ 'is-out': item.stock <= 0 }">
                {{ item.stock <= 0 ? 'Esgotado' : item.stock + ' un' }}
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

          <div v-for="item in cartItems" :key="item.key" class="pdv-row">
            <span class="pdv-row-num">#{{ item.id }}</span>
            <span class="pdv-row-qty">{{ item.qty }}</span>
            <span class="pdv-row-info">
              <span class="pdv-row-name">{{ item.name }} <small v-if="item.hasMultipleUnits" class="pdv-unit-tag">{{ item.unitName }}</small></span>
              <span class="pdv-row-sub">{{ formatBRL(item.price) }} / {{ item.unitName === 'Unidade' ? 'un' : item.unitName.toLowerCase() }}</span>
            </span>
            <span class="pdv-row-price">{{ formatBRL(item.price * item.qty) }}</span>
            <span class="pdv-row-qty-ctrl">
              <button
                type="button"
                :aria-label="'Diminuir quantidade de ' + item.name"
                :disabled="item.qty <= 1"
                @click="changeQty(item.key, -1)"
              >
                &minus;
              </button>
              <button
                type="button"
                :aria-label="'Aumentar quantidade de ' + item.name"
                @click="changeQty(item.key, 1)"
              >
                +
              </button>
            </span>
            <span class="pdv-row-remove">
              <button type="button" class="pdv-row-remove-btn" :aria-label="'Remover ' + item.name" @click="removeItem(item.key)">
                <i class="fas fa-times"></i>
              </button>
            </span>
          </div>
        </div>

        <div class="pdv-customer-row">
          <div class="pdv-customer-search">
            <i class="fas fa-user"></i>
            <input
              :value="customerSearch"
              type="text"
              placeholder="Buscar cliente (nome ou CPF/CNPJ)…"
              @input="onCustomerInput"
              @focus="showCustomerDropdown = true"
              @click.outside="showCustomerDropdown = false"
            />
            <button
              v-if="selectedCustomer"
              type="button"
              class="pdv-customer-clear"
              @click="clearCustomer"
              title="Limpar cliente"
            >
              <i class="fas fa-times"></i>
            </button>
          </div>
          <div v-if="showCustomerDropdown && filteredCustomers.length" class="pdv-customer-dropdown">
            <div
              v-for="c in filteredCustomers"
              :key="c.id"
              class="pdv-customer-option"
              @click="selectCustomer(c)"
            >
              <span class="pdv-customer-name">{{ c.name }}</span>
              <span v-if="c.cpf_cnpj" class="pdv-customer-doc">{{ c.cpf_cnpj }}</span>
            </div>
          </div>
          <span v-if="selectedCustomer" class="pdv-customer-badge">
            <i class="fas fa-user-check"></i> {{ selectedCustomer.name }}
          </span>
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
          <div class="pdv-checkout-total">
            <span>Total</span>
            <strong>{{ formatBRL(cartTotalAfter) }}</strong>
          </div>

          <div class="pdv-paylist" v-if="methods.length">
            <div v-for="(m, i) in methods" :key="m.id" class="pdv-payrow">
              <span class="pdv-payicon" :class="paymentColor(m.name)">
                <i :class="paymentIcon(m.name)"></i>
              </span>
              <span class="pdv-payname">{{ m.name }}</span>
              <div class="pdv-payfield">
                <span>R$</span>
                <input
                  :ref="(el) => (payInputs[i] = el)"
                  :value="payAmounts[m.id]"
                  type="text"
                  inputmode="numeric"
                  :aria-label="'Valor em ' + m.name"
                  placeholder="0,00"
                  autocomplete="off"
                  @input="onPayInput($event, m.id)"
                  @keydown="onPayKeydown($event, i)"
                />
              </div>
            </div>
            <div class="pdv-paystatus" v-if="paymentsEntered.length">
              <span v-if="paymentDiff > 0" class="is-troco">Troco {{ formatBRL(paymentDiff) }}</span>
              <span v-else-if="paymentDiff < 0" class="is-missing">
                Falta {{ formatBRL(Math.abs(paymentDiff)) }}
              </span>
              <span v-else class="is-ok"><i class="fas fa-check"></i> Valor fechado</span>
            </div>
            <p class="pdv-payhint">
              <i class="fas fa-arrow-down"></i> Seta para baixo pula para a próxima forma.
            </p>
          </div>
          <p v-if="!methods.length" class="pdv-panel-note">
            Nenhuma forma ativa. Configure em
            <router-link to="/payments">Formas de pagamento</router-link>.
          </p>
        </div>
        <div class="modal-footer pdv-checkout-footer">
          <button type="button" class="btn btn-ghost modal-cancel" @click="checkoutOpen = false">Cancelar <kbd>Esc</kbd></button>
          <button
            type="button"
            class="btn btn-primary"
            :disabled="finishing || !canConfirm"
            @click="confirmCheckout"
          >
            <i class="fas fa-check-circle"></i> {{ finishing ? 'Concluindo…' : 'Confirmar venda' }}
            <kbd>F2</kbd>
          </button>
        </div>
      </div>
    </div>

    <!-- Recibo da venda concluída -->
    <SaleReceiptModal
      v-if="receiptOrder"
      :sale="receiptOrder"
      @close="closeReceipt"
    />
  </div>
</template>

<style scoped>
.pdv-caixa-warning {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: color-mix(in srgb, #f59e0b 12%, white);
  border-bottom: 1px solid color-mix(in srgb, #f59e0b 30%, transparent);
  color: #92400e;
  font-size: 14px;
  font-weight: 600;
  flex-shrink: 0;
}
.pdv-caixa-warning i {
  font-size: 16px;
}
.pdv-caixa-warning .btn-warning {
  margin-left: auto;
  padding: 5px 14px;
  font-size: 13px;
  background: #f59e0b;
  color: #fff;
  border: none;
  border-radius: 6px;
  text-decoration: none;
  white-space: nowrap;
}
.pdv-caixa-warning .btn-warning:hover {
  background: #d97706;
}
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
.pdv-checkout-footer {
  display: flex;
  justify-content: flex-end;
  align-items: center;
  gap: 10px;
}
.pdv-checkout-total {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 4px 0 16px;
}
.pdv-checkout-total span {
  font-size: 13px;
  color: var(--text-muted, #9ca3af);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}
.pdv-checkout-total strong {
  font-size: 40px;
  line-height: 1.1;
  font-weight: 800;
  letter-spacing: -0.5px;
  color: #111827;
  font-variant-numeric: tabular-nums;
}
.pdv-paylist {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.pdv-payrow {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 7px 12px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: var(--radius-sm, 8px);
  background: var(--surface, #ffffff);
}
.pdv-payicon {
  width: 32px;
  height: 32px;
  border-radius: var(--radius-sm, 8px);
  display: grid;
  place-items: center;
  font-size: 14px;
  background: color-mix(in srgb, currentColor 12%, transparent);
  flex-shrink: 0;
}
.pdv-payname {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
}
.pdv-payfield {
  display: flex;
  align-items: center;
  gap: 6px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: var(--radius-sm, 8px);
  padding: 0 10px;
  height: 36px;
  background: #ffffff;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}
.pdv-payfield span {
  color: var(--text-muted, #9ca3af);
  font-size: 13px;
}
.pdv-payfield input {
  border: none;
  outline: none;
  width: 96px;
  text-align: right;
  font-size: 14px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  background: transparent;
}
.pdv-payfield:focus-within {
  border-color: var(--primary);
  box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary) 15%, transparent);
}
.pdv-payfield input:focus {
  box-shadow: none;
  outline: none;
}
.pdv-paystatus {
  display: flex;
  justify-content: flex-end;
  font-size: 13px;
  font-weight: 600;
  padding: 2px 24px 0;
}
.pdv-paystatus .is-troco {
  color: var(--primary, #4f46e5);
}
.pdv-paystatus .is-missing {
  color: var(--danger, #dc2626);
}
.pdv-paystatus .is-ok {
  color: var(--success, #16a34a);
}
.pdv-paystatus .is-ok i {
  margin-right: 4px;
}
.pdv-payhint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  font-size: 12px;
  color: var(--text-muted, #9ca3af);
}

/* Customer selector */
.pdv-customer-row {
  position: relative;
  padding: 8px 16px;
}
.pdv-customer-search {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface, #fff);
  border: 1px solid var(--border, #d1d5db);
  border-radius: 8px;
  padding: 6px 10px;
}
.pdv-customer-search i {
  color: var(--text-muted, #999);
  font-size: 13px;
}
.pdv-customer-search input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 13px;
  background: transparent;
}
.pdv-customer-clear {
  background: none;
  border: none;
  color: var(--text-muted, #999);
  cursor: pointer;
  padding: 2px;
}
.pdv-customer-clear:hover {
  color: var(--danger, #dc2626);
}
.pdv-customer-dropdown {
  position: absolute;
  left: 16px;
  right: 16px;
  background: var(--surface, #fff);
  border: 1px solid var(--border, #d1d5db);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.12);
  max-height: 160px;
  overflow-y: auto;
  z-index: 20;
}
.pdv-customer-option {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  cursor: pointer;
  font-size: 13px;
}
.pdv-customer-option:hover {
  background: var(--surface-hover, #f3f4f6);
}
.pdv-customer-name {
  font-weight: 600;
}
.pdv-customer-doc {
  color: var(--text-muted, #999);
  font-size: 12px;
}
.pdv-customer-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  margin-top: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--primary, #2563eb);
  background: color-mix(in srgb, var(--primary, #2563eb) 10%, transparent);
  padding: 3px 8px;
  border-radius: 4px;
}
.pdv-unit-tag {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  color: var(--primary, #4f46e5);
  background: color-mix(in srgb, var(--primary, #4f46e5) 10%, transparent);
  padding: 1px 5px;
  border-radius: 3px;
  margin-left: 4px;
  vertical-align: middle;
}
</style>