<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, brdateShort, maskMoney, moneyToDecimal } from '@/utils/format'
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

const PAYMENT_ICONS = {
  dinheiro: 'fas fa-money-bill-wave',
  pix: 'fas fa-qrcode',
  credito: 'fas fa-credit-card',
  debito: 'fas fa-credit-card',
  vr: 'fas fa-utensils',
  va: 'fas fa-utensils',
}

const active = ref('hoje')
const showValues = ref(true)
const data = ref(null)
const loading = ref(false)
const saving = ref(false)

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

function paymentIcon(payment) {
  const key = (payment || '').toLowerCase().trim()
  return PAYMENT_ICONS[key] || 'fas fa-credit-card'
}

function mask(event) {
  form.value.total = maskMoney(event.target.value)
}

function maskEdit(event) {
  editForm.value.total = maskMoney(event.target.value)
}

function visibleItems(sale) {
  return sale.items.slice(0, 3)
}

function isExpanded(sale) {
  return expandedIds.value.has(sale.id)
}

function toggleExpand(sale) {
  if (expandedIds.value.has(sale.id)) {
    expandedIds.value.delete(sale.id)
  } else {
    expandedIds.value.add(sale.id)
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

async function confirmCancel() {
  const sale = cancelTarget.value
  cancelTarget.value = null
  if (!sale) return
  try {
    if (sale.kind === 'pdv') {
      data.value = await api.del(`/sales/orders/${sale.id}`)
      ElMessage.success('Venda cancelada e estoque restaurado.')
    } else {
      data.value = await api.del(`/sales/${sale.id}`)
      ElMessage.success('Venda excluída.')
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
          <p class="page-subtitle">Lançamentos avulsos e vendas do PDV.</p>
        </div>
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
          class="icon-btn eye-btn"
          :title="showValues ? 'Ocultar valores' : 'Mostrar valores'"
          :aria-pressed="showValues ? 'true' : 'false'"
          @click="showValues = !showValues"
        >
          <i :class="showValues ? 'fas fa-eye' : 'fas fa-eye-slash'"></i>
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="stats-row">
          <div class="stat-card">
            <span class="stat-label">Total vendido</span>
            <span class="stat-value stat-value-success">{{ fmt(currentPeriod?.total) }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Nº de vendas</span>
            <span class="stat-value">{{ showValues ? currentPeriod?.count : '•••' }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Dias com venda</span>
            <span class="stat-value">{{ showValues ? currentPeriod?.days : '•••' }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Média por dia</span>
            <span class="stat-value">{{ fmt(currentPeriod?.avg) }}</span>
          </div>
        </div>

        <div class="sales-form-card">
          <div class="sales-form-head">
            <i class="fas fa-hand-holding-usd"></i>
            <div>
              <span>Lançar venda avulsa</span>
              <small>Apenas valor, sem produtos.</small>
            </div>
          </div>
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

        <div class="table-card">
          <div class="table-card-head">
            <h2>Vendas</h2>
          </div>
          <div v-if="!data.sales.length" class="empty-state">
            <i class="fas fa-cash-register"></i>
            <h3>Nenhuma venda ainda</h3>
            <p>Lance uma venda avulsa ou feche uma venda no PDV.</p>
          </div>
          <div v-else class="sales-list">
            <div class="sales-list-header">
              <span>ID</span>
              <span>Valor</span>
              <span>Origem</span>
              <span>Data / hora</span>
              <span>Itens</span>
              <span class="sales-th-actions">Ações</span>
            </div>
            <div v-for="sale in data.sales" :key="sale.kind + '-' + sale.id" class="sale-row">
              <div class="sale-row-main">
                <span class="sale-id">#{{ sale.id }}</span>

                <span class="sale-value">
                  <i class="sale-payment-icon" :class="paymentIcon(sale.payment)" :title="sale.payment || ''"></i>
                  {{ brl(sale.total) }}
                </span>

                <span :class="sale.kind === 'pdv' ? 'source-badge source-badge-pdv' : 'source-badge source-badge-manual'">
                  <i :class="sale.kind === 'pdv' ? 'fas fa-cash-register' : 'fas fa-hand-holding-usd'"></i>
                  {{ sale.kind === 'pdv' ? 'PDV' : 'Manual' }}
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
                    <span v-for="item in visibleItems(sale)" :key="item.name" class="sale-item-chip">
                      {{ item.quantity }}x {{ item.name }}
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
                    type="button"
                    class="icon-btn"
                    title="Editar venda"
                    @click="sale.kind === 'pdv' ? openEditPdv(sale) : openEditManual(sale)"
                  >
                    <i class="fas fa-pen"></i>
                  </button>
                  <button type="button" class="icon-btn is-danger" title="Cancelar venda" @click="askCancel(sale)">
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
      @confirm="confirmCancel"
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