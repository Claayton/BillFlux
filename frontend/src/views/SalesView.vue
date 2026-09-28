<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, brdateShort, maskMoney, moneyToDecimal } from '@/utils/format'
import { normalizeForSearch } from '@/utils/normalize'
import { paymentIcon, paymentColor } from '@/utils/payment'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import SaleEditModal from '@/views/SaleEditModal.vue'
import SaleReceiptModal from '@/views/SaleReceiptModal.vue'

const periods = [
  { key: 'hoje', label: 'Hoje', icon: 'fas fa-calendar-day' },
  { key: '7d', label: '7 dias', icon: 'fas fa-calendar-week' },
  { key: 'mes', label: 'Este mês', icon: 'fas fa-calendar' },
  { key: 'mes_anterior', label: 'Mês passado', icon: 'fas fa-calendar-minus' },
]

const active = ref('hoje')
const showValues = ref(false)
const saleFilter = ref('todas')
const search = ref('')
const showAvulsa = ref(false)
const data = ref(null)
const loading = ref(false)
const saving = ref(false)

const filterOptions = [
  { key: 'todas', label: 'Todas' },
  { key: 'ativas', label: 'Ativas' },
  { key: 'canceladas', label: 'Canceladas' },
]

const form = ref({
  date: new Date().toISOString().slice(0, 10),
  total: '',
  obs: '',
})

const expandedIds = ref(new Set())
const editManual = ref({ open: false, sale: null })
const editPdvId = ref(null)
const receiptSale = ref(null)
const cancelTarget = ref(null)

const editForm = ref({ date: '', total: '', obs: '' })

const currentPeriod = computed(() => (data.value?.periods || {})[active.value])

/** Dias cobertos por cada período (para "X de Y dias"). */
const periodDays = computed(() => {
  const now = new Date()
  if (active.value === 'hoje') return 1
  if (active.value === '7d') return 7
  if (active.value === 'mes') return now.getDate()
  const prev = new Date(now.getFullYear(), now.getMonth(), 0)
  return prev.getDate()
})

function brNum(value, digits = 1) {
  return Number(value).toFixed(digits).replace('.', ',')
}

/** Cards de indicadores (valor + dica secundária derivada dos dados). */
const kpis = computed(() => {
  const p = currentPeriod.value || {}
  const total = Number(p.total || 0)
  const count = Number(p.count || 0)
  const days = Number(p.days || 0)
  return [
    {
      key: 'total',
      label: 'Total vendido',
      icon: 'fas fa-wallet',
      value: fmt(total),
      hint: count > 0 ? `ticket médio ${brl(total / count)}` : null,
    },
    {
      key: 'count',
      label: 'Nº de vendas',
      icon: 'fas fa-receipt',
      value: showValues.value ? String(count) : '•••',
      hint: days > 0 ? `${brNum(count / days)} por dia` : null,
    },
    {
      key: 'days',
      label: 'Dias com venda',
      icon: 'fas fa-calendar-check',
      value: showValues.value ? String(days) : '•••',
      hint: `${days} de ${periodDays.value} dia${periodDays.value === 1 ? '' : 's'}`,
    },
    {
      key: 'avg',
      label: 'Média por dia',
      icon: 'fas fa-chart-line',
      value: fmt(p.avg),
      hint: null,
    },
  ]
})

const statusCounts = computed(() => {
  const sales = data.value?.sales || []
  return {
    todas: sales.length,
    ativas: sales.filter((s) => !s.cancelled).length,
    canceladas: sales.filter((s) => Boolean(s.cancelled)).length,
  }
})

const filteredSales = computed(() => {
  if (!data.value) return []
  if (saleFilter.value === 'todas') return data.value.sales
  const wantCancelled = saleFilter.value === 'canceladas'
  return data.value.sales.filter((sale) => Boolean(sale.cancelled) === wantCancelled)
})

const searchedSales = computed(() => {
  const q = normalizeForSearch(search.value.trim())
  if (!q) return filteredSales.value
  return filteredSales.value.filter((sale) => {
    const hay = [
      String(sale.id),
      sale.obs || '',
      sale.payment || '',
      ...(sale.items || []).map((item) => `${item.quantity} ${item.name}`),
    ]
      .map((part) => normalizeForSearch(part))
      .join(' ')
    return hay.includes(q)
  })
})

function mask(event) {
  form.value.total = maskMoney(event.target.value)
}

