<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, maskMoney, moneyToDecimal } from '@/utils/format'
import AppShell from '@/components/AppShell.vue'

const data = ref(null)
const loading = ref(false)
const saving = ref(false)

const isOpen = computed(() => !!data.value?.open)
const methods = computed(() => data.value?.payment_methods || {})

// abertura: só Dinheiro e PIX
const OPEN_METHODS = { Dinheiro: true, PIX: true }
const openMethods = computed(() => {
  const result = {}
  for (const [mid, name] of Object.entries(methods.value)) {
    if (OPEN_METHODS[name]) result[mid] = name
  }
  return result
})

// abertura: dict methodId -> "100,00"
const openDetails = ref({})

// fechamento: dict methodId -> "150,00" (o que o operador contou)
const closeDetails = ref({})
const closeObs = ref('')

const systemTotals = computed(() => data.value?.system_totals_named || {})

const closeTotalCounted = computed(() => {
  let sum = 0
  for (const mid of Object.keys(closeDetails.value)) {
    const v = moneyToDecimal(closeDetails.value[mid])
    if (v !== null) sum += v
  }
  return Math.round(sum * 100) / 100
})

const closeSystemTotal = computed(() => {
  let sum = 0
  for (const item of Object.values(systemTotals.value)) {
    sum += item.total
  }
  return Math.round(sum * 100) / 100
})

const openTotal = computed(() => {
  let sum = 0
  for (const mid of Object.keys(openDetails.value)) {
    const v = moneyToDecimal(openDetails.value[mid])
    if (v !== null) sum += v
  }
  return Math.round(sum * 100) / 100
})

function initOpenDetails() {
  const details = {}
  for (const [mid, name] of Object.entries(openMethods.value)) {
    details[mid] = ''
  }
  openDetails.value = details
}

function initCloseDetails() {
  const details = {}
  for (const mid of Object.keys(methods.value)) {
    details[mid] = ''
  }
  closeDetails.value = details
}

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/caixa')
    if (!isOpen.value) {
      initOpenDetails()
    } else {
      initCloseDetails()
    }
  } finally {
    loading.value = false
  }
}

function onOpenInput(mid, event) {
  openDetails.value[mid] = maskMoney(event.target.value)
}

function onCloseInput(mid, event) {
  closeDetails.value[mid] = maskMoney(event.target.value)
}

async function openRegister() {
  const details = {}
  let total = 0
  for (const [mid, raw] of Object.entries(openDetails.value)) {
    const v = moneyToDecimal(raw)
    if (v === null || v < 0) {
      ElMessage.warning(`Informe um valor válido para ${openMethods.value[mid]}.`)
      return
    }
    details[mid] = String(v)
    total += v
  }
  if (total <= 0) {
    ElMessage.warning('O valor total de abertura deve ser maior que zero.')
    return
  }
  saving.value = true
  try {
    data.value = await api.post('/caixa/open', { opening_details: details })
    ElMessage.success('Caixa aberto!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function closeRegister() {
  const details = {}
  let total = 0
  for (const [mid, raw] of Object.entries(closeDetails.value)) {
    const v = moneyToDecimal(raw)
    if (v === null || v < 0) {
      ElMessage.warning(`Informe um valor válido para ${methods.value[mid]}.`)
      return
    }
    details[mid] = String(v)
    total += v
  }
  if (total <= 0) {
    ElMessage.warning('O valor total contado deve ser maior que zero.')
    return
  }
  saving.value = true
  try {
    data.value = await api.post('/caixa/close', {
      closing_details: details,
      obs: closeObs.value,
    })
    closeObs.value = ''
    ElMessage.success('Caixa fechado!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

function methodDiff(mid) {
  const systemVal = systemTotals.value[mid]?.total || 0
  const counted = moneyToDecimal(closeDetails.value[mid])
  if (counted === null) return null
  return Math.round((counted - systemVal) * 100) / 100
}

function methodDiffClass(mid) {
  const diff = methodDiff(mid)
  if (diff === null) return ''
  if (Math.abs(diff) < 0.01) return 'diff-ok'
  return diff > 0 ? 'diff-sobra' : 'diff-falta'
}

function methodDiffLabel(mid) {
  const diff = methodDiff(mid)
  if (diff === null) return ''
  if (Math.abs(diff) < 0.01) return 'Correto'
  const prefix = diff > 0 ? '+' : ''
  return `${prefix}${brl(diff)}`
}

function fmtDate(iso) {
  if (!iso) return '—'
  return iso.replace('T', ' ').slice(0, 16)
}

function diffClass(expected, closing) {
  if (expected == null || closing == null) return ''
  const diff = closing - expected
  if (Math.abs(diff) < 0.01) return 'diff-ok'
  return diff > 0 ? 'diff-sobra' : 'diff-falta'
}

function diffLabel(expected, closing) {
  if (expected == null || closing == null) return ''
  const diff = Math.round((closing - expected) * 100) / 100
  if (Math.abs(diff) < 0.01) return 'Feito ✓'
  const prefix = diff > 0 ? '+' : ''
  return `${prefix}${brl(diff)}`
}

onMounted(() => {
  load()
})
</script>

<template>
  <AppShell>
    <div class="dashboard">
      <div class="page-header">
        <div>
          <h1 class="page-title">Caixa</h1>
          <p class="page-subtitle">Controle de abertura e fechamento do caixa.</p>
        </div>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <!-- Status card -->
        <div class="caixa-status-card" :class="isOpen ? 'is-open' : 'is-closed'">
          <div class="caixa-status-icon">
            <i :class="isOpen ? 'fas fa-lock-open' : 'fas fa-lock'"></i>
          </div>
          <div class="caixa-status-info">
            <h2>{{ isOpen ? 'Caixa Aberto' : 'Caixa Fechado' }}</h2>
            <p v-if="data.open">
              Aberto por <strong>{{ data.open.opened_by }}</strong> em
              {{ fmtDate(data.open.opened_at) }}
            </p>
            <p v-else-if="data.last_closed">
              Último fechamento: {{ fmtDate(data.last_closed.closed_at) }}
            </p>
            <p v-else>Nenhum caixa registrado ainda.</p>
          </div>
          <div v-if="data.open" class="caixa-status-value">
            <span class="label">Valor inicial</span>
            <span class="value">{{ brl(data.open.opening_amount) }}</span>
          </div>
        </div>

        <!-- Abrir Caixa -->
        <div v-if="!isOpen" class="caixa-action-card">
          <h3><i class="fas fa-door-open"></i> Abrir Caixa</h3>
          <p>Informe o valor em dinheiro e PIX que estão no caixa na abertura.</p>
          <form class="caixa-form" @submit.prevent="openRegister">
            <div class="method-rows">
              <div v-for="(name, mid) in openMethods" :key="mid" class="method-row">
                <span class="method-label">{{ name }}</span>
                <div class="method-input">
                  <span class="input-prefix">R$</span>
                  <input
                    :value="openDetails[mid] || ''"
                    type="text"
                    placeholder="0,00"
                    inputmode="decimal"
                    @input="onOpenInput(mid, $event)"
                  />
                </div>
              </div>
            </div>
            <div class="open-total">
              <span>Total em caixa:</span>
              <strong>{{ brl(openTotal) }}</strong>
            </div>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-door-open"></i> {{ saving ? 'Abrindo…' : 'Abrir caixa' }}
            </button>
          </form>
        </div>

        <!-- Fechar Caixa -->
        <div v-if="isOpen" class="caixa-action-card caixa-close">
          <h3><i class="fas fa-door-closed"></i> Fechar Caixa</h3>
          <p>Preencha o valor contado para cada forma de pagamento. O sistema mostra o total registrado ao lado.</p>

          <div class="method-rows method-rows-close">
            <div v-for="(name, mid) in methods" :key="mid" class="method-row method-row-close">
              <span class="method-label">{{ name }}</span>
              <div class="close-trio">
                <div class="method-input">
                  <span class="input-prefix">R$</span>
                  <input
                    :value="closeDetails[mid] || ''"
                    type="text"
                    placeholder="0,00"
                    inputmode="decimal"
                    @input="onCloseInput(mid, $event)"
                  />
                </div>
                <span class="system-total">{{ brl(systemTotals[mid]?.total || 0) }}</span>
                <span
                  class="method-diff"
                  :class="methodDiffClass(mid)"
                >{{ methodDiffLabel(mid) }}</span>
              </div>
            </div>
            <div class="method-row method-row-close totals-row">
              <span class="method-label"><strong>Totais</strong></span>
              <div class="close-trio">
                <span class="total-counted"><strong>{{ brl(closeTotalCounted) }}</strong></span>
                <span class="system-total"><strong>{{ brl(closeSystemTotal) }}</strong></span>
                <span
                  class="method-diff"
                  :class="Math.abs(closeTotalCounted - closeSystemTotal) < 0.01 ? 'diff-ok' : closeTotalCounted > closeSystemTotal ? 'diff-sobra' : 'diff-falta'"
                >
                  <strong>
                    {{ Math.abs(closeTotalCounted - closeSystemTotal) < 0.01 ? 'Correto' : (closeTotalCounted > closeSystemTotal ? '+' : '') + brl(closeTotalCounted - closeSystemTotal) }}
                  </strong>
                </span>
              </div>
            </div>
          </div>

          <div class="form-field">
            <label>Observações (opcional)</label>
            <input
              v-model="closeObs"
              type="text"
              placeholder="Ex: Troco faltou R$ 2,00..."
            />
          </div>
          <button type="button" class="btn btn-primary" :disabled="saving" @click="closeRegister">
            <i class="fas fa-door-closed"></i> {{ saving ? 'Fechando…' : 'Fechar caixa' }}
          </button>
        </div>

        <!-- Histórico -->
        <div v-if="data.history.length" class="caixa-history">
          <h3>Histórico de caixas</h3>
          <div class="table-card">
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Abertura</th>
                    <th>Valor inicial</th>
                    <th>Fechamento</th>
                    <th>Valor final</th>
                    <th>Esperado</th>
                    <th>Situação</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="cr in data.history" :key="cr.id">
                    <td>{{ cr.id }}</td>
                    <td>{{ fmtDate(cr.opened_at) }}</td>
                    <td class="cell-amount">{{ brl(cr.opening_amount) }}</td>
                    <td>{{ cr.closed_at ? fmtDate(cr.closed_at) : '—' }}</td>
                    <td class="cell-amount">{{ cr.closing_amount != null ? brl(cr.closing_amount) : '—' }}</td>
                    <td class="cell-amount">{{ cr.expected_amount != null ? brl(cr.expected_amount) : '—' }}</td>
                    <td>
                      <span
                        v-if="cr.status === 'open'"
                        class="status-badge is-active"
                      >Aberto</span>
                      <span
                        v-else
                        class="status-badge"
                        :class="diffClass(cr.expected_amount, cr.closing_amount)"
                      >{{ diffLabel(cr.expected_amount, cr.closing_amount) }}</span>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}

/* Status card */
.caixa-status-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px 24px;
  border-radius: 12px;
  border: 1px solid var(--border, #e5e7eb);
  background: var(--surface, #fff);
  margin-bottom: 24px;
}
.caixa-status-card.is-open {
  border-color: #16a34a;
  background: color-mix(in srgb, #16a34a 5%, white);
}
.caixa-status-card.is-closed {
  border-color: var(--border, #e5e7eb);
}
.caixa-status-icon {
  width: 48px;
  height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
}
.is-open .caixa-status-icon {
  background: #16a34a;
  color: #fff;
}
.is-closed .caixa-status-icon {
  background: var(--surface-hover, #f3f4f6);
  color: var(--text-muted, #999);
}
.caixa-status-info {
  flex: 1;
}
.caixa-status-info h2 {
  font-size: 18px;
  font-weight: 700;
  margin: 0 0 4px;
}
.caixa-status-info p {
  margin: 0;
  font-size: 14px;
  color: var(--text-secondary, #666);
}
.caixa-status-value {
  text-align: right;
  flex-shrink: 0;
}
.caixa-status-value .label {
  display: block;
  font-size: 12px;
  color: var(--text-muted, #999);
  margin-bottom: 2px;
}
.caixa-status-value .value {
  font-size: 20px;
  font-weight: 700;
  color: var(--text, #333);
}

/* Action cards */
.caixa-action-card {
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 12px;
  padding: 24px;
  margin-bottom: 24px;
}
.caixa-action-card h3 {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 6px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.caixa-action-card > p {
  font-size: 14px;
  color: var(--text-secondary, #666);
  margin: 0 0 16px;
}

/* Method rows (shared for open/close) */
.method-rows {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 16px;
}
.method-row {
  display: flex;
  align-items: center;
  gap: 16px;
}
.method-label {
  min-width: 120px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text, #333);
}
.method-input {
  position: relative;
  display: flex;
  align-items: center;
}
.method-input .input-prefix {
  position: absolute;
  left: 10px;
  font-size: 13px;
  color: var(--text-muted, #999);
  pointer-events: none;
}
.method-input input {
  width: 160px;
  padding: 8px 10px 8px 28px;
  border: 1px solid var(--border, #d1d5db);
  border-radius: 6px;
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}
.method-input input:focus {
  outline: none;
  border-color: var(--primary, #2563eb);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.open-total {
  font-size: 15px;
  color: var(--text, #333);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.open-total strong {
  font-size: 18px;
}

/* Close section */
.method-rows-close {
  background: var(--surface-hover, #f9fafb);
  border-radius: 8px;
  padding: 16px;
}
.method-row-close {
  display: grid;
  grid-template-columns: 120px 1fr;
  gap: 8px 16px;
  align-items: center;
}
.method-row-close .method-label {
  min-width: unset;
}
.close-trio {
  display: flex;
  align-items: center;
  gap: 12px;
}
.system-total {
  font-size: 14px;
  color: var(--text-secondary, #666);
  font-variant-numeric: tabular-nums;
  min-width: 100px;
}
.method-diff {
  font-size: 13px;
  font-weight: 600;
  min-width: 80px;
}
.totals-row {
  border-top: 1px solid var(--border, #e5e7eb);
  padding-top: 10px;
  margin-top: 4px;
}
.total-counted {
  min-width: 180px;
}

/* Diff badges */
.diff-ok { color: var(--success, #16a34a); }
.diff-sobra { color: var(--primary, #2563eb); }
.diff-falta { color: var(--danger, #dc2626); }

.caixa-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.caixa-form .btn {
  align-self: flex-start;
}
.form-field {
  margin-bottom: 4px;
}
.form-field label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary, #666);
  margin-bottom: 4px;
}
.form-field input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border, #d1d5db);
  border-radius: 6px;
  font-size: 14px;
}
.form-field input:focus {
  outline: none;
  border-color: var(--primary, #2563eb);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

/* History */
.caixa-history {
  margin-top: 8px;
}
.caixa-history h3 {
  font-size: 16px;
  font-weight: 700;
  margin: 0 0 12px;
}
.cell-amount {
  text-align: right;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.status-badge.diff-ok {
  background: rgba(16, 185, 129, 0.12);
  color: var(--success, #16a34a);
}
.status-badge.diff-sobra {
  background: rgba(59, 130, 246, 0.12);
  color: var(--primary, #2563eb);
}
.status-badge.diff-falta {
  background: rgba(239, 68, 68, 0.12);
  color: var(--danger, #dc2626);
}
</style>
