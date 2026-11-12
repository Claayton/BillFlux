<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import ThermalCoupon from '@/components/ThermalCoupon.vue'
import { printDanfe } from '@/utils/danfe'
import { printElementWithAgent } from '@/utils/printBridge'

const props = defineProps({
  sale: { type: Object, required: true },
  /**
   * 'post-sale': modal pós-venda do PDV (emitir, imprimir cupom ou nova venda);
   * Esc fecha como "nova venda". 'reprint': reimpressão em Vendas.
   */
  mode: { type: String, default: 'reprint' },
})
const emit = defineEmits(['close'])

const order = ref(null)
const loading = ref(true)
const settings = ref({})
const fiscalDocument = ref(null)
const fiscalMessage = ref('')
const fiscalBusy = ref(false)
const printing = ref(false)
let pageStyleEl = null

const isPostSale = computed(() => props.mode === 'post-sale')

/** Largura térmica configurada; sem configuração assume 80 mm (cupom). */
const thermalWidth = computed(() => (settings.value['receipt.width'] === '58' ? '58' : '80'))
const paperWidthMm = computed(() => Number(thermalWidth.value))

const fiscal = computed(() => fiscalDocument.value || props.sale.fiscal || null)
const isAuthorized = computed(() => fiscal.value?.status === 'autorizada')
const canPrintDanfe = computed(
  () => isAuthorized.value && Boolean(fiscal.value?.has_danfe) && Boolean(fiscal.value?.id)
)
const hasFiscalError = computed(
  () => Boolean(fiscalMessage.value) || ['rejeitada', 'denegada'].includes(fiscal.value?.status)
)
const printLabel = computed(() => (canPrintDanfe.value ? 'Imprimir DANFE' : 'Imprimir cupom'))
const needsRetry = computed(() => Boolean(fiscal.value) && !isAuthorized.value)
const fiscalBadge = computed(() => {
  if (isAuthorized.value) return { label: 'NFC-e autorizada', icon: 'fa-circle-check', tone: 'ok' }
  if (fiscal.value?.status === 'cancelada') {
    return { label: 'Nota cancelada', icon: 'fa-ban', tone: 'muted' }
  }
  if (hasFiscalError.value) {
    return { label: 'NFC-e não autorizada', icon: 'fa-triangle-exclamation', tone: 'error' }
  }
  if (fiscal.value?.status) {
    return { label: 'NFC-e pendente', icon: 'fa-clock', tone: 'warn' }
  }
  return null
})

const headerLines = computed(() => splitLines(settings.value['receipt.header']))
const footerLines = computed(() => splitLines(settings.value['receipt.footer']))
const companyLine = computed(() => settings.value['company.name'] || '')
const companyCnpj = computed(() => settings.value['company.cnpj'] || '')
const companyAddress = computed(() => settings.value['company.address'] || '')
const companyPhone = computed(() => settings.value['company.phone'] || '')
const receiptMessage = computed(() => settings.value['receipt.message'] || '')
const isOn = (key) => settings.value[key] === 'true'

function splitLines(text) {
  return (text || '').split('\n').map((l) => l.trim()).filter(Boolean)
}

