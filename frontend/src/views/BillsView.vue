<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import JsBarcode from 'jsbarcode'
import qrcode from 'qrcode-generator'
import { api } from '@/api/client'
import { brl, brdate, brdateShort, maskMoney, moneyToDecimal } from '@/utils/format'
import AppShell from '@/components/AppShell.vue'

const data = ref(null)
const loading = ref(false)
const saving = ref(false)
const showModal = ref(false)
const editing = ref(null)

const search = ref('')
const filterStatus = ref('Todas')
const openMenu = ref(null)

function toggleMenu(id) {
  openMenu.value = openMenu.value === id ? null : id
}

function closeMenus() {
  openMenu.value = null
}

const detailsModal = ref(false)
const detailsBill = ref(null)

function openDetails(bill) {
  detailsBill.value = bill
  detailsModal.value = true
}

function rowClick(bill, event) {
  if (event.target.closest('a, button, select, input, .dropdown-panel')) return
  openDetails(bill)
}

// ---------- Autofill a partir do código de barras ----------
function checkDvGeral(code) {
  if (code.length !== 44) return false
  const dvPos = code[0] === '8' ? 3 : 4
  const base = code.slice(0, dvPos) + code.slice(dvPos + 1)
  let sum = 0
  for (let i = 0; i < base.length; i++) {
    sum += parseInt(base[base.length - 1 - i], 10) * (i % 8 + 2)
  }
  const resto = sum % 11
  const dv = resto === 0 || resto === 1 ? 0 : 11 - resto
  return dv === parseInt(code[dvPos], 10)
}

function decodeBarcode(raw) {
  const code = toBarcode(raw)
  if (!code || !checkDvGeral(code)) return null
  const result = { value: null, vencimento: null }

  if (code[0] === '8') {
    if (code[2] === '6' || code[2] === '8') {
      result.value = parseInt(code.slice(4, 15), 10) / 100
    }
    const y = parseInt(code.slice(19, 23), 10)
    const m = parseInt(code.slice(23, 25), 10)
    const d = parseInt(code.slice(25, 27), 10)
    if (y >= 1 && m >= 1 && m <= 12 && d >= 1 && d <= 31) {
      result.vencimento =
        String(y).padStart(4, '0') + '-' + String(m).padStart(2, '0') + '-' + String(d).padStart(2, '0')
    }
  } else {
    result.value = parseInt(code.slice(9, 19), 10) / 100
    const factor = parseInt(code.slice(5, 9), 10)
    if (factor >= 1000 && factor <= 9999) {
      const ms = Date.UTC(1997, 9, 7) + (factor - 1000) * 86400000
      result.vencimento = new Date(ms).toISOString().slice(0, 10)
    }
  }
  return result
}

function shouldAutofillDate(isoDate) {
  if (!isoDate) return false
  const d = new Date(isoDate + 'T00:00:00')
  if (Number.isNaN(d.getTime())) return false
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const limit = new Date(today)
  limit.setDate(limit.getDate() - 7)
  return d >= limit
}

function onBarcodeInput() {
  const decoded = decodeBarcode(form.value.bar_code)
  if (!decoded) return
  if (decoded.value !== null && !form.value.value) {
    form.value.value = maskMoney(String(Math.round(decoded.value * 100)))
  }
  if (shouldAutofillDate(decoded.vencimento) && !form.value.due_date) {
    form.value.due_date = decoded.vencimento
  }
}

const form = ref({
  value: '',
  due_date: '',
  reference: '',
  suplyer: '',
  account_id: '',
  pix_key: '',
  obs: '',
  bar_code: '',
  status: false,
})

const STATUS_LABELS = {
  paga: 'Paga',
  vencida: 'Vencida',
  hoje: 'Vence hoje',
  amanha: 'Vence amanhã',
  semvenc: 'Sem vencimento',
  pendente: 'Pendente',
}

