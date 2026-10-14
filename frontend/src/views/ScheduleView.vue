<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, brdate, maskMoney, toNumber } from '@/utils/format'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ProductSearch from '@/components/ProductSearch.vue'

const tab = ref('orders')

// ---------- Pedidos agendados (encargos a clientes) ----------
const orders = ref([])
const loading = ref(false)
const saving = ref(false)
const customers = ref([])
const allProducts = ref([])
const filters = ref({ date: '', status: '', q: '' })

const showModal = ref(false)
const form = ref(emptyForm())
const items = ref([])
const deleteTarget = ref(null)

const STATUSES = [
  { key: 'pendente', label: 'Pendente', cls: 'is-low' },
  { key: 'confirmado', label: 'Confirmado', cls: 'is-info' },
  { key: 'listo', label: 'Pronto', cls: 'is-ok' },
  { key: 'entregado', label: 'Entregue', cls: 'is-off' },
  { key: 'cancelado', label: 'Cancelado', cls: 'is-danger' },
]
const statusLabel = (k) => (STATUSES.find((s) => s.key === k) || {}).label || k
const statusClass = (k) => (STATUSES.find((s) => s.key === k) || {}).cls || ''

function todayISO() {
  return new Date().toISOString().slice(0, 10)
}
function emptyForm() {
  return {
    id: null,
    customer_id: null,
    customer_name: '',
    order_date: todayISO(),
    order_time: '',
    status: 'pendente',
    obs: '',
  }
}

function defMask(value) {
  const n = toNumber(value)
  if (Number.isNaN(n)) return ''
  return maskMoney(String(Math.round(n * 100)))
}
function moneyInput(target, key, event) {
  target[key] = maskMoney(event.target.value)
}
function itemNames(order) {
  const names = (order.items || []).map((i) => `${i.quantity}x ${i.name}`)
  return names.join(', ')
}
function itemsTotal(order) {
  return (order.items || []).reduce(
    (s, i) => s + (Number(i.quantity) || 0) * (toNumber(i.unit_price) || 0),
    0
  )
}

async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (filters.value.date) params.set('date', filters.value.date)
    if (filters.value.status) params.set('status', filters.value.status)
    if (filters.value.q) params.set('q', filters.value.q)
    const query = params.toString()
    const data = await api.get('/scheduled-orders' + (query ? `?${query}` : ''))
    orders.value = data.orders || []
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function loadSupport() {
  try {
    customers.value = (await api.get('/customers')).customers || []
  } catch { /* ignore */ }
  try {
    allProducts.value = (await api.get('/products')).products || []
  } catch { /* ignore */ }
}

function openNewOrder() {
  form.value = emptyForm()
  items.value = []
  showModal.value = true
}

