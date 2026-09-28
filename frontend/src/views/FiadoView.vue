<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, brdateShort } from '@/utils/format'
import { normalizeForSearch } from '@/utils/normalize'
import AppShell from '@/components/AppShell.vue'

const items = ref([])
const totals = ref({ open_amount: 0, open_count: 0, customers: 0, paid_count: 0 })
const loading = ref(false)
const statusFilter = ref('open')
const search = ref('')

const methods = ref([])
const paying = ref(null)
const payForm = ref({ amount: '', method_id: null })
const paySaving = ref(false)

const statusOptions = [
  { id: 'open', label: 'Em aberto' },
  { id: 'paid', label: 'Quitados' },
  { id: 'all', label: 'Todos' },
]

async function load() {
  loading.value = true
  try {
    const data = await api.get(`/receivables?status=${statusFilter.value}`)
    items.value = data.items
    totals.value = data.totals
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

const filtered = computed(() => {
  const query = normalizeForSearch(search.value)
  if (!query) return items.value
  return items.value.filter((r) => normalizeForSearch(r.customer_name).includes(query))
})

function selectStatus(statusId) {
  statusFilter.value = statusId
  load()
}

function openPay(receivable) {
  paying.value = receivable
  payForm.value = {
    amount: String(receivable.balance.toFixed(2)).replace('.', ','),
    method_id: methods.value[0]?.id ?? null,
  }
}

function closePay() {
  paying.value = null
}

function parseAmount(raw) {
  if (raw === '' || raw === null || raw === undefined) return NaN
  const text = String(raw).trim()
  const normalized = text.includes(',')
    ? text.replace(/\./g, '').replace(',', '.')
    : text
  return Number(normalized)
}

async function submitPayment() {
  const amount = parseAmount(payForm.value.amount)
  if (!payForm.value.method_id) {
    ElMessage.warning('Selecione a forma de pagamento.')
    return
  }
  if (Number.isNaN(amount) || amount <= 0) {
    ElMessage.warning('Informe um valor maior que zero.')
    return
  }
  if (amount > paying.value.balance + 0.009) {
    ElMessage.warning(
      `Valor acima do saldo em aberto (${brl(paying.value.balance)}).`
    )
    return
  }

  paySaving.value = true
  try {
    const result = await api.post(`/receivables/${paying.value.id}/payments`, {
      amount: amount.toFixed(2),
      method_id: payForm.value.method_id,
    })
    if (result.in_caixa) {
      ElMessage.success('Recebimento registrado no caixa!')
    } else {
      ElMessage.warning(
        'Recebimento registrado. Não há caixa aberto, então não entrou no fechamento.'
      )
    }
    closePay()
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    paySaving.value = false
  }
}

async function loadMethods() {
  try {
    const data = await api.get('/payments')
    const fiadoAliases = ['fiado', 'crediario']
    methods.value = (data.methods || []).filter((m) => {
      const key = (m.name || '')
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim()
      return m.active && !fiadoAliases.includes(key)
    })
  } catch {
    methods.value = []
  }
}

onMounted(() => {
  load()
  loadMethods()
})
</script>

<template>
  <AppShell>
    <div class="dashboard fiado-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">Fiado</h1>
          <p class="page-subtitle">
            Contas a receber: débitos de clientes e recebimentos do crediário.
          </p>
        </div>
      </div>

      <div class="fiado-stats">
        <div class="stat-card">
          <span class="stat-label">Total em aberto</span>
          <span class="stat-value">{{ brl(totals.open_amount) }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Débitos abertos</span>
          <span class="stat-value">{{ totals.open_count }}</span>
        </div>
        <div class="stat-card">
          <span class="stat-label">Clientes devendo</span>
          <span class="stat-value">{{ totals.customers }}</span>
        </div>
      </div>

      <div class="products-toolbar fiado-toolbar">
        <div class="filter-segmented" role="tablist" aria-label="Status dos débitos">
          <button
            v-for="option in statusOptions"
            :key="option.id"
            type="button"
            :class="{ 'is-active': statusFilter === option.id }"
            @click="selectStatus(option.id)"
          >
            {{ option.label }}
          </button>
        </div>
        <div class="search-box products-search-box">
          <i class="fas fa-search"></i>
          <input
            v-model="search"
            type="text"
            placeholder="Buscar por cliente..."
            aria-label="Buscar débito por cliente"
          />
          <button
            v-if="search"
            type="button"
            class="search-clear"
            aria-label="Limpar busca"
            @click="search = ''"
          >
            <i class="fas fa-times"></i>
          </button>
        </div>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <div v-else class="table-card">
        <div class="table-container">
          <table class="data-table fiado-table">
            <thead>
              <tr>
                <th>Cliente</th>
                <th class="col-order">Pedido</th>
                <th class="col-date">Data</th>
                <th class="col-qty">Valor</th>
                <th class="col-qty">Pago</th>
                <th class="col-qty">Saldo</th>
                <th class="col-actions-table">Ações</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="receivable in filtered" :key="receivable.id">
                <td>
                  <span class="cell-ellipsis">{{ receivable.customer_name }}</span>
                </td>
                <td class="col-order">
                  <span v-if="receivable.order_id">#{{ receivable.order_id }}</span>
                  <span v-else>—</span>
                </td>
                <td class="col-date">{{ brdateShort(receivable.date) }}</td>
                <td class="col-qty">{{ brl(receivable.amount) }}</td>
                <td class="col-qty">{{ brl(receivable.paid) }}</td>
                <td class="col-qty">
                  <strong
                    class="fiado-balance"
                    :class="{ 'is-paid': receivable.balance <= 0 }"
                  >
                    {{ brl(receivable.balance) }}
                  </strong>
                </td>
                <td class="col-actions-table">
                  <button
                    v-if="receivable.balance > 0"
                    type="button"
                    class="btn-brand btn-sm"
                    :aria-label="`Receber de ${receivable.customer_name}`"
                    @click="openPay(receivable)"
                  >
                    <i class="fas fa-hand-holding-usd"></i> Receber
                  </button>
                  <span v-else class="status-badge is-ok">Quitado</span>
                </td>
              </tr>
              <tr v-if="!filtered.length" class="empty-row">
                <td colspan="7" class="empty-state">
                  <i class="fas fa-hand-holding-usd"></i>
                  <h3>{{ statusFilter === 'open' ? 'Nenhum débito em aberto' : 'Nenhum débito encontrado' }}</h3>
                  <p>
                    {{
                      search
                        ? 'Tente buscar outro cliente.'
                        : 'Vendas fiadas aparecem aqui automaticamente.'
                    }}
                  </p>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div v-if="paying" class="modal is-open" data-test="pay-modal">
        <div class="modal-content modal-content-sm">
          <div class="modal-header">
            <h2>Receber de {{ paying.customer_name }}</h2>
            <button type="button" class="modal-close" aria-label="Fechar" @click="closePay">
              &times;
            </button>
          </div>
          <div class="confirm-body">
            <dl class="confirm-summary">
              <div class="confirm-summary-row">
                <dt>Saldo em aberto</dt>
                <dd>{{ brl(paying.balance) }}</dd>
              </div>
              <div v-if="paying.order_id" class="confirm-summary-row">
                <dt>Pedido</dt>
                <dd>#{{ paying.order_id }}</dd>
              </div>
            </dl>
            <div class="form-field">
              <label for="pay-amount">Valor recebido</label>
              <input
                id="pay-amount"
                v-model="payForm.amount"
                type="text"
                inputmode="decimal"
                placeholder="0,00"
              />
            </div>
            <div class="form-field">
              <label for="pay-method">Forma de pagamento</label>
              <select id="pay-method" v-model="payForm.method_id">
                <option
                  v-for="method in methods"
                  :key="method.id"
                  :value="method.id"
                >
                  {{ method.name }}
                </option>
              </select>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-ghost modal-cancel" @click="closePay">
              Voltar
            </button>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="paySaving"
              @click="submitPayment"
            >
              <i class="fas fa-check"></i>
              {{ paySaving ? 'Registrando…' : 'Receber' }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.fiado-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 18px;
  flex-wrap: wrap;
}

.fiado-stats .stat-card {
  flex: 1;
  min-width: 160px;
}

.fiado-toolbar {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.fiado-table .col-order {
  width: 80px;
}
.fiado-table .col-date {
  width: 96px;
}
.fiado-table .col-qty {
  width: 110px;
  text-align: right;
}
.fiado-table .col-actions-table {
  width: 130px;
}

.fiado-balance.is-paid {
  color: #15803d;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.82rem;
}

.cell-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  display: block;
  max-width: 260px;
}

.form-field select {
  width: 100%;
  padding: 9px 10px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
  background: #fff;
  font-size: 0.92rem;
}
</style>