const filteredBills = computed(() => {
  if (!data.value) return []
  const term = search.value.trim().toLowerCase()
  return data.value.bills.filter((bill) => {
    if (filterStatus.value !== 'Todas') {
      const paid = bill.status === 'paga'
      if (filterStatus.value === 'Pagas' && !paid) return false
      if (filterStatus.value === 'NaoPagas' && paid) return false
      if (filterStatus.value === 'Vencidas' && bill.status !== 'vencida') return false
      if (filterStatus.value === 'Hoje' && bill.status !== 'hoje') return false
      if (filterStatus.value === 'AVencer' && ['paga', 'vencida'].includes(bill.status)) return false
    }
    if (!term) return true
    const haystack = [
      bill.reference,
      bill.suplyer,
      bill.category,
      bill.bill_type,
      bill.obs,
      bill.bar_code,
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase()
    return haystack.includes(term)
  })
})

function openNew() {
  editing.value = null
  form.value = {
    value: '',
    due_date: '',
    reference: '',
    suplyer: '',
    account_id: '',
    pix_key: '',
    obs: '',
    bar_code: '',
    status: false,
  }
  showModal.value = true
}

function openEdit(bill) {
  editing.value = bill
  form.value = {
    value: maskMoney(String(Math.round(bill.value * 100))),
    due_date: bill.due_date || '',
    reference: bill.reference || '',
    suplyer: bill.suplyer || '',
    account_id: bill.account_id ? String(bill.account_id) : '',
    pix_key: bill.pix_key || '',
    obs: bill.obs || '',
    bar_code: bill.bar_code || '',
    status: bill.status === 'paga',
  }
  showModal.value = true
}

function mask(event) {
  form.value.value = maskMoney(event.target.value)
}

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/bills')
  } finally {
    loading.value = false
  }
}