async function openEditOrder(order) {
  try {
    const data = await api.get(`/scheduled-orders/${order.id}`)
    const o = data.order
    form.value = {
      id: o.id,
      customer_id: o.customer_id,
      customer_name: o.customer_name || '',
      order_date: o.order_date || todayISO(),
      order_time: o.order_time || '',
      status: o.status,
      obs: o.obs || '',
    }
    items.value = (o.items || []).map((i) => ({ ...i, unit_price: defMask(i.unit_price) }))
    showModal.value = true
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function addProduct(product) {
  items.value.push({
    product_id: product.id,
    name: product.name,
    quantity: 1,
    unit_price: defMask(product.price),
  })
}
function removeItem(idx) {
  items.value.splice(idx, 1)
}
function calcTotal() {
  return items.value.reduce(
    (s, i) => s + (parseInt(i.quantity) || 0) * (toNumber(i.unit_price) || 0),
    0
  )
}
function onCustomerInput() {
  const name = form.value.customer_name.trim().toLowerCase()
  const found = customers.value.find((c) => c.name.trim().toLowerCase() === name)
  form.value.customer_id = found ? found.id : null
}

async function saveOrder() {
  if (!form.value.customer_name.trim()) {
    ElMessage.warning('Informe o cliente.')
    return
  }
  saving.value = true
  try {
    const payload = {
      customer_id: form.value.customer_id,
      customer_name: form.value.customer_name,
      order_date: form.value.order_date || null,
      order_time: form.value.order_time || null,
      status: form.value.status,
      obs: form.value.obs,
      items: items.value.map((i) => ({
        product_id: i.product_id,
        name: i.name,
        quantity: parseInt(i.quantity) || 0,
        unit_price: i.unit_price,
      })),
    }
    if (form.value.id) {
      await api.put(`/scheduled-orders/${form.value.id}`, payload)
      ElMessage.success('Pedido atualizado!')
    } else {
      await api.post('/scheduled-orders', payload)
      ElMessage.success('Pedido criado!')
    }
    showModal.value = false
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function changeStatus(order, status) {
  try {
    await api.post(`/scheduled-orders/${order.id}/status`, { status })
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function askDelete(order) {
  deleteTarget.value = order
}
async function confirmDelete() {
  const order = deleteTarget.value
  deleteTarget.value = null
  if (!order) return
  try {
    await api.del(`/scheduled-orders/${order.id}`)
    ElMessage.success('Pedido excluído.')
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

// ---------- Sugestões de compra (reposição a fornecedores) ----------
const week = ref([])
const selectedDay = ref(null)

const WEEKDAYS_FULL = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado']
const MONTHS_FULL = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

function cap(text) {
  return text.charAt(0).toUpperCase() + text.slice(1)
}
function friendlyDate(iso) {
  if (!iso) return ''
  const d = new Date(iso + 'T12:00:00')
  if (Number.isNaN(d.getTime())) return iso
  return `${cap(WEEKDAYS_FULL[d.getDay()])}, ${d.getDate()} de ${MONTHS_FULL[d.getMonth()]}`
}
async function loadSuggestions() {
  try {
    const data = await api.get('/schedule/week')
    week.value = data.week || []
    const today = week.value.find((d) => d.is_today)
    if (today) selectedDay.value = today
    else if (week.value.length) selectedDay.value = week.value[0]
  } catch (error) {
    ElMessage.error('Erro ao carregar sugestões: ' + error.message)
  }
}
function selectDay(day) {
  selectedDay.value = day
}
async function createOrder(supplierId) {
  try {
    const res = await api.post('/schedule/create-order', { supplier_id: supplierId })
    ElMessage.success(`Pedido #${res.purchase_id} criado com ${res.items_count} itens!`)
    await loadSuggestions()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

onMounted(() => {
  load()
  loadSupport()
  loadSuggestions()
})
</script>

<template>
  <AppShell>
    <div class="dashboard">
      <div class="page-header">
        <div>
          <h1 class="page-title">Agenda de pedidos</h1>
          <p class="page-subtitle">Cadastre, acompanhe e gerencie os encargos de clientes.</p>
        </div>
        <button v-if="tab === 'orders'" type="button" class="btn-brand" @click="openNewOrder">
          <i class="fas fa-plus"></i> Novo pedido
        </button>
      </div>

      <div class="filter-segmented schedule-tabs" role="group" aria-label="Seções da agenda">
        <button type="button" :class="{ 'is-active': tab === 'orders' }" @click="tab = 'orders'">
          <i class="fas fa-clipboard-list"></i> Pedidos
        </button>
        <button type="button" :class="{ 'is-active': tab === 'suggestions' }" @click="tab = 'suggestions'">
          <i class="fas fa-truck"></i> Sugestões de compra
        </button>
      </div>

      <!-- Pedidos agendados -->
      <template v-if="tab === 'orders'">
        <div class="schedule-toolbar">
          <label class="toolbar-field">
            <span>Data</span>
            <input v-model="filters.date" type="date" @change="load" />
          </label>
          <label class="toolbar-field">
            <span>Status</span>
            <select v-model="filters.status" @change="load">
              <option value="">Todos</option>
              <option v-for="s in STATUSES" :key="s.key" :value="s.key">{{ s.label }}</option>
            </select>
          </label>
          <div class="search-box schedule-search">
            <i class="fas fa-search"></i>
            <input
              v-model="filters.q"
              type="search"
              placeholder="Buscar cliente/observação…"
              @keyup.enter="load"
            />
          </div>
          <button type="button" class="btn btn-ghost btn-sm" @click="filters = { date: '', status: '', q: '' }; load()">
            Limpar
          </button>
        </div>

        <div v-if="loading" class="muted">Carregando…</div>
        <div v-else-if="!orders.length" class="empty-state">
          <i class="fas fa-clipboard-list"></i>
          <h3>Nenhum pedido agendado</h3>
          <p>Crie um novo pedido para um cliente (retirada ou entrega).</p>
        </div>
        <div v-else class="table-card">
          <div class="table-container">
            <table class="data-table schedule-table">
              <thead>
                <tr>
                  <th>Data / hora</th>
                  <th>Cliente</th>
                  <th>Itens</th>
                  <th class="th-amount">Total</th>
                  <th>Status</th>
                  <th class="th-actions"><span class="sr-only">Ações</span></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="order in orders" :key="order.id">
                  <td class="nowrap">
                    <strong>{{ brdate(order.order_date) }}</strong>
                    <span v-if="order.order_time" class="muted-inline"> · {{ order.order_time }}</span>
                  </td>
                  <td>
                    <span class="cell-title">{{ order.customer_name }}</span>
                    <span v-if="order.obs" class="cell-sub">{{ order.obs }}</span>
                  </td>
                  <td>
                    <span class="cell-sub" :title="itemNames(order)">
                      {{ (order.items || []).length }} item(ns)
                      <template v-if="order.items && order.items.length"> · {{ order.items[0].name }}</template>
                    </span>
                  </td>
                  <td class="cell-amount nowrap">{{ brl(itemsTotal(order)) }}</td>
                  <td>
                    <select
                      class="status-select"
                      :class="statusClass(order.status)"
                      :value="order.status"
                      @change="changeStatus(order, $event.target.value)"
                    >
                      <option v-for="s in STATUSES" :key="s.key" :value="s.key">{{ s.label }}</option>
                    </select>
                  </td>
                  <td class="cell-actions">
                    <button type="button" class="icon-btn" title="Editar" @click="openEditOrder(order)">
                      <i class="fas fa-pen"></i>
                    </button>
                    <button type="button" class="icon-btn is-danger" title="Excluir" @click="askDelete(order)">
                      <i class="fas fa-trash"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>

      <!-- Sugestões de compra (reposição) -->
      <template v-else>
        <div class="schedule-layout">
          <div class="week-strip">
            <div
              v-for="day in week" :key="day.date"
              class="week-day"
              :class="{ 'is-today': day.is_today, 'is-selected': selectedDay?.date === day.date }"
              @click="selectDay(day)"
            >
              <span class="week-day-name">{{ day.day_name.slice(0, 3) }}</span>
              <span class="week-day-num">{{ new Date(day.date + 'T12:00:00').getDate() }}</span>
              <span v-if="day.product_count > 0" class="week-day-badge">{{ day.product_count }}</span>
            </div>
          </div>

          <div v-if="selectedDay" class="schedule-content">
            <h2>{{ friendlyDate(selectedDay.date) }}</h2>
            <div v-if="!selectedDay.suggestions.length" class="empty-state">
              <i class="fas fa-calendar-day"></i>
              <h3>Nenhum pedido sugerido</h3>
              <p>Não há sugestões de compra para este dia.</p>
            </div>
            <div v-else class="supplier-cards">
              <div v-for="s in selectedDay.suggestions" :key="s.supplier_id" class="supplier-card">
                <div class="supplier-card-header">
                  <div>
                    <h3>{{ s.supplier_name }}</h3>
                    <span class="supplier-product-count">{{ s.products.length }} produto(s)</span>
                  </div>
                  <button class="btn btn-primary btn-sm" @click="createOrder(s.supplier_id)">
                    <i class="fas fa-file-alt"></i> Criar compra
                  </button>
                </div>
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Produto</th>
                      <th class="th-number">Estoque atual</th>
                      <th class="th-number">Estoque ideal</th>
                      <th class="th-number">Sugerido</th>
                      <th class="th-number">Média/dia (28d)</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="p in s.products" :key="p.product_id">
                      <td>{{ p.product_name }}</td>
                      <td class="cell-number" :class="{ 'stock-low': p.current_stock <= 0 }">{{ p.current_stock }}</td>
                      <td class="cell-number">{{ p.ideal_stock }}</td>
                      <td class="cell-number cell-highlight">{{ p.suggested_qty }}</td>
                      <td class="cell-number">{{ p.avg_daily_sales.toFixed(1) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Modal Pedido -->
    <div class="modal" :class="{ 'is-open': showModal }">
      <div class="modal-content modal-content-lg">
        <div class="modal-header">
          <h2>{{ form.id ? 'Editar pedido' : 'Novo pedido' }}</h2>
          <button type="button" class="modal-close" @click="showModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="saveOrder">
          <div class="form-row">
            <div class="form-field flex-2">
              <label>Cliente *</label>
              <input
                v-model="form.customer_name"
                list="schedule-customers"
                type="text"
                placeholder="Nome do cliente"
                @input="onCustomerInput"
              />
              <datalist id="schedule-customers">
                <option v-for="c in customers" :key="c.id" :value="c.name" />
              </datalist>
            </div>
            <div class="form-field flex-1">
              <label>Data</label>
              <input v-model="form.order_date" type="date" />
            </div>
            <div class="form-field flex-1">
              <label>Hora</label>
              <input v-model="form.order_time" type="time" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-field flex-1">
              <label>Status</label>
              <select v-model="form.status">
                <option v-for="s in STATUSES" :key="s.key" :value="s.key">{{ s.label }}</option>
              </select>
            </div>
            <div class="form-field flex-3">
              <label>Observações</label>
              <input v-model="form.obs" type="text" placeholder="Ex: retirar às 18h, entregar no endereço…" />
            </div>
          </div>

          <div class="items-section">
            <div class="items-header"><h3>Produtos</h3></div>
            <ProductSearch
              :products="allProducts"
              placeholder="Buscar produto para adicionar…"
              @select="addProduct"
            />
            <p v-if="!items.length" class="muted-sm">Nenhum produto. Busque um acima.</p>
            <div v-else class="item-list">
              <div v-for="(item, idx) in items" :key="idx" class="item-row">
                <div class="form-field flex-3">
                  <label>Produto</label>
                  <input :value="item.name" type="text" disabled />
                </div>
                <div class="form-field flex-1">
                  <label>Qtd</label>
                  <input v-model.number="item.quantity" type="number" min="1" />
                </div>
                <div class="form-field flex-1">
                  <label>Valor</label>
                  <input
                    :value="item.unit_price"
                    type="text" inputmode="decimal" placeholder="0,00"
                    @input="moneyInput(item, 'unit_price', $event)"
                  />
                </div>
                <div class="form-field flex-1">
                  <label>Total</label>
                  <input :value="brl((parseInt(item.quantity) || 0) * (toNumber(item.unit_price) || 0))" type="text" disabled />
                </div>
                <button type="button" class="icon-btn remove-item" @click="removeItem(idx)">
                  <i class="fas fa-times"></i>
                </button>
              </div>
            </div>
          </div>

          <div class="totals-row">
            <span>Total do pedido: <strong>{{ brl(calcTotal()) }}</strong></span>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-ghost" @click="showModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Salvar' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog
      v-if="deleteTarget"
      title="Excluir pedido"
      :message="'Excluir o pedido de ' + deleteTarget.customer_name + '?'"
      confirm-label="Excluir"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </AppShell>
</template>

<style scoped>
.muted { color: var(--text-muted); padding: 24px 4px; }
.muted-inline { color: var(--text-muted); font-weight: 500; }
.muted-sm { color: var(--text-muted); font-size: 13px; padding: 8px 4px; }

.schedule-tabs { margin-bottom: 18px; }

.schedule-toolbar {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}
.toolbar-field { display: flex; flex-direction: column; gap: 4px; font-size: 12px; font-weight: 600; color: var(--text-secondary); }
.toolbar-field input, .toolbar-field select {
  padding: 7px 10px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; background: #fff;
}
.schedule-search { min-width: 220px; }

.schedule-table .status-select {
  padding: 4px 8px;
  border-radius: 999px;
  border: 1px solid var(--border);
  font-size: 12px;
  font-weight: 700;
  background: var(--surface-hover);
  cursor: pointer;
}
.status-select.is-low { color: #92400e; }
.status-select.is-info { color: #1d4ed8; }
.status-select.is-ok { color: #065f46; }
.status-select.is-off { color: #374151; }
.status-select.is-danger { color: #991b1b; }

.schedule-table .cell-actions { display: flex; gap: 4px; justify-content: flex-end; }

/* Modal reutiliza classes globais; aqui só ajustes leves */
.form-field { margin-bottom: 14px; }
.form-field label { display: block; font-size: 13px; font-weight: 600; color: var(--text-secondary); margin-bottom: 6px; }
.form-field input, .form-field select { width: 100%; padding: 9px 12px; border: 1px solid var(--border); border-radius: 6px; font-size: 14px; }
.form-row { display: flex; gap: 16px; }
.flex-1 { flex: 1; } .flex-2 { flex: 2; } .flex-3 { flex: 3; }
.items-section { margin: 12px 0; border: 1px solid var(--border); border-radius: 8px; padding: 14px 16px; }
.items-header h3 { margin: 0 0 8px; font-size: 14px; }
.item-list { display: flex; flex-direction: column; gap: 8px; margin-top: 8px; }
.item-row { display: flex; gap: 8px; align-items: flex-end; }
.item-row .form-field { margin-bottom: 0; }
.remove-item { margin-bottom: 4px; }
.totals-row { display: flex; justify-content: flex-end; font-size: 14px; margin: 8px 0; }

/* Sugestões (reposição) */
.schedule-layout { display: flex; flex-direction: column; gap: 20px; }
.week-strip { display: flex; gap: 8px; }
.week-day {
  flex: 1; min-width: 0; display: flex; flex-direction: column; align-items: center; gap: 2px;
  padding: 8px 4px; border-radius: var(--brand-radius-sm); cursor: pointer;
  background: var(--surface); border: 1px solid var(--border); box-shadow: var(--shadow-xs);
}
.week-day.is-today { border-color: var(--primary); }
.week-day.is-selected { background: var(--brand-gradient); border-color: transparent; color: #fff; }
.week-day-name { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; opacity: 0.75; }
.week-day-num { font-size: 18px; font-weight: 800; line-height: 1.2; }
.week-day-badge { background: var(--primary-soft); color: var(--primary); font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 999px; }
.week-day.is-selected .week-day-badge { background: rgba(255,255,255,0.25); color: #fff; }
.schedule-content h2 { font-size: 19px; font-weight: 800; margin: 0 0 10px; }
.empty-state { padding: 12px 16px 28px; color: var(--text-secondary); }
.empty-state i {
  font-size: 30px; margin-bottom: 12px; color: var(--primary); background: var(--primary-soft);
  display: inline-flex; align-items: center; justify-content: center; width: 56px; height: 56px; border-radius: 16px;
}
.empty-state h3 { font-size: 15px; font-weight: 700; color: var(--text); margin: 0 0 4px; }
.empty-state p { margin: 0; font-size: 13px; }
.supplier-cards { display: flex; flex-direction: column; gap: 16px; }
.supplier-card { background: var(--surface); border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.supplier-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.supplier-card-header h3 { font-size: 16px; margin: 0; }
.supplier-product-count { font-size: 12px; color: var(--text-muted); }
.stock-low { color: var(--danger); font-weight: 700; }
.cell-highlight { color: var(--primary); font-weight: 700; }
@media (max-width: 640px) { .week-strip { overflow-x: auto; } .week-day { min-width: 64px; } }
</style>