function maskEdit(event) {
  editForm.value.total = maskMoney(event.target.value)
}

/** Resumo compacto da coluna de itens: "6 itens" + primeiro + restante. */
function itemsTitle(sale) {
  return (sale.items || []).map((item) => `${item.quantity}x ${item.name}`).join('\n')
}

function firstItemLabel(sale) {
  const items = sale.items || []
  const [first] = items
  if (!first) return ''
  const rest = items.length - 1
  return `${first.quantity}x ${first.name}${rest > 0 ? ` +${rest}` : ''}`
}

function expandKey(sale) {
  return `${sale.kind}-${sale.id}`
}

function isExpanded(sale) {
  return expandedIds.value.has(expandKey(sale))
}

function toggleExpand(sale) {
  const key = expandKey(sale)
  if (expandedIds.value.has(key)) {
    expandedIds.value.delete(key)
  } else {
    expandedIds.value.add(key)
  }
  expandedIds.value = new Set(expandedIds.value)
}

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/sales')
  } finally {
    loading.value = false
  }
}

async function submit() {
  const total = moneyToDecimal(form.value.total)
  if (!form.value.date || total === null || total <= 0) {
    ElMessage.warning('Informe data e um total válido.')
    return
  }
  saving.value = true
  try {
    data.value = await api.post('/sales', {
      date: form.value.date,
      total: String(total),
      obs: form.value.obs,
    })
    form.value = {
      date: new Date().toISOString().slice(0, 10),
      total: '',
      obs: '',
    }
    ElMessage.success('Venda lançada!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

function printSale(sale) {
  receiptSale.value = sale
}

function openEditManual(sale) {
  editForm.value = {
    date: sale.date,
    total: maskMoney(String(Math.round(sale.total * 100))),
    obs: sale.obs || '',
  }
  editManual.value = { open: true, sale }
}

async function saveEditManual() {
  const sale = editManual.value.sale
  const total = moneyToDecimal(editForm.value.total)
  if (!editForm.value.date || total === null || total <= 0) {
    ElMessage.warning('Informe data e um total válido.')
    return
  }
  saving.value = true
  try {
    data.value = await api.put(`/sales/${sale.id}`, {
      date: editForm.value.date,
      total: String(total),
      obs: editForm.value.obs,
    })
    editManual.value = { open: false, sale: null }
    ElMessage.success('Venda editada!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

function openEditPdv(sale) {
  editPdvId.value = sale.id
}

function onPdvEdited() {
  editPdvId.value = null
  load()
}

function askCancel(sale) {
  cancelTarget.value = sale
}

async function confirmCancel(reason) {
  const sale = cancelTarget.value
  cancelTarget.value = null
  if (!sale) return
  const body = reason && String(reason).trim() ? { reason: String(reason).trim() } : {}
  try {
    if (sale.kind === 'pdv') {
      data.value = await api.post(`/sales/orders/${sale.id}/cancel`, body)
      ElMessage.success('Venda cancelada e estoque restaurado.')
    } else {
      data.value = await api.post(`/sales/${sale.id}/cancel`, body)
      ElMessage.success('Venda cancelada.')
    }
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function fmt(value) {
  return showValues.value ? brl(value) : 'R$ ••••'
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="dashboard">
      <div class="page-header">
        <div>
          <h1 class="page-title">Vendas</h1>
          <p class="page-subtitle">Acompanhe suas vendas e registre lançamentos avulsos.</p>
        </div>
        <router-link class="btn-brand" to="/pdv">
          <i class="fas fa-cash-register"></i> Abrir PDV
        </router-link>
      </div>

      <div class="stats-toolbar">
        <div class="filter-segmented" role="group" aria-label="Período das métricas">
          <button
            v-for="p in periods"
            :key="p.key"
            type="button"
            :class="{ 'is-active': active === p.key }"
            @click="active = p.key"
          >
            <i :class="p.icon"></i> {{ p.label }}
          </button>
        </div>
        <button
          type="button"
          class="btn btn-ghost btn-sm eye-toggle"
          :title="showValues ? 'Ocultar valores' : 'Mostrar valores'"
          :aria-pressed="showValues ? 'true' : 'false'"
          @click="showValues = !showValues"
        >
          <i :class="showValues ? 'fas fa-eye' : 'fas fa-eye-slash'"></i>
          {{ showValues ? 'Ocultar valores' : 'Mostrar valores' }}
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="stats-row">
          <div v-for="kpi in kpis" :key="kpi.key" class="stat-card">
            <div class="stat-top">
              <span class="icon-tile"><i :class="kpi.icon"></i></span>
              <span class="stat-label">{{ kpi.label }}</span>
            </div>
            <span class="stat-value">{{ kpi.value }}</span>
            <span v-if="kpi.hint" class="stat-hint">
              {{ showValues ? kpi.hint : '•••' }}
            </span>
          </div>
        </div>

        <div class="sales-form-card sales-collapse">
          <button
            type="button"
            class="sales-collapse-head"
            :aria-expanded="showAvulsa ? 'true' : 'false'"
            @click="showAvulsa = !showAvulsa"
          >
            <span class="collapse-icon"><i class="fas fa-plus"></i></span>
            <span class="collapse-text">
              <strong>Lançar venda avulsa</strong>
              <small>Registre uma venda sem produtos</small>
            </span>
            <i class="fas fa-chevron-down collapse-chevron" :class="{ open: showAvulsa }"></i>
          </button>
          <div class="sales-collapse-body" :class="{ open: showAvulsa }">
            <form class="sales-form" @submit.prevent="submit">
              <div class="form-field">
                <label for="sale_date">Data</label>
                <input id="sale_date" v-model="form.date" type="date" required />
              </div>
              <div class="form-field">
                <label for="sale_total">Total bruto</label>
                <input
                  id="sale_total"
                  :value="form.total"
                  type="text"
                  placeholder="R$ 0,00"
                  inputmode="decimal"
                  required
                  @input="mask"
                />
              </div>
              <div class="form-field">
                <label for="sale_obs">Observações (opcional)</label>
                <input id="sale_obs" v-model="form.obs" type="text" placeholder="Ex: feira, balcão..." />
              </div>
              <div class="sales-form-actions">
                <button type="submit" class="btn btn-primary" :disabled="saving">
                  <i class="fas fa-check"></i> {{ saving ? 'Lançando…' : 'Lançar' }}
                </button>
              </div>
            </form>
          </div>
        </div>

        <div class="table-card">
          <div class="table-card-head">
            <h2>Histórico de vendas</h2>
            <div class="table-head-tools">
              <div class="search-box">
                <i class="fas fa-search"></i>
                <input
                  v-model="search"
                  type="search"
                  placeholder="Buscar venda…"
                  aria-label="Buscar vendas por ID, observação, itens ou pagamento"
                />
              </div>
              <div class="filter-segmented sales-filter" role="group" aria-label="Filtrar vendas">
                <button
                  v-for="opt in filterOptions"
                  :key="opt.key"
                  type="button"
                  :class="{ 'is-active': saleFilter === opt.key }"
                  @click="saleFilter = opt.key"
                >
                  {{ opt.label }}
                  <span class="filter-count">{{ statusCounts[opt.key] }}</span>
                </button>
              </div>
            </div>
          </div>
          <div v-if="!searchedSales.length" class="empty-state">
            <i class="fas fa-cash-register"></i>
            <h3>Nenhuma venda {{ saleFilter === 'canceladas' ? 'cancelada' : 'encontrada' }}</h3>
            <p>Lance uma venda avulsa ou feche uma venda no PDV.</p>
          </div>
          <div v-else class="sales-list-scroll">
            <div class="sales-list">
            <div class="sales-list-header">
              <span>ID</span>
              <span>Valor</span>
              <span>Origem</span>
              <span>Data / hora</span>
              <span>Itens</span>
              <span>Ações</span>
            </div>
            <div
              v-for="sale in searchedSales"
              :key="sale.kind + '-' + sale.id"
              class="sale-row"
              :class="{ 'is-cancelled': sale.cancelled }"
            >
              <div class="sale-row-main">
                <span class="sale-id">#{{ sale.id }}</span>

                <span class="sale-value">
                  <i
                    class="sale-payment-icon"
                    :class="[paymentIcon(sale.payment), paymentColor(sale.payment)]"
                    :title="sale.payment || ''"
                  ></i>
                  {{ brl(sale.total) }}
                </span>

                <span class="sale-origin-cell">
                  <span v-if="sale.cancelled" class="sale-cancelled-badge">Cancelada</span>
                  <span :class="sale.kind === 'pdv' ? 'source-badge source-badge-pdv' : 'source-badge source-badge-manual'">
                    <i :class="sale.kind === 'pdv' ? 'fas fa-cash-register' : 'fas fa-hand-holding-usd'"></i>
                    {{ sale.kind === 'pdv' ? 'PDV' : 'Manual' }}
                  </span>
                </span>

                <span class="sale-date">
                  <span class="sale-date-line">
                    {{ brdateShort(sale.date) }}
                    <span v-if="sale.date === data.today" class="sale-today">hoje</span>
                  </span>
                  <span v-if="sale.time" class="sale-time">{{ sale.time }}</span>
                </span>

                <div class="sale-items">
                  <template v-if="sale.items.length">
                    <span
                      class="sale-items-summary"
                      :title="itemsTitle(sale)"
                    >
                      <strong>{{ sale.items.length }} {{ sale.items.length === 1 ? 'item' : 'itens' }}</strong>
                      <span class="sale-items-first">{{ firstItemLabel(sale) }}</span>
                    </span>
                    <button
                      v-if="sale.items.length > 3"
                      type="button"
                      class="sale-items-more"
                      @click="toggleExpand(sale)"
                    >
                      <i :class="isExpanded(sale) ? 'fas fa-chevron-up' : 'fas fa-chevron-down'"></i>
                      {{ isExpanded(sale) ? 'ver menos' : 'ver todos (' + sale.items.length + ')' }}
                    </button>
                  </template>
                  <span v-else class="sale-no-items">Sem itens</span>
                </div>

                <div class="sale-actions">
                  <button
                    type="button"
                    class="icon-btn"
                    title="Imprimir recibo"
                    @click="printSale(sale)"
                  >
                    <i class="fas fa-print"></i>
                  </button>
                  <button
                    v-if="!sale.cancelled"
                    type="button"
                    class="icon-btn"
                    title="Editar venda"
                    @click="sale.kind === 'pdv' ? openEditPdv(sale) : openEditManual(sale)"
                  >
                    <i class="fas fa-pen"></i>
                  </button>
                  <button
                    v-if="!sale.cancelled"
                    type="button"
                    class="icon-btn is-danger"
                    title="Cancelar venda"
                    @click="askCancel(sale)"
                  >
                    <i class="fas fa-trash"></i>
                  </button>
                </div>
              </div>

              <div v-if="isExpanded(sale) && sale.items.length > 3" class="sale-items-expanded">
                <div v-for="item in sale.items" :key="item.name" class="sale-item-expanded">
                  <span>{{ item.name }}</span>
                  <strong>{{ item.quantity }}x</strong>
                </div>
              </div>
            </div>
          </div>
          </div>
        </div>
      </template>
    </div>

    <div class="modal" :class="{ 'is-open': editManual.open }">
      <div class="modal-content modal-content-sm">
        <div class="modal-header">
          <h2>Editar venda #{{ editManual.sale?.id }}</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="editManual = { open: false, sale: null }">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="saveEditManual">
          <div class="form-field">
            <label for="edit_date">Data</label>
            <input id="edit_date" v-model="editForm.date" type="date" required />
          </div>
          <div class="form-field">
            <label for="edit_total">Total bruto</label>
            <input id="edit_total" :value="editForm.total" type="text" placeholder="R$ 0,00" inputmode="decimal" required @input="maskEdit" />
          </div>
          <div class="form-field">
            <label for="edit_obs">Observações</label>
            <input id="edit_obs" v-model="editForm.obs" type="text" placeholder="Opcional..." />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-ghost modal-cancel" @click="editManual = { open: false, sale: null }">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Salvar' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <SaleEditModal
      v-if="editPdvId"
      :order-id="editPdvId"
      @saved="onPdvEdited"
      @close="editPdvId = null"
    />

    <SaleReceiptModal
      v-if="receiptSale"
      :sale="receiptSale"
      @close="receiptSale = null"
    />

    <ConfirmDialog
      v-if="cancelTarget"
      title="Cancelar venda"
      :message="cancelTarget.kind === 'pdv'
        ? `Cancelar a venda #${cancelTarget.id}? O estoque dos itens será restaurado.`
        : `Excluir a venda #${cancelTarget.id}?`"
      confirm-label="Cancelar venda"
      danger
      input-label="Motivo (opcional)"
      input-placeholder="Ex: erro de lançamento, desistência..."
      @confirm="confirmCancel($event)"
      @cancel="cancelTarget = null"
    />
  </AppShell>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}
</style>