<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, brdate, maskMoney, moneyToDecimal } from '@/utils/format'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { tabLabel } from '@/utils/tabs'

const data = ref(null)
const loading = ref(false)
const saving = ref(false)
const confirmClose = ref(false)

const isOpen = computed(() => !!data.value?.open)
const methods = computed(() => data.value?.payment_methods || {})

/** Comandas abertas (aviso ao abrir/fechar o caixa). */
const openTabs = computed(() => data.value?.open_tabs || [])
const openTabsLabel = computed(() =>
  openTabs.value.map((t) => tabLabel(t.number)).join(', ')
)

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
const closeInputs = ref({})
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

const movementTotals = computed(() => ({
  sangria: Number(data.value?.movement_totals?.sangria || 0),
  suprimento: Number(data.value?.movement_totals?.suprimento || 0),
  entrada: Number(data.value?.movement_totals?.entrada || 0),
}))

const movements = computed(() => data.value?.movements || [])

/** Resumo do caixa atual: esperado = abertura + vendas + sup + entradas − sang. */
const summary = computed(() => {
  const opening = Number(data.value?.open?.opening_amount || 0)
  const sales = closeSystemTotal.value
  const { sangria, suprimento, entrada } = movementTotals.value
  return {
    opening,
    sales,
    suprimento,
    sangria,
    entrada,
    expected:
      Math.round((opening + sales + suprimento + entrada - sangria) * 100) / 100,
  }
})

const expectedTotal = computed(() => summary.value.expected)

const totalDiff = computed(() =>
  Math.round((closeTotalCounted.value - expectedTotal.value) * 100) / 100
)

function diffTone(diff) {
  if (diff === null || Math.abs(diff) < 0.01) return 'ok'
  return diff > 0 ? 'warn' : 'bad'
}

/** Linhas do modal de confirmação de fechamento. */
const closeSummary = computed(() => {
  const diff = totalDiff.value
  const tone = diffTone(diff)
  const rows = [
    { label: 'Valor contado', value: brl(closeTotalCounted.value) },
    { label: 'Valor registrado', value: brl(expectedTotal.value) },
    { label: 'Diferença', value: diffLabelText(expectedTotal.value, closeTotalCounted.value), tone },
  ]
  if (openTabs.value.length) {
    rows.push({
      label: 'Comandas abertas',
      value: `${openTabs.value.length} (${openTabsLabel.value})`,
      tone: 'warn',
    })
  }
  return rows
})

const movementForm = ref({ kind: 'sangria', amount: '', obs: '' })
const savingMovement = ref(false)

function onMovementInput(event) {
  movementForm.value.amount = maskMoney(event.target.value)
}

async function submitMovement() {
  const amount = moneyToDecimal(movementForm.value.amount)
  if (amount === null || amount <= 0) {
    ElMessage.warning('Informe um valor maior que zero.')
    return
  }
  const kind = movementForm.value.kind
  savingMovement.value = true
  try {
    await api.post('/caixa/movement', {
      kind,
      amount: String(amount),
      obs: movementForm.value.obs,
    })
    movementForm.value = { kind, amount: '', obs: '' }
    await load()
    ElMessage.success(kind === 'sangria' ? 'Sangria registrada!' : 'Suprimento registrado!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    savingMovement.value = false
  }
}

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

/** Enter pula para o próximo campo de valor do fechamento (na última, vai p/ obs). */
function focusNextClose(mid) {
  const order = Object.keys(methods.value)
  const nextKey = order[order.indexOf(String(mid)) + 1]
  if (nextKey && closeInputs.value[nextKey]) {
    closeInputs.value[nextKey].focus()
    return
  }
  document.getElementById('close_obs')?.focus()
}

async function openRegister() {
  const details = {}
  for (const [mid, raw] of Object.entries(openDetails.value)) {
    // campo vazio conta como 0 → permite abrir o caixa com 00,00
    const parsed = moneyToDecimal(raw)
    const value = parsed === null ? 0 : parsed
    if (value < 0) {
      ElMessage.warning(`Informe um valor válido para ${openMethods.value[mid]}.`)
      return
    }
    details[mid] = String(value)
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

function closePayload() {
  const details = {}
  let total = 0
  for (const [mid, raw] of Object.entries(closeDetails.value)) {
    const v = moneyToDecimal(raw)
    if (v === null || v < 0) {
      return { error: `Informe um valor válido para ${methods.value[mid]}.` }
    }
    details[mid] = String(v)
    total += v
  }
  if (total <= 0) {
    return { error: 'O valor total contado deve ser maior que zero.' }
  }
  return { details }
}

function askClose() {
  const { error } = closePayload()
  if (error) {
    ElMessage.warning(error)
    return
  }
  confirmClose.value = true
}

async function closeRegister() {
  const { details, error } = closePayload()
  confirmClose.value = false
  if (error) {
    ElMessage.warning(error)
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

/** Texto da diferença com significado: "R$ 6,00 faltando". */
function diffText(counted, expected) {
  if (counted === null || counted === undefined) return ''
  if (expected === null || expected === undefined) return ''
  const diff = Math.round((counted - expected) * 100) / 100
  if (Math.abs(diff) < 0.01) return '✓ Correto'
  return diff > 0 ? `${brl(diff)} sobrando` : `${brl(Math.abs(diff))} faltando`
}

function methodDiffLabel(mid) {
  const systemVal = systemTotals.value[mid]?.total || 0
  return diffText(moneyToDecimal(closeDetails.value[mid]), systemVal)
}

function fmtDateTime(iso) {
  if (!iso) return '—'
  const [date, time] = String(iso).split(' ')
  if (!time) return brdate(iso)
  return `${brdate(date)} às ${time.slice(0, 5)}`
}

function diffClass(expected, closing) {
  if (expected == null || closing == null) return ''
  const diff = closing - expected
  if (Math.abs(diff) < 0.01) return 'diff-ok'
  return diff > 0 ? 'diff-sobra' : 'diff-falta'
}

function diffLabelText(expected, closing) {
  if (expected == null || closing == null) return ''
  const diff = Math.round((closing - expected) * 100) / 100
  if (Math.abs(diff) < 0.01) return '✓ Correto'
  return diff > 0 ? `${brl(diff)} sobrando` : `${brl(Math.abs(diff))} faltando`
}

function diffLabel(expected, closing) {
  return diffLabelText(expected, closing)
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
            <h2>{{ isOpen ? 'Caixa aberto' : 'Caixa fechado' }}</h2>
            <p v-if="data.open">
              Aberto por <strong>{{ data.open.opened_by }}</strong> ·
              {{ fmtDateTime(data.open.opened_at) }}
            </p>
            <p v-else-if="data.last_closed">
              Último fechamento: {{ fmtDateTime(data.last_closed.closed_at) }}
            </p>
            <p v-else>Nenhum caixa registrado ainda.</p>
          </div>
          <div v-if="data.open" class="caixa-status-value">
            <span class="label">Saldo inicial</span>
            <span class="value">{{ brl(data.open.opening_amount) }}</span>
          </div>
        </div>

        <!-- Resumo do caixa atual -->
        <div v-if="isOpen" class="stats-row caixa-summary">
          <div class="stat-card">
            <div class="stat-top">
              <span class="icon-tile"><i class="fas fa-wallet"></i></span>
              <span class="stat-label">Saldo inicial</span>
            </div>
            <span class="stat-value">{{ brl(summary.opening) }}</span>
          </div>
          <div class="stat-card">
            <div class="stat-top">
              <span class="icon-tile"><i class="fas fa-cash-register"></i></span>
              <span class="stat-label">Vendas</span>
            </div>
            <span class="stat-value">{{ brl(summary.sales) }}</span>
          </div>
          <div v-if="summary.suprimento > 0" class="stat-card">
            <div class="stat-top">
              <span class="icon-tile"><i class="fas fa-arrow-down"></i></span>
              <span class="stat-label">Entradas</span>
            </div>
            <span class="stat-value">{{ brl(summary.suprimento) }}</span>
          </div>
          <div v-if="summary.entrada > 0" class="stat-card">
            <div class="stat-top">
              <span class="icon-tile"><i class="fas fa-hand-holding-usd"></i></span>
              <span class="stat-label">Recebimentos</span>
            </div>
            <span class="stat-value">{{ brl(summary.entrada) }}</span>
          </div>
          <div v-if="summary.sangria > 0" class="stat-card">
            <div class="stat-top">
              <span class="icon-tile"><i class="fas fa-arrow-up"></i></span>
              <span class="stat-label">Saídas</span>
            </div>
            <span class="stat-value">{{ brl(summary.sangria) }}</span>
          </div>
          <div class="stat-card stat-card-highlight">
            <div class="stat-top">
              <span class="icon-tile"><i class="fas fa-balance-scale"></i></span>
              <span class="stat-label">Saldo esperado</span>
            </div>
            <span class="stat-value">{{ brl(summary.expected) }}</span>
          </div>
        </div>

        <!-- Sangria / suprimento -->
        <div v-if="isOpen" class="caixa-action-card">
          <h3><i class="fas fa-exchange-alt"></i> Movimentações</h3>
          <p>Registre sangrias (−) e suprimentos (+) com motivo. Entram no saldo esperado.</p>

          <form class="movement-form" @submit.prevent="submitMovement">
            <div class="filter-segmented" role="group" aria-label="Tipo de movimentação">
              <button
                type="button"
                :class="{ 'is-active': movementForm.kind === 'sangria' }"
                @click="movementForm.kind = 'sangria'"
              >
                <i class="fas fa-arrow-up"></i> Sangria
              </button>
              <button
                type="button"
                :class="{ 'is-active': movementForm.kind === 'suprimento' }"
                @click="movementForm.kind = 'suprimento'"
              >
                <i class="fas fa-arrow-down"></i> Suprimento
              </button>
            </div>
            <div class="method-input">
              <span class="input-prefix">R$</span>
              <input
                :value="movementForm.amount"
                type="text"
                placeholder="0,00"
                inputmode="decimal"
                aria-label="Valor da movimentação"
                @input="onMovementInput"
              />
            </div>
            <input
              v-model="movementForm.obs"
              type="text"
              class="movement-obs"
              placeholder="Motivo (ex: pagamento fornecedor...)"
              aria-label="Motivo da movimentação"
            />
            <button type="submit" class="btn btn-primary" :disabled="savingMovement">
              <i class="fas fa-check"></i> {{ savingMovement ? 'Registrando…' : 'Registrar' }}
            </button>
          </form>

          <div v-if="movements.length" class="movement-list">
            <div v-for="m in movements" :key="m.id" class="movement-row">
              <span
                class="status-badge"
                :class="m.kind === 'sangria' ? 'is-off' : 'is-ok'"
              >{{
                m.kind === 'sangria'
                  ? '− Sangria'
                  : m.kind === 'entrada'
                    ? '+ Entrada'
                    : '+ Suprimento'
              }}</span>
              <strong>{{ brl(m.amount) }}</strong>
              <span class="movement-meta">
                {{ m.obs || 'Sem motivo' }} · {{ m.created_by }}
              </span>
            </div>
          </div>
        </div>

        <!-- Abrir Caixa -->
        <div v-if="!isOpen" class="caixa-action-card">
          <h3><i class="fas fa-door-open"></i> Abrir caixa</h3>
          <p>Informe o valor em dinheiro e PIX que estão no caixa na abertura.</p>
          <div v-if="openTabs.length" class="caixa-tabs-warning">
            <i class="fas fa-triangle-exclamation"></i>
            <span>
              Há {{ openTabs.length }} comanda(s) aberta(s) (<strong>{{ openTabsLabel }}</strong>).
              Elas continuam abertas e continuarão contando nas vendas.
            </span>
          </div>
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
          <h3><i class="fas fa-door-closed"></i> Fechar caixa</h3>
          <p>Confira o valor contado de cada forma de pagamento com o total registrado pelo sistema.</p>
          <div v-if="openTabs.length" class="caixa-tabs-warning">
            <i class="fas fa-triangle-exclamation"></i>
            <span>
              Atenção: {{ openTabs.length }} comanda(s) em aberto (<strong>{{ openTabsLabel }}</strong>).
              Elas continuarão abertas após fechar o caixa.
            </span>
          </div>

          <div class="close-table" role="table" aria-label="Conferência do caixa">
            <div class="close-table-head" role="row">
              <span role="columnheader">Forma de pagamento</span>
              <span role="columnheader">Valor contado</span>
              <span role="columnheader">Registrado</span>
              <span role="columnheader">Diferença</span>
            </div>
            <div v-for="(name, mid) in methods" :key="mid" class="close-table-row" role="row">
              <span class="method-label" role="cell">{{ name }}</span>
              <div class="method-input" role="cell">
                <span class="input-prefix">R$</span>
                <input
                  :value="closeDetails[mid] || ''"
                  :ref="(el) => (closeInputs[mid] = el)"
                  type="text"
                  placeholder="0,00"
                  inputmode="decimal"
                  :aria-label="`Valor contado em ${name}`"
                  @input="onCloseInput(mid, $event)"
                  @keydown.enter.prevent="focusNextClose(mid)"
                />
              </div>
              <span class="system-total" role="cell">{{ brl(systemTotals[mid]?.total || 0) }}</span>
              <span
                class="method-diff"
                role="cell"
                :class="methodDiffClass(mid)"
              >{{ methodDiffLabel(mid) }}</span>
            </div>
            <div class="close-table-row totals-row" role="row">
              <span class="method-label" role="cell"><strong>Totais</strong></span>
              <span class="total-counted" role="cell">
                <strong>Contado: {{ brl(closeTotalCounted) }}</strong>
              </span>
              <span class="system-total" role="cell">
                <strong>Registrado: {{ brl(expectedTotal) }}</strong>
              </span>
              <span
                class="method-diff"
                role="cell"
                :class="diffTone(totalDiff) === 'ok' ? 'diff-ok' : diffTone(totalDiff) === 'warn' ? 'diff-sobra' : 'diff-falta'"
              >
                <strong>Diferença: {{ diffLabelText(expectedTotal, closeTotalCounted) }}</strong>
              </span>
            </div>
          </div>

          <div class="form-field">
            <label for="close_obs">Observações (opcional)</label>
            <input
              id="close_obs"
              v-model="closeObs"
              type="text"
              placeholder="Ex: troco para amanhã, justificativa de diferença..."
            />
          </div>
          <div class="close-actions">
            <button type="button" class="btn-brand" :disabled="saving" @click="askClose">
              <i class="fas fa-door-closed"></i> {{ saving ? 'Fechando…' : 'Fechar caixa' }}
            </button>
          </div>
        </div>

        <ConfirmDialog
          v-if="confirmClose"
          title="Fechar este caixa?"
          message="Confira os valores informados antes de continuar."
          confirm-label="Fechar caixa"
          :summary="closeSummary"
          @confirm="closeRegister"
          @cancel="confirmClose = false"
        />

        <!-- Histórico -->
        <div v-if="data.history.length" class="caixa-history">
          <div class="table-card">
            <div class="table-card-head">
              <h2>Histórico de caixas</h2>
            </div>
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
                    <td>{{ fmtDateTime(cr.opened_at) }}</td>
                    <td class="cell-amount">{{ brl(cr.opening_amount) }}</td>
                    <td>{{ cr.closed_at ? fmtDateTime(cr.closed_at) : '—' }}</td>
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
  padding: 18px 22px;
  border-radius: var(--radius-lg);
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow-xs);
  margin-bottom: 20px;
}
.caixa-status-card.is-open {
  border-color: rgba(22, 163, 74, 0.35);
  background: rgba(22, 163, 74, 0.06);
}
.caixa-status-icon {
  width: 44px;
  height: 44px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  flex-shrink: 0;
}
.is-open .caixa-status-icon {
  background: rgba(22, 163, 74, 0.14);
  color: var(--success);
}
.is-closed .caixa-status-icon {
  background: var(--surface-hover);
  color: var(--text-muted);
}
.caixa-status-info {
  flex: 1;
  min-width: 0;
}
.caixa-status-info h2 {
  font-size: 17px;
  font-weight: 800;
  letter-spacing: -0.3px;
  margin: 0 0 4px;
}
.is-open .caixa-status-info h2 {
  color: var(--success);
}
.caixa-status-info p {
  margin: 0;
  font-size: 13px;
  color: var(--text-secondary);
}
.caixa-status-value {
  text-align: right;
  flex-shrink: 0;
}
.caixa-status-value .label {
  display: block;
  font-size: 12px;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: 2px;
}
.caixa-status-value .value {
  font-size: 22px;
  font-weight: 800;
  letter-spacing: -0.4px;
  color: var(--text);
  font-variant-numeric: tabular-nums;
}

/* Resumo do caixa atual (reusa stat-card de Vendas) */
.caixa-summary {
  margin-bottom: 20px;
}

.caixa-summary .stat-card-highlight {
  background: rgba(99, 102, 241, 0.05);
}

.caixa-summary .stat-card-highlight .stat-value {
  color: var(--primary-hover);
}

/* Action cards */
.caixa-action-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-xs);
  padding: 22px 24px;
  margin-bottom: 20px;
}
.caixa-action-card h3 {
  font-size: 16px;
  font-weight: 800;
  letter-spacing: -0.3px;
  margin: 0 0 6px;
  display: flex;
  align-items: center;
  gap: 10px;
}
.caixa-action-card h3 i {
  color: var(--primary);
}
.caixa-action-card > p {
  font-size: 14px;
  color: var(--text-secondary);
  margin: 0 0 18px;
}
.caixa-tabs-warning {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 14px;
  margin: 0 0 16px;
  border: 1px solid #f59e0b;
  background: #fffbeb;
  border-radius: var(--brand-radius-sm, 8px);
  font-size: 13px;
  color: #92400e;
  line-height: 1.5;
}
.caixa-tabs-warning i {
  margin-top: 2px;
  color: #d97706;
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
  color: var(--text);
}
.close-table .method-label {
  min-width: 0;
}

.close-actions {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}
.method-input {
  position: relative;
  display: flex;
  align-items: center;
}
.method-input .input-prefix {
  position: absolute;
  left: 12px;
  font-size: 13px;
  color: var(--text-muted);
  pointer-events: none;
}
.method-input input {
  width: 170px;
  max-width: 100%;
  padding: 8px 12px 8px 32px;
  border: 1px solid var(--border);
  border-radius: var(--brand-radius-sm);
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
.method-input input::placeholder {
  color: var(--text-muted);
  font-weight: 400;
}
.method-input input:hover {
  border-color: var(--border-strong);
}
.method-input input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: var(--brand-input-ring);
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

/* Close section: tabela de conferência */
.close-table {
  border: 1px solid var(--border);
  border-radius: var(--brand-radius-md);
  overflow: hidden;
  margin-bottom: 18px;
}

.close-table-head,
.close-table-row {
  display: grid;
  grid-template-columns: 150px minmax(150px, 190px) minmax(110px, 1fr) minmax(140px, 1fr);
  gap: 16px;
  align-items: center;
  padding: 7px 18px;
}

.close-table-head {
  background: var(--surface-hover);
  color: var(--text-secondary);
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
}

.close-table-row + .close-table-row {
  border-top: 1px solid var(--border);
}

.close-table-row:hover {
  background: var(--surface-hover);
}

.system-total {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

.method-diff {
  font-size: 13px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.totals-row {
  background: var(--surface-hover);
  border-top: 2px solid var(--border-strong);
}

.totals-row:hover {
  background: var(--surface-hover);
}

.total-counted {
  font-variant-numeric: tabular-nums;
}

/* Diff: verde = correto, vermelho = faltando, âmbar = sobrando */
.diff-ok { color: var(--success); }
.diff-sobra { color: var(--warning); }
.diff-falta { color: var(--danger); }

.caixa-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.caixa-form .btn {
  align-self: flex-start;
}

/* Sangria / suprimento */
.movement-form {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

.movement-form .method-input input {
  width: 140px;
}

.movement-obs {
  flex: 1;
  min-width: 180px;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--brand-radius-sm);
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
}

.movement-obs::placeholder {
  color: var(--text-muted);
}

.movement-obs:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: var(--brand-input-ring);
}

.movement-list {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--border);
  border-radius: var(--brand-radius-md);
  overflow: hidden;
}

.movement-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
}

.movement-row + .movement-row {
  border-top: 1px solid var(--border);
}

.movement-row strong {
  font-variant-numeric: tabular-nums;
}

.movement-meta {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted);
  text-align: right;
}
.form-field {
  margin-bottom: 4px;
}
.form-field label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 6px;
}
.form-field input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--brand-radius-sm);
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
.form-field input::placeholder {
  color: var(--text-muted);
}
.form-field input:hover {
  border-color: var(--border-strong);
}
.form-field input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: var(--brand-input-ring);
}

/* History */
.caixa-history {
  margin-top: 4px;
}
.caixa-history .table-card {
  margin-bottom: 0;
}
.caixa-history tbody tr:hover {
  background: var(--surface-hover);
}
.cell-amount {
  text-align: right;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
.status-badge {
  display: inline-block;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
  padding: 5px 11px;
  border-radius: 999px;
  white-space: nowrap;
  background: var(--surface-hover);
  color: var(--text-secondary);
}
.status-badge.is-active {
  background: rgba(22, 163, 74, 0.12);
  color: var(--success);
}
.status-badge.diff-ok {
  background: rgba(22, 163, 74, 0.12);
  color: var(--success);
}
.status-badge.diff-sobra {
  background: rgba(217, 119, 6, 0.12);
  color: var(--warning);
}
.status-badge.diff-falta {
  background: rgba(220, 38, 38, 0.12);
  color: var(--danger);
}
</style>
