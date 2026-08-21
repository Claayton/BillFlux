<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, maskMoney, moneyToDecimal } from '@/utils/format'

const props = defineProps({
  orderId: { type: Number, required: true },
})
const emit = defineEmits(['saved', 'close'])

const products = ref([])
const methods = ref([])
const cart = ref([])
const methodId = ref(null)
const obs = ref('')
const saving = ref(false)
const loading = ref(true)

const search = ref('')
const suggestions = ref([])
const highlighted = ref(-1)

const cartTotal = computed(() => cart.value.reduce((sum, i) => sum + i.price * i.qty, 0))

function formatBRL(value) {
  return brl(value)
}

function byProductId(productId) {
  return products.value.find((p) => p.id === productId)
}

function itemMaxQty(item) {
  const product = byProductId(item.product_id)
  return product ? product.stock + item.oldQty : item.qty
}

function incQty(item) {
  const max = itemMaxQty(item)
  if (item.qty < max) item.qty += 1
}

function decQty(item) {
  if (item.qty > 1) item.qty -= 1
}

function removeItem(item) {
  cart.value = cart.value.filter((i) => i !== item)
}

function addProduct(product) {
  const existing = cart.value.find((i) => i.product_id === product.id)
  if (existing) {
    incQty(existing)
  } else {
    cart.value.push({
      product_id: product.id,
      name: product.name,
      price: product.price,
      qty: 1,
      oldQty: 0,
    })
  }
  search.value = ''
  suggestions.value = []
}

function buildSuggestions(term) {
  const lower = term.toLowerCase()
  return products.value.filter(
    (p) => p.name.toLowerCase().includes(lower) || p.barcode.toLowerCase().includes(lower)
  )
}

function onSearchInput() {
  suggestions.value = buildSuggestions(search.value.trim())
  highlighted.value = suggestions.value.length ? 0 : -1
}

function onSearchKeydown(event) {
  if (event.key === 'Enter') {
    event.preventDefault()
    const raw = search.value.trim()
    const product =
      products.value.find((p) => p.name.toLowerCase() === raw.toLowerCase()) ||
      suggestions.value[highlighted.value]
    if (product) addProduct(product)
  } else if (event.key === 'ArrowDown' && suggestions.value.length) {
    event.preventDefault()
    highlighted.value = (highlighted.value + 1) % suggestions.value.length
  } else if (event.key === 'ArrowUp' && suggestions.value.length) {
    event.preventDefault()
    highlighted.value =
      (highlighted.value - 1 + suggestions.value.length) % suggestions.value.length
  }
}

async function load() {
  try {
    const [orderData, pdvData] = await Promise.all([
      api.get(`/sales/orders/${props.orderId}`),
      api.get('/pdv'),
    ])
    products.value = pdvData.products
    methods.value = pdvData.methods
    const order = orderData.order
    cart.value = order.items.map((item) => ({
      product_id: item.product_id,
      name: item.name,
      price: item.unit_price,
      qty: item.quantity,
      oldQty: item.quantity,
    }))
    methodId.value = order.method_id
    obs.value = order.obs || ''
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!cart.value.length) {
    ElMessage.warning('Adicione ao menos um item.')
    return
  }
  if (!methodId.value) {
    ElMessage.warning('Selecione a forma de pagamento.')
    return
  }
  saving.value = true
  try {
    await api.put(`/sales/orders/${props.orderId}`, {
      method_id: methodId.value,
      obs: obs.value,
      items: cart.value.map((i) => ({ product_id: i.product_id, quantity: i.qty })),
    })
    emit('saved')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="modal is-open">
    <div class="modal-content sale-edit-modal">
      <div class="modal-header">
        <h2>Editar venda #{{ orderId }}</h2>
        <button type="button" class="modal-close" aria-label="Fechar" @click="emit('close')">&times;</button>
      </div>

      <div v-if="loading" class="sale-edit-body muted">Carregando…</div>

      <div v-else class="sale-edit-body">
        <div class="sale-edit-block">
          <h3>Itens</h3>

          <div class="sale-edit-search">
            <i class="fas fa-search"></i>
            <input
              v-model="search"
              type="text"
              placeholder="Buscar produto para adicionar..."
              autocomplete="off"
              @input="onSearchInput"
              @keydown="onSearchKeydown"
            />
            <div v-if="suggestions.length" class="pdv-suggestions">
              <button
                v-for="(p, i) in suggestions"
                :key="p.id"
                type="button"
                class="pdv-suggestion"
                :class="{ 'is-highlighted': i === highlighted }"
                @mousedown.prevent="addProduct(p)"
              >
                <span class="pdv-suggestion-info">
                  <span class="pdv-suggestion-name">{{ p.name }}</span>
                </span>
                <span class="pdv-suggestion-price">{{ formatBRL(p.price) }}</span>
              </button>
            </div>
          </div>

          <div v-if="!cart.length" class="sale-edit-empty">
            Nenhum item no pedido. Adicione um produto acima.
          </div>

          <div v-for="item in cart" :key="item.product_id" class="sale-edit-item">
            <span class="sale-edit-item-name">{{ item.name }}</span>
            <span class="sale-edit-item-price">{{ brl(item.price) }} / un</span>
            <span class="sale-edit-item-qty">
              <button type="button" :disabled="item.qty <= 1" @click="decQty(item)">&minus;</button>
              <span>{{ item.qty }}</span>
              <button type="button" :disabled="item.qty >= itemMaxQty(item)" @click="incQty(item)">+</button>
            </span>
            <span class="sale-edit-item-subtotal">{{ brl(item.price * item.qty) }}</span>
            <button type="button" class="sale-edit-item-remove" aria-label="Remover" @click="removeItem(item)">
              <i class="fas fa-times"></i>
            </button>
          </div>
        </div>

        <div class="sale-edit-block">
          <h3>Forma de pagamento</h3>
          <div class="pdv-methods">
            <button
              v-for="m in methods"
              :key="m.id"
              type="button"
              class="pdv-method"
              :class="{ 'is-selected': methodId === m.id }"
              @click="methodId = m.id"
            >
              {{ m.name }}
            </button>
          </div>
        </div>

        <div class="sale-edit-block">
          <h3>Observações</h3>
          <input v-model="obs" type="text" placeholder="Opcional..." autocomplete="off" />
        </div>

        <div class="sale-edit-total">
          <span>Total</span>
          <strong>{{ brl(cartTotal) }}</strong>
        </div>
      </div>

      <div class="modal-footer">
        <button type="button" class="btn btn-ghost modal-cancel" @click="emit('close')">Cancelar</button>
        <button type="button" class="btn btn-primary" :disabled="saving || loading" @click="save">
          <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Salvar alterações' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px;
}
.sale-edit-modal {
  max-width: 640px;
}
.sale-edit-body {
  padding: 20px 24px;
  display: grid;
  gap: 20px;
}
.sale-edit-block h3 {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-secondary);
  margin-bottom: 10px;
}
.sale-edit-search {
  position: relative;
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.sale-edit-search > i {
  color: var(--text-muted);
}
.sale-edit-search input {
  flex: 1;
  padding: 9px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  background: var(--surface);
}
.sale-edit-empty {
  font-size: 13px;
  color: var(--text-muted);
  padding: 8px 0;
}
.sale-edit-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border);
}
.sale-edit-item-name {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  font-size: 14px;
}
.sale-edit-item-price {
  color: var(--text-secondary);
  font-size: 12px;
  white-space: nowrap;
}
.sale-edit-item-qty {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  white-space: nowrap;
}
.sale-edit-item-qty button {
  width: 28px;
  height: 28px;
  border: 1px solid var(--border);
  background: var(--surface);
  border-radius: var(--radius-sm);
  cursor: pointer;
  font-size: 15px;
  line-height: 1;
}
.sale-edit-item-qty button:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.sale-edit-item-qty span {
  min-width: 20px;
  text-align: center;
  font-weight: 600;
}
.sale-edit-item-subtotal {
  min-width: 90px;
  text-align: right;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.sale-edit-item-remove {
  border: none;
  background: transparent;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px;
}
.sale-edit-item-remove:hover {
  color: var(--danger);
}
.sale-edit-total {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 18px;
  font-weight: 700;
}
.sale-edit-modal .modal-footer {
  margin-top: 0;
  padding: 16px 24px 20px;
}
</style>