<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl } from '@/utils/format'
import { tabLabel } from '@/utils/tabs'

const props = defineProps({
  /** Detalhe da comanda (payload de GET /tabs/<id>), com itens. */
  tab: { type: Object, required: true },
})
const emit = defineEmits(['close', 'printed'])

const settings = ref({})
const isReprint = computed(() => (props.tab.print_count || 0) > 0)
let pageStyleEl = null
let autoPrintTimer = null
let autoPrinted = false

/** Largura térmica: configuração do sistema ou 80 mm por padrão. */
const thermalWidth = computed(() => {
  const w = settings.value['receipt.width']
  return w === '58' || w === '80' ? w : '80'
})

const companyLine = computed(
  () =>
    (settings.value['receipt.header'] || '').split('\n')[0]?.trim() ||
    settings.value['company.name'] ||
    'BeeFlux'
)

function formatDateTime(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/**
 * Imprime um CLONE do ticket fora do #app (mesmo mecanismo do recibo de
 * venda): no print o #app some e só o clone sai no papel.
 */
function printWithClone() {
  if (typeof window.print !== 'function') return
  const el = document.getElementById('tab-print')
  if (!el) {
    window.print()
    return
  }
  const clone = el.cloneNode(true)
  clone.classList.add('receipt-print-clone')
  document.body.appendChild(clone)
  document.body.classList.add('printing-receipt')
  try {
    window.print()
  } finally {
    clone.remove()
    document.body.classList.remove('printing-receipt')
  }
}

/** @page medido: altura exata do ticket (px -> mm), nunca paisagem. */
function applyPageRule() {
  removePageRule()
  const el = document.getElementById('tab-print')
  const heightPx = el ? el.getBoundingClientRect().height : 0
  const width = thermalWidth.value
  const wMm = Number(width)
  let hMm = heightPx > 0 ? Math.ceil((heightPx * 25.4) / 96) + 3 : wMm
  if (hMm < wMm) hMm = wMm
  pageStyleEl = document.createElement('style')
  pageStyleEl.textContent = `@page { size: ${width}mm ${hMm}mm; margin: 0; }`
  document.head.appendChild(pageStyleEl)
}

function removePageRule() {
  if (pageStyleEl) {
    pageStyleEl.remove()
    pageStyleEl = null
  }
}

async function bumpPrintCount() {
  try {
    const data = await api.post(`/tabs/${props.tab.id}/print`)
    emit('printed', data.tab)
  } catch {
    /* contador é best-effort: a impressão já ocorreu */
  }
}

function printTicket() {
  applyPageRule()
  printWithClone()
  bumpPrintCount()
}

/** Impressão automática ao abrir o modal (opção "Imprimir comanda"). */
function autoPrint() {
  applyPageRule()
  printWithClone()
  bumpPrintCount()
}

function onKeydown(event) {
  if (event.key === 'F2' || (event.key === 'Enter' && !event.shiftKey)) {
    event.preventDefault()
    printTicket()
  } else if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
}

onMounted(async () => {
  document.addEventListener('keydown', onKeydown)
  try {
    const cfg = await api.get('/settings')
    settings.value = cfg.settings || {}
  } catch {
    settings.value = {}
  }
  await nextTick()
  applyPageRule()
  if (!autoPrinted) {
    autoPrinted = true
    autoPrintTimer = setTimeout(autoPrint, 250)
  }
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  removePageRule()
  if (autoPrintTimer) clearTimeout(autoPrintTimer)
})
</script>

<template>
  <div class="modal is-open">
    <div class="modal-content sale-receipt-modal tab-print-modal">
      <div class="modal-header">
        <h2>Comanda {{ tabLabel(tab.number) }}</h2>
        <button type="button" class="modal-close" aria-label="Fechar" @click="emit('close')">
          &times;
        </button>
      </div>

      <div class="sale-receipt-body">
        <div class="receipt receipt-thermal tab-ticket" id="tab-print" :style="{ width: thermalWidth + 'mm' }">
          <div class="tab-ticket-head">
            <strong>{{ companyLine }}</strong>
            <span>Comanda de consumo</span>
          </div>

          <div class="tab-ticket-title">
            <span>COMANDA {{ tabLabel(tab.number) }}</span>
            <span v-if="isReprint" class="tab-ticket-reprint">REIMPRESSÃO</span>
          </div>

          <div class="tab-ticket-meta">
            <span>Mesa/Cliente: <strong>{{ tab.identification }}</strong></span>
            <span>Abertura: {{ formatDateTime(tab.opened_at) }}</span>
          </div>

          <table class="receipt-table tab-ticket-table">
            <tbody>
              <tr v-for="item in tab.items || []" :key="item.id">
                <td>{{ item.quantity }}x {{ item.name }}</td>
                <td class="r-amount">{{ brl(item.total) }}</td>
              </tr>
            </tbody>
          </table>

          <div class="tab-ticket-launched">
            <span>LANÇADO NO SISTEMA:</span>
            <strong>{{ brl(tab.total) }}</strong>
          </div>

          <div class="tab-ticket-notes">
            <div class="tab-ticket-notes-title">ADICIONAIS / ANOTAÇÕES</div>
            <div v-for="n in 6" :key="n" class="tab-ticket-note-line">
              ______________________ R$ __________
            </div>
          </div>

          <div class="tab-ticket-final">TOTAL FINAL: R$ ______________________</div>
          <div class="tab-ticket-note-line">Pagamento: ___________________________</div>
          <div class="tab-ticket-note-line">Atendente: ___________________________</div>

          <div class="tab-ticket-foot">
            <span>Lançado por: {{ tab.opened_by || '—' }}</span>
            <span>{{ tabLabel(tab.number) }}</span>
          </div>
        </div>
      </div>

      <div class="modal-footer">
        <button type="button" class="btn btn-ghost modal-cancel" @click="emit('close')">
          Fechar <kbd>Esc</kbd>
        </button>
        <button type="button" class="btn btn-primary" @click="printTicket">
          <i class="fas fa-print"></i>
          {{ isReprint ? 'Reimprimir' : 'Imprimir' }} comanda <kbd>F2</kbd>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sale-receipt-modal {
  max-width: 380px;
}
.sale-receipt-body {
  padding: 20px 20px 16px;
}
.sale-receipt-modal .modal-footer {
  margin-top: 0;
  padding: 14px 20px 18px;
}

/* ---- Ticket térmico (herda .receipt* global do pdv.css) ---- */
.tab-ticket {
  box-sizing: border-box;
  margin: 0 auto;
  padding: 10px 8px;
  font-size: 11px;
  border-radius: 0;
  box-shadow: none;
}

.tab-ticket-head {
  display: flex;
  flex-direction: column;
  gap: 1px;
  padding-bottom: 6px;
  margin-bottom: 6px;
  border-bottom: 1px dashed #111;
  text-align: center;
}

.tab-ticket-head strong {
  font-size: 13px;
}

.tab-ticket-head span {
  font-size: 10px;
  color: #374151;
}

.tab-ticket-title {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 800;
  letter-spacing: 0.5px;
  margin-bottom: 4px;
}

.tab-ticket-reprint {
  padding: 1px 5px;
  border: 1px solid #111;
  font-size: 9px;
  font-weight: 800;
}

.tab-ticket-meta {
  display: flex;
  flex-direction: column;
  gap: 1px;
  font-size: 10px;
  margin-bottom: 6px;
}

.tab-ticket-table {
  table-layout: fixed;
  border-top: 1px dashed #111;
}

.tab-ticket-table td {
  padding: 4px 0;
  font-size: 11px;
  word-break: break-word;
}

.tab-ticket-table .r-amount {
  width: 64px;
  text-align: right;
}

.tab-ticket-launched {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding-top: 6px;
  margin-top: 2px;
  border-top: 1px dashed #111;
  font-size: 11px;
  font-weight: 700;
}

.tab-ticket-notes {
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #111;
}

.tab-ticket-notes-title {
  font-size: 11px;
  font-weight: 800;
  letter-spacing: 0.4px;
  margin-bottom: 6px;
  text-align: center;
}

.tab-ticket-note-line {
  font-size: 11px;
  line-height: 2.1;
  white-space: nowrap;
}

.tab-ticket-final {
  margin-top: 6px;
  padding-top: 6px;
  border-top: 1px dashed #111;
  font-size: 11px;
  font-weight: 800;
  line-height: 2.1;
}

.tab-ticket-foot {
  display: flex;
  justify-content: space-between;
  gap: 6px;
  margin-top: 8px;
  padding-top: 6px;
  border-top: 1px dashed #111;
  font-size: 9px;
  color: #374151;
}
</style>