async function submit() {
  const value = moneyToDecimal(form.value.value)
  if (!form.value.due_date || value === null || value <= 0) {
    ElMessage.warning('Informe um valor e um vencimento válidos.')
    return
  }
  saving.value = true
  try {
    const payload = {
      value: String(value),
      due_date: form.value.due_date,
      reference: form.value.reference,
      suplyer: form.value.suplyer,
      account_id: form.value.account_id || null,
      pix_key: form.value.pix_key,
      obs: form.value.obs,
      bar_code: form.value.bar_code,
      status: form.value.status,
    }
    if (editing.value) {
      data.value = await api.put(`/bills/${editing.value.id}`, payload)
    } else {
      data.value = await api.post('/bills', payload)
    }
    showModal.value = false
    ElMessage.success(editing.value ? 'Conta atualizada!' : 'Conta cadastrada!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function payBill(bill) {
  openPay(bill)
}

async function removeBill(bill) {
  if (!window.confirm('Excluir esta conta?')) return
  try {
    data.value = await api.del(`/bills/${bill.id}`)
    ElMessage.success('Conta excluída.')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

const payModal = ref(false)
const payingBill = ref(null)
const activePayTab = ref('barcode')
const barcodeEmpty = ref(false)
const pixCopyCola = ref('')
const copyFeedback = ref('')

const barcodeSvg = ref(null)
const pixQrSvg = ref(null)

const payBarcode = computed(() => payingBill.value?.bar_code || '')
const payPixKey = computed(() => payingBill.value?.pix_key || '')
const payPixPayload = computed(() => payingBill.value?.pix_payload || '')
const payPixImage = computed(() => payingBill.value?.pix_image || '')
const hasPix = computed(() => !!(payPixKey.value || payPixPayload.value || payPixImage.value))
const hasBarcode = computed(() => !!payBarcode.value)

const linhaDigitavel = computed(() => {
  const d = digitsOnly(payBarcode.value)
  if (d.length === 48) return d.match(/.{12}/g).join(' ')
  if (d.length === 47) {
    return [
      d.slice(0, 5) + '.' + d.slice(5, 10),
      d.slice(10, 15) + '.' + d.slice(15, 21),
      d.slice(21, 26) + '.' + d.slice(26, 32),
      d.slice(32),
    ].join(' ')
  }
  return d || '—'
})

function digitsOnly(text) {
  return String(text || '').replace(/\D/g, '')
}

function toBarcode(raw) {
  const digits = digitsOnly(raw)
  if (digits.length === 47) {
    return (
      digits.slice(0, 4) + digits[32] + digits.slice(33) +
      digits.slice(4, 9) + digits.slice(10, 20) + digits.slice(21, 31)
    )
  }
  if (digits.length === 48) {
    return (
      digits.slice(0, 11) + digits.slice(12, 23) + digits.slice(24, 35) + digits.slice(36, 47)
    )
  }
  if (digits.length === 44) return digits
  return null
}

function renderPayBarcode() {
  const svg = barcodeSvg.value
  if (!svg) return
  svg.innerHTML = ''
  const digits = digitsOnly(payBarcode.value)
  const normalized = toBarcode(digits)
  const barcode44 = normalized || (digits.length === 44 ? digits : '')
  if (!barcode44) {
    barcodeEmpty.value = true
    return
  }
  barcodeEmpty.value = false
  const totalModules = 425
  const parent = svg.parentElement
  const maxWidth = parent && parent.clientWidth ? parent.clientWidth - 24 : window.innerWidth - 80
  const module = Math.max(2, Math.min(Math.floor(maxWidth / totalModules), 6))
  JsBarcode(svg, barcode44, {
    format: 'ITF',
    displayValue: false,
    width: module,
    height: Math.round(module * 47.5),
    margin: module * 10,
  })
}

function crc16Pix(text) {
  let crc = 0xffff
  for (let i = 0; i < text.length; i++) {
    crc ^= text.charCodeAt(i) << 8
    for (let j = 0; j < 8; j++) {
      crc = crc & 0x8000 ? ((crc << 1) ^ 0x1021) & 0xffff : (crc << 1) & 0xffff
    }
  }
  return crc.toString(16).toUpperCase().padStart(4, '0')
}

function emvField(id, value) {
  return id + String(value.length).padStart(2, '0') + value
}

function ascii(text) {
  return String(text)
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^A-Za-z0-9 ]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
    .toUpperCase()
}

function randomTxid() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
  let out = ''
  for (let i = 0; i < 8; i++) out += chars[Math.floor(Math.random() * chars.length)]
  return out
}

function buildPixPayload(key, amount, name, city) {
  const merchantInfo = emvField('00', 'br.gov.bcb.pix') + emvField('01', key)
  let payload =
    emvField('00', '01') +
    emvField('26', merchantInfo) +
    emvField('52', '0000') +
    emvField('53', '986') +
    emvField('54', amount.toFixed(2)) +
    emvField('58', 'BR') +
    emvField('59', name) +
    emvField('60', city) +
    emvField('62', emvField('05', randomTxid()))
  return payload + '6304' + crc16Pix(payload + '6304')
}

function renderPixQr(text) {
  const svg = pixQrSvg.value
  if (!svg) return
  svg.innerHTML = ''
  const qr = qrcode(0, 'M')
  qr.addData(text)
  qr.make()
  svg.innerHTML = qr.createSvgTag({ cellSize: 8, margin: 2, scalable: true })
}

function renderPix() {
  const value = payingBill.value?.value
  if (payPixImage.value) {
    pixCopyCola.value = payPixPayload.value
    return
  }
  if (payPixPayload.value) {
    pixCopyCola.value = payPixPayload.value
    renderPixQr(payPixPayload.value)
    return
  }
  if (payPixKey.value && value && value > 0) {
    const name = (ascii(payingBill.value?.suplyer) || 'RECEBEDOR').slice(0, 25)
    const payload = buildPixPayload(payPixKey.value, value, name, 'BRASILIA')
    pixCopyCola.value = payload
    renderPixQr(payload)
    return
  }
  pixCopyCola.value = ''
}

function openPay(bill) {
  payingBill.value = bill
  activePayTab.value = hasPix.value ? 'pix' : 'barcode'
  copyFeedback.value = ''
  payModal.value = true
  nextTick(() => {
    renderPayBarcode()
    if (hasPix.value) renderPix()
  })
}

function switchPayTab(tab) {
  activePayTab.value = tab
}

async function copyText(text, label) {
  if (!text) return
  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text)
    } else {
      const input = document.createElement('textarea')
      input.value = text
      input.style.position = 'fixed'
      input.style.opacity = '0'
      document.body.appendChild(input)
      input.select()
      document.execCommand('copy')
      document.body.removeChild(input)
    }
    copyFeedback.value = label
    setTimeout(() => {
      if (copyFeedback.value === label) copyFeedback.value = ''
    }, 1500)
  } catch {
    ElMessage.error('Não foi possível copiar.')
  }
}

async function confirmPay() {
  if (!payingBill.value) return
  if (!window.confirm('Confirmar o pagamento desta conta?')) return
  try {
    data.value = await api.post(`/bills/${payingBill.value.id}/pay`)
    payModal.value = false
    ElMessage.success('Conta marcada como paga!')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

onMounted(() => {
  load()
  document.addEventListener('click', closeMenus)
})
</script>

<template>
  <AppShell>
    <div class="dashboard">
      <div class="page-header">
        <div>
          <h1 class="page-title">Contas</h1>
          <p class="page-subtitle">Acompanhe boletos, fornecedores e despesas fixas.</p>
        </div>
        <button type="button" class="btn btn-primary" @click="openNew">
          <i class="fas fa-plus"></i> Nova conta
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="stats-row">
          <div class="stat-card">
            <span class="stat-label">Total em aberto</span>
            <span class="stat-value">{{ brl(data.stats.open) }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Vencidas</span>
            <span class="stat-value" :class="{ 'stat-value-danger': data.stats.overdue > 0 }">
              {{ brl(data.stats.overdue) }}
            </span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Pagas este mês</span>
            <span class="stat-value stat-value-success">{{ brl(data.stats.paid_month) }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Total de contas</span>
            <span class="stat-value">{{ data.stats.total }}</span>
          </div>
        </div>

        <div class="toolbar">
          <div class="search">
            <i class="fas fa-search"></i>
            <input
              v-model="search"
              type="text"
              placeholder="Buscar por fornecedor, descrição..."
              aria-label="Buscar contas"
            />
          </div>
          <div class="filter-group">
            <div class="filter-wrap">
              <i class="fas fa-filter"></i>
              <select v-model="filterStatus" class="filter-select" aria-label="Filtrar por status">
                <option value="Todas">Todos os status</option>
                <option value="NaoPagas">Não pagas</option>
                <option value="Vencidas">Vencidas</option>
                <option value="AVencer">À vencer</option>
                <option value="Hoje">Vence hoje</option>
                <option value="Pagas">Pagas</option>
              </select>
            </div>
          </div>
        </div>

        <div class="table-card">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>Descrição</th>
                  <th>Fornecedor</th>
                  <th>Vencimento</th>
                  <th class="th-amount">Valor</th>
                  <th class="th-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="bill in filteredBills" :key="bill.id" class="account-row" @click="rowClick(bill, $event)">
                  <td>
                    <span class="status" :class="'status-' + bill.status">
                      <span class="status-dot"></span>
                      {{ STATUS_LABELS[bill.status] || 'Pendente' }}
                    </span>
                  </td>
                  <td>
                    <span class="cell-title">{{ bill.reference || 'Sem descrição' }}</span>
                    <span v-if="bill.category || bill.bill_type" class="cell-sub">
                      {{ bill.category || bill.bill_type }}
                    </span>
                  </td>
                  <td class="cell-supplier">{{ bill.suplyer || '—' }}</td>
                  <td>
                    <span v-if="bill.due_date" class="cell-date" :class="{ 'cell-date-overdue': bill.status === 'vencida' }">
                      {{ brdateShort(bill.due_date) }}
                    </span>
                    <span v-else class="cell-date muted-text">—</span>
                    <span v-if="bill.status === 'vencida' && bill.overdue_days" class="cell-sub cell-overdue">
                      há {{ -bill.overdue_days }} dias
                    </span>
                    <span v-else-if="bill.status === 'paga' && bill.payday" class="cell-sub">
                      Pago em {{ brdateShort(bill.payday) }}
                    </span>
                  </td>
                  <td class="cell-amount">{{ brl(bill.value) }}</td>
                  <td class="cell-actions">
                    <div class="dropdown">
                      <button
                        type="button"
                        class="icon-btn row-menu-btn"
                        aria-haspopup="true"
                        aria-expanded="false"
                        aria-label="Ações da conta"
                        @click.stop="toggleMenu(bill.id)"
                      >
                        <i class="fas fa-ellipsis-h"></i>
                      </button>
                      <div class="dropdown-panel" v-show="openMenu === bill.id">
                        <button type="button" class="dropdown-item" @click="openDetails(bill)">
                          <i class="fas fa-eye"></i> Ver detalhes
                        </button>
                        <button type="button" class="dropdown-item" @click="openEdit(bill)">
                          <i class="fas fa-pen"></i> Editar
                        </button>
                        <button v-if="bill.status !== 'paga'" type="button" class="dropdown-item" @click="payBill(bill)">
                          <i class="fas fa-check-circle"></i> Marcar como paga
                        </button>
                        <button type="button" class="dropdown-item is-danger" @click="removeBill(bill)">
                          <i class="fas fa-trash"></i> Excluir
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr v-if="!filteredBills.length" class="empty-row">
                  <td colspan="6" class="empty-state">
                    <i class="fas fa-receipt"></i>
                    <h3>Nenhuma conta encontrada</h3>
                    <p v-if="data.bills.length">Experimente alterar os filtros ou termos da busca.</p>
                    <p v-else>Você ainda não possui contas cadastradas.</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>

    <div class="modal" :class="{ 'is-open': showModal }">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ editing ? 'Editar conta' : 'Cadastrar Nova Conta' }}</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="showModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="submit">
          <div class="form-field">
            <label for="bill_barcode">Código de barras</label>
            <input
              id="bill_barcode"
              v-model="form.bar_code"
              type="text"
              placeholder="Número do documento"
              @input="onBarcodeInput"
            />
          </div>

          <div class="form-grid">
            <div class="form-field">
              <label for="bill_value">Valor</label>
              <input
                id="bill_value"
                :value="form.value"
                type="text"
                placeholder="R$ 0,00"
                inputmode="decimal"
                required
                @input="mask"
              />
            </div>
            <div class="form-field">
              <label for="bill_due">Vencimento</label>
              <input id="bill_due" v-model="form.due_date" type="date" required />
            </div>
          </div>

          <div class="form-field">
            <label for="bill_reference">Referente a</label>
            <input id="bill_reference" v-model="form.reference" type="text" placeholder="Ex: Energia de agosto" />
          </div>

          <div class="form-grid">
            <div class="form-field">
              <label for="bill_suplyer">Fornecedor</label>
              <input id="bill_suplyer" v-model="form.suplyer" type="text" placeholder="Ex: CEMIG" />
            </div>
            <div class="form-field">
              <label for="bill_category">Categoria</label>
              <select id="bill_category" v-model="form.account_id">
                <option value="">Selecione uma categoria</option>
                <optgroup v-for="group in data?.account_groups || []" :key="group.label" :label="group.label">
                  <option v-for="account in group.accounts" :key="account.id" :value="String(account.id)">
                    {{ account.name }}
                  </option>
                </optgroup>
              </select>
            </div>
          </div>

          <div class="form-grid">
            <div class="form-field">
              <label for="bill_pix">Chave PIX (opcional)</label>
              <input id="bill_pix" v-model="form.pix_key" type="text" placeholder="CPF, CNPJ, e-mail, telefone ou aleatória" />
            </div>
            <div class="form-field">
              <label for="bill_obs">Observações</label>
              <input id="bill_obs" v-model="form.obs" type="text" placeholder="Observações opcionais" />
            </div>
          </div>

          <label class="form-check">
            <input id="bill_status" v-model="form.status" type="checkbox" />
            <span>Conta já paga</span>
          </label>

          <div class="modal-footer">
            <button type="button" class="btn btn-ghost modal-cancel" @click="showModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Salvar conta' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <div class="modal" :class="{ 'is-open': detailsModal }">
      <div class="modal-content modal-content-sm">
        <div class="modal-header">
          <h2>Detalhes da conta</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="detailsModal = false">&times;</button>
        </div>
        <div class="modal-details">
          <div class="modal-details-item">
            <span class="label">Status:</span>
            <span>{{ detailsBill ? STATUS_LABELS[detailsBill.status] || 'Pendente' : '—' }}</span>
          </div>
          <div class="modal-details-item">
            <span class="label">Referente a:</span>
            <span>{{ detailsBill?.reference || '—' }}</span>
          </div>
          <div class="modal-details-item">
            <span class="label">Fornecedor:</span>
            <span>{{ detailsBill?.suplyer || '—' }}</span>
          </div>
          <div class="modal-details-item">
            <span class="label">Categoria:</span>
            <span>{{ detailsBill?.category || '—' }}</span>
          </div>
          <div class="modal-details-item">
            <span class="label">Vencimento:</span>
            <span>{{ detailsBill?.due_date ? brdate(detailsBill.due_date) : '—' }}</span>
          </div>
          <div class="modal-details-item">
            <span class="label">Valor:</span>
            <span>{{ brl(detailsBill?.value) }}</span>
          </div>
          <div class="modal-details-item">
            <span class="label">Nº documento:</span>
            <span>{{ detailsBill?.bar_code || '—' }}</span>
          </div>
          <div class="modal-details-item">
            <span class="label">Lançado em:</span>
            <span>{{ detailsBill?.date_from_add ? brdate(detailsBill.date_from_add) : '—' }}</span>
          </div>
          <div class="modal-details-item">
            <span class="label">Observações:</span>
            <span>{{ detailsBill?.obs || '—' }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="modal" id="pay-modal" :class="{ 'is-open': payModal }">
      <div class="modal-content pay-modal-content">
        <div class="modal-header">
          <h2>Realizar Pagamento</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="payModal = false">&times;</button>
        </div>
        <div class="pay-tabs">
          <button
            type="button"
            class="pay-tab"
            :class="{ 'is-active': activePayTab === 'barcode' }"
            v-show="hasBarcode"
            @click="switchPayTab('barcode')"
          >
            Código de barras
          </button>
          <button
            type="button"
            class="pay-tab"
            :class="{ 'is-active': activePayTab === 'pix' }"
            v-show="hasPix"
            @click="switchPayTab('pix')"
          >
            PIX
          </button>
        </div>

        <div class="pay-hero">
          <span class="pay-hero-label">Valor</span>
          <span class="pay-hero-value">{{ brl(payingBill?.value) }}</span>
        </div>

        <div class="pay-pane" v-show="activePayTab === 'barcode'">
          <div class="pay-barcode">
            <svg ref="barcodeSvg" id="pay-codigo-barras"></svg>
            <p v-if="!hasBarcode || barcodeEmpty" class="pay-barcode-empty">
              Este registro não possui um código de barras válido para escaneamento.
            </p>
          </div>
          <div class="pay-linedigitavel">
            <span class="label">Linha digitável:</span>
            <p id="pay-modal-barcode">{{ linhaDigitavel }}</p>
            <div class="pay-actions" v-if="linhaDigitavel !== '—'">
              <button type="button" class="btn btn-ghost btn-sm" @click="copyText(linhaDigitavel, 'barcode')">
                {{ copyFeedback === 'barcode' ? 'Copiado!' : 'Copiar código' }}
              </button>
            </div>
          </div>
        </div>

        <div class="pay-pane" v-show="activePayTab === 'pix' && hasPix">
          <div class="pix-box">
            <p class="pix-hint" v-if="!payPixPayload && !payPixImage">
              QR Code PIX gerado a partir da chave salva nesta conta.
            </p>
            <div class="pix-qr">
              <svg ref="pixQrSvg" id="pix-qr-svg"></svg>
              <img v-if="payPixImage" id="pix-img" class="pix-qr-img" :src="payPixImage" alt="QR Code PIX" />
            </div>
            <p class="pix-copiacola-label" v-if="pixCopyCola">Pix Copia e Cola:</p>
            <p id="pix-copiacola" class="pix-copiacola">{{ pixCopyCola }}</p>
            <div class="pay-actions" v-if="pixCopyCola">
              <button type="button" class="btn btn-ghost btn-sm" @click="copyText(pixCopyCola, 'pix')">
                {{ copyFeedback === 'pix' ? 'Copiado!' : 'Copiar código PIX' }}
              </button>
            </div>
          </div>
        </div>

        <div class="pay-info">
          <div class="pay-info-item">
            <span class="label">Vencimento:</span>
            <span>{{ brdateShort(payingBill?.due_date) }}</span>
          </div>
          <div class="pay-info-item">
            <span class="label">Referente a:</span>
            <span>{{ payingBill?.reference || '—' }}</span>
          </div>
          <div class="pay-info-item">
            <span class="label">Fornecedor:</span>
            <span>{{ payingBill?.suplyer || '—' }}</span>
          </div>
          <div class="pay-info-item">
            <span class="label">Categoria:</span>
            <span>{{ payingBill?.category || payingBill?.bill_type || '—' }}</span>
          </div>
          <div class="pay-info-item">
            <span class="label">Observações:</span>
            <span>{{ payingBill?.obs || '—' }}</span>
          </div>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-ghost modal-cancel" @click="payModal = false">Cancelar</button>
          <button id="pay-save-button" type="button" class="btn btn-primary" @click="confirmPay">
            Confirmar pagamento
          </button>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}
/* O products.css redefine .modal-content (520px) após o bills.css; força a
   largura original do modal de pagamento (880px) com especificidade maior. */
.modal-content.pay-modal-content {
  max-width: min(880px, 94vw);
}
#pay-modal .pay-pane {
  padding: 4px 28px;
}
#pay-modal .pay-info {
  margin-top: 16px;
  padding: 0 28px;
}
#pay-modal .pay-linedigitavel,
#pay-modal .pix-box {
  margin-top: 16px;
}
</style>