async function load() {
  try {
    const path =
      props.sale.kind === 'pdv'
        ? `/pdv/recibo/${props.sale.id}`
        : `/sales/recibo/${props.sale.id}`
    const [data, cfg] = await Promise.all([
      api.get(path),
      api.get('/settings').catch(() => ({ settings: {} })),
    ])
    order.value = data.order
    settings.value = cfg.settings || {}
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
  await nextTick()
  applyPageRule()
}

/**
 * Imprime um CLONE do cupom fora do #app: no print o #app some (display:none)
 * e só o clone é paginado — sai 1 folha do tamanho certo.
 * Com o agente de impressão rodando, o clone vai por HTTP e imprime direto.
 */
async function printWithClone() {
  const el = document.getElementById('sale-receipt-print')
  if (!el) {
    if (typeof window.print === 'function') window.print()
    return
  }

  if (await printElementWithAgent(el, { widthMm: paperWidthMm.value })) return

  if (typeof window.print !== 'function') return
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

/** Imprime o cupom não fiscal com os dados das configurações. */
async function printCoupon() {
  applyPageRule()
  await printWithClone()
}

/**
 * @page medido: altura exata do cupom renderizado (px -> mm).
 * Assim o papel sai do tamanho certo — sem folga comprida nem corte.
 */
function applyPageRule() {
  removePageRule()
  const el = document.getElementById('sale-receipt-print')
  const heightPx = el ? el.getBoundingClientRect().height : 0
  const w = thermalWidth.value
  const wMm = Number(w)
  let hMm = heightPx > 0 ? Math.ceil((heightPx * 25.4) / 96) + 3 : wMm
  // Nunca paisagem (largura > altura): drivers térmicos giram o conteúdo.
  if (hMm < wMm) hMm = wMm
  pageStyleEl = document.createElement('style')
  pageStyleEl.textContent = `@page { size: ${w}mm ${hMm}mm; margin: 0; }`
  document.head.appendChild(pageStyleEl)
}

function removePageRule() {
  if (pageStyleEl) {
    pageStyleEl.remove()
    pageStyleEl = null
  }
}

/** Emite a NFC-e da venda já concluída (nunca desfaz a venda). */
async function emitirNota() {
  if (fiscalBusy.value) return
  fiscalBusy.value = true
  fiscalMessage.value = ''
  try {
    const result = await api.post('/fiscal/emitir', { order_id: props.sale.id })
    fiscalDocument.value = result.document || null
    if (result.ok) {
      const number = result.document?.number ? ` (nº ${result.document.number})` : ''
      ElMessage.success(`NFC-e autorizada${number}.`)
    } else {
      fiscalMessage.value =
        result.message || 'A SEFAZ não autorizou a nota. Confira e tente novamente.'
      ElMessage.warning('NFC-e não autorizada. Veja o motivo no modal.')
    }
  } catch (error) {
    fiscalMessage.value = error.message
    ElMessage.error(error.message)
  } finally {
    fiscalBusy.value = false
  }
}

/** Imprime o DANFE (quando autorizada) ou o cupom não fiscal. */
async function printDocument() {
  if (printing.value) return
  if (canPrintDanfe.value) {
    printing.value = true
    try {
      await printDanfe(fiscal.value.id, { widthMm: paperWidthMm.value })
    } catch (error) {
      ElMessage.error(error.message)
      throw error
    } finally {
      printing.value = false
    }
    return
  }
  await printCoupon()
}

async function printDocumentAndClose() {
  try {
    await printDocument()
    close()
  } catch {
    /* o erro já foi avisado; mantém o modal aberto */
  }
}

async function printCouponAndClose() {
  if (printing.value) return
  printing.value = true
  try {
    await printCoupon()
  } finally {
    printing.value = false
  }
  close()
}

function close() {
  emit('close')
}

// P imprime, F3 emite (pós-venda), F2 nova venda e Esc fecha o modal.
function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    close()
    return
  }
  if (event.key === 'p' || event.key === 'P') {
    // Não sequestra o "p" de quem está digitando num campo (busca do PDV).
    const tag = event.target?.tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || event.target?.isContentEditable) {
      return
    }
    if (event.repeat) return
    event.preventDefault()
    if (printing.value || loading.value || !order.value) return
    if (isPostSale.value) {
      printCouponAndClose()
    } else {
      printDocumentAndClose()
    }
    return
  }
  if (isPostSale.value) {
    if (event.key === 'F3') {
      event.preventDefault()
      if (printing.value || fiscalBusy.value || loading.value || !order.value) return
      if (canPrintDanfe.value) {
        printDocumentAndClose()
      } else if (!isAuthorized.value) {
        emitirNota()
      }
    } else if (event.key === 'F2') {
      event.preventDefault()
      close()
    }
    return
  }
  if (event.key === 'F2') {
    event.preventDefault()
    printDocumentAndClose()
  }
}

watch(thermalWidth, async () => {
  await nextTick()
  applyPageRule()
})

onMounted(() => {
  load()
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  removePageRule()
})
</script>

<template>
  <div class="modal is-open">
    <div class="modal-content sale-receipt-modal" :class="{ 'is-post-sale': isPostSale }">
      <div class="modal-header">
        <h2>
          {{ isPostSale ? `Venda #${sale.id} finalizada` : `Cupom #${sale.id}` }}
        </h2>
        <button
          v-if="!isPostSale"
          type="button"
          class="modal-close"
          aria-label="Fechar"
          @click="close"
        >
          &times;
        </button>
      </div>

      <div v-if="!isPostSale" class="sale-receipt-body">
        <div v-if="loading" class="muted">Carregando…</div>

        <template v-else-if="order">
          <div v-if="fiscalBadge" class="fiscal-result" :class="`is-${fiscalBadge.tone}`">
            <div class="fiscal-result-title">
              <i class="fas" :class="fiscalBadge.icon"></i> {{ fiscalBadge.label }}
            </div>

            <template v-if="isAuthorized">
              <div class="fiscal-result-grid">
                <span>Número</span>
                <strong>{{ fiscal.number || '—' }}</strong>
                <span>Série</span>
                <strong>{{ fiscal.series || '—' }}</strong>
                <template v-if="fiscal.protocol">
                  <span>Protocolo</span>
                  <strong>{{ fiscal.protocol }}</strong>
                </template>
                <template v-if="fiscal.access_key">
                  <span>Chave</span>
                  <strong class="fiscal-key">{{ fiscal.access_key }}</strong>
                </template>
              </div>
            </template>

            <p v-else-if="fiscalMessage" class="fiscal-result-message">{{ fiscalMessage }}</p>
          </div>

          <ThermalCoupon
            id="sale-receipt-print"
            :width="thermalWidth"
            :company="companyLine"
            :header-lines="headerLines"
            :footer-lines="footerLines"
            :order="order"
            :company-cnpj="companyCnpj"
            :company-address="companyAddress"
            :company-phone="companyPhone"
            :show-cnpj="isOn('receipt.show_cnpj')"
            :show-address="isOn('receipt.show_address')"
            :show-phone="isOn('receipt.show_phone')"
            :show-customer="isOn('receipt.show_customer')"
            :message="receiptMessage"
          />
        </template>

        <div v-else class="muted">Cupom não encontrado.</div>
      </div>

      <!-- Pós-venda: ações rápidas, sem preview do cupom -->
      <div v-if="isPostSale" class="sale-receipt-quick">
        <div v-if="loading" class="muted">Carregando…</div>

        <template v-else>
          <div
            v-if="fiscalBadge"
            class="post-sale-status"
            :class="`is-${fiscalBadge.tone}`"
          >
            <i class="fas" :class="fiscalBadge.icon"></i>
            <strong>{{ fiscalBadge.label }}</strong>
            <span v-if="isAuthorized && fiscal.number">
              nº {{ fiscal.number }} · série {{ fiscal.series || '—' }}
            </span>
          </div>

          <p v-if="fiscalMessage" class="post-sale-message">{{ fiscalMessage }}</p>
          <p v-if="!order" class="muted">Cupom não encontrado.</p>

          <div class="sale-receipt-actions is-horizontal">
            <button
              type="button"
              class="btn btn-outline"
              :disabled="printing || loading || !order"
              @click="printCouponAndClose"
            >
              <i :class="['fas', printing ? 'fa-circle-notch fa-spin' : 'fa-receipt']"></i>
              {{ printing ? 'Preparando…' : 'Imprimir comprovante' }} <kbd>P</kbd>
            </button>

            <button
              v-if="canPrintDanfe"
              type="button"
              class="btn btn-primary"
              :disabled="printing"
              @click="printDocumentAndClose"
            >
              <i :class="['fas', printing ? 'fa-circle-notch fa-spin' : 'fa-file-invoice']"></i>
              {{ printing ? 'Preparando…' : 'Imprimir DANFE' }} <kbd>F3</kbd>
            </button>
            <button
              v-else-if="isAuthorized"
              type="button"
              class="btn btn-primary"
              disabled
            >
              <i class="fas fa-circle-check"></i> NFC-e autorizada
            </button>
            <button
              v-else
              type="button"
              class="btn btn-primary"
              :disabled="fiscalBusy || loading || !order"
              @click="emitirNota"
            >
              <i
                :class="[
                  'fas',
                  fiscalBusy ? 'fa-circle-notch fa-spin' : 'fa-file-invoice-dollar',
                ]"
              ></i>
              {{ fiscalBusy ? 'Emitindo…' : needsRetry ? 'Tentar de novo' : 'Emitir NFC-e' }}
              <kbd>F3</kbd>
            </button>

            <button type="button" class="btn btn-ghost" @click="close">
              <i class="fas fa-check"></i> Concluir <kbd>F2</kbd>
            </button>
          </div>

          <p class="sale-receipt-hint"><kbd>Esc</kbd> também conclui e volta ao PDV</p>
        </template>
      </div>

      <!-- Reimpressão (Vendas) -->
      <div v-else class="modal-footer">
        <button type="button" class="btn btn-ghost modal-cancel" @click="close">
          Fechar <kbd>Esc</kbd>
        </button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="loading || !order || printing"
          @click="printDocumentAndClose"
        >
          <i :class="['fas', printing ? 'fa-circle-notch fa-spin' : 'fa-print']"></i>
          {{ printing ? 'Preparando…' : printLabel }} <kbd>P</kbd>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px;
  text-align: center;
}
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

/* Resultado fiscal da emissão */
.fiscal-result {
  margin-bottom: 16px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-hover, #f8fafc);
}
.fiscal-result.is-ok {
  border-color: #16a34a;
  background: rgba(22, 163, 74, 0.08);
}
.fiscal-result.is-error {
  border-color: #dc2626;
  background: rgba(220, 38, 38, 0.07);
}
.fiscal-result.is-warn {
  border-color: #d97706;
  background: rgba(245, 158, 11, 0.09);
}
.fiscal-result-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 700;
  color: var(--text);
}
.fiscal-result.is-ok .fiscal-result-title {
  color: #15803d;
}
.fiscal-result.is-error .fiscal-result-title {
  color: #b91c1c;
}
.fiscal-result.is-warn .fiscal-result-title {
  color: #b45309;
}
.fiscal-result-grid {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 4px 12px;
  margin-top: 8px;
  font-size: 12px;
}
.fiscal-result-grid span {
  color: var(--text-muted);
}
.fiscal-result-grid strong {
  color: var(--text);
  font-variant-numeric: tabular-nums;
  word-break: break-all;
}
.fiscal-key {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  font-size: 11px;
  line-height: 1.4;
}
.fiscal-result-message {
  margin: 6px 0 0;
  font-size: 12px;
  line-height: 1.45;
  color: var(--text-secondary);
}

/* Ações do modal pós-venda */
.sale-receipt-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sale-receipt-actions .action-wide {
  width: 100%;
  justify-content: center;
}
.sale-receipt-actions .action-row {
  display: flex;
  gap: 8px;
}
.sale-receipt-actions .action-row .btn {
  flex: 1;
  justify-content: center;
}
.sale-receipt-hint {
  margin: 2px 0 0;
  text-align: center;
  font-size: 11px;
  color: var(--text-muted);
}

/* Modal pós-venda: horizontal, só as três ações (sem preview do cupom) */
.sale-receipt-modal.is-post-sale {
  max-width: 760px;
}
.sale-receipt-quick {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 16px 24px 18px;
}
.post-sale-status {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-hover, #f8fafc);
  font-size: 12px;
  color: var(--text-secondary);
}
.post-sale-status strong {
  font-size: 12px;
  color: var(--text);
}
.post-sale-status span {
  color: var(--text-muted);
}
.post-sale-status.is-ok {
  border-color: rgba(22, 163, 74, 0.35);
  background: rgba(22, 163, 74, 0.08);
}
.post-sale-status.is-ok i,
.post-sale-status.is-ok strong {
  color: #15803d;
}
.post-sale-status.is-warn {
  border-color: rgba(217, 119, 6, 0.35);
  background: rgba(245, 158, 11, 0.09);
}
.post-sale-status.is-warn i,
.post-sale-status.is-warn strong {
  color: #b45309;
}
.post-sale-status.is-error {
  border-color: rgba(220, 38, 38, 0.35);
  background: rgba(220, 38, 38, 0.07);
}
.post-sale-status.is-error i,
.post-sale-status.is-error strong {
  color: #b91c1c;
}
.post-sale-message {
  margin: 0;
  font-size: 12px;
  line-height: 1.45;
  color: #b91c1c;
}
.sale-receipt-actions.is-horizontal {
  flex-direction: row;
  flex-wrap: wrap;
}
.sale-receipt-actions.is-horizontal .btn {
  flex: 1 1 190px;
  justify-content: center;
  white-space: nowrap;
}

@media (max-width: 560px) {
  .sale-receipt-modal.is-post-sale {
    max-width: calc(100vw - 24px);
  }
  .sale-receipt-quick {
    padding: 14px 16px 16px;
  }
  .sale-receipt-actions.is-horizontal .btn {
    flex-basis: 100%;
  }
}
</style>
