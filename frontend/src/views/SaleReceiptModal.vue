<script setup>
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl } from '@/utils/format'
import ThermalCoupon from '@/components/ThermalCoupon.vue'

const props = defineProps({
  sale: { type: Object, required: true },
})
const emit = defineEmits(['close'])

const order = ref(null)
const loading = ref(true)
const settings = ref({})
const view = ref('full')
const autoPrinted = ref(false)
let pageStyleEl = null
let autoPrintTimer = null

/** Largura térmica ativa ('58' | '80') ou null (modo recibo clássico). */
const thermalWidth = computed(() => {
  const w = settings.value['receipt.width']
  return w === '58' || w === '80' ? w : null
})
const showToggle = computed(() => thermalWidth.value !== null)
const autoPrintEnabled = computed(() => settings.value['pdv.auto_print'] === 'true')

const headerLines = computed(() => splitLines(settings.value['receipt.header']))
const footerLines = computed(() => splitLines(settings.value['receipt.footer']))
const companyLine = computed(() => settings.value['company.name'] || 'BeeFlux')

function splitLines(text) {
  return (text || '').split('\n').map((l) => l.trim()).filter(Boolean)
}

function formatDateTime(iso) {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleString('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
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
    if (thermalWidth.value) view.value = 'thermal'
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
  // Mede o recibo SÓ depois que ele existe no DOM (loading já saiu).
  await nextTick()
  applyPageRule()
  if (autoPrintEnabled.value && order.value && !autoPrinted.value) {
    autoPrinted.value = true
    autoPrintTimer = setTimeout(autoPrint, 250)
  }
}

/**
 * Imprime um CLONE do recibo fora do #app: no print o #app some (display:none)
 * e só o clone é paginado — sai 1 folha do tamanho certo, sem cortes,
 * sem papel comprido e sem duplicar.
 */
function printWithClone() {
  if (typeof window.print !== 'function') return
  const el = document.getElementById('sale-receipt-print')
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

function printReceipt() {
  applyPageRule()
  // window.print() bloqueia até a caixa de impressão fechar; só então o modal fecha.
  printWithClone()
  emit('close')
}

/** Impressão automática pós-venda: não fecha o modal (dá pra reimprimir). */
function autoPrint() {
  applyPageRule()
  printWithClone()
}

/**
 * @page medido: altura exata do cupom renderizado (px -> mm).
 * Assim o papel sai do tamanho certo — sem folga comprida nem corte.
 */
function applyPageRule() {
  removePageRule()
  if (!thermalWidth.value || view.value !== 'thermal') return
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

// F2 imprime, Esc fecha.
function onKeydown(event) {
  if (event.key === 'F2') {
    event.preventDefault()
    printReceipt()
  } else if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
}

watch([thermalWidth, view], async () => {
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
  if (autoPrintTimer) clearTimeout(autoPrintTimer)
})
</script>

<template>
  <div class="modal is-open">
    <div class="modal-content sale-receipt-modal">
      <div class="modal-header">
        <h2>Recibo #{{ sale.id }}</h2>
        <button type="button" class="modal-close" aria-label="Fechar" @click="emit('close')">&times;</button>
      </div>

      <div class="sale-receipt-body">
        <div v-if="loading" class="muted">Carregando recibo…</div>

        <template v-else-if="order">
          <!-- Troca cupom térmico x recibo completo -->
          <div v-if="showToggle" class="filter-segmented receipt-view-toggle no-print" role="group" aria-label="Formato de impressão">
            <button
              type="button"
              :class="{ 'is-active': view === 'thermal' }"
              @click="view = 'thermal'"
            >
              <i class="fas fa-receipt"></i> Cupom {{ thermalWidth }} mm
            </button>
            <button
              type="button"
              :class="{ 'is-active': view === 'full' }"
              @click="view = 'full'"
            >
              <i class="fas fa-file-alt"></i> Recibo
            </button>
          </div>

          <!-- Cupom térmico 58/80 mm -->
          <ThermalCoupon
            v-if="view === 'thermal'"
            id="sale-receipt-print"
            :width="thermalWidth || '80'"
            :company="companyLine"
            :header-lines="headerLines"
            :footer-lines="footerLines"
            :order="order"
          />

          <!-- Recibo completo (formato atual) -->
          <div v-else class="receipt" id="sale-receipt-print">
            <div class="receipt-head">
              <strong>BeeFlux</strong>
              <span>Recibo de venda</span>
            </div>

            <div class="receipt-meta">
              <span>Venda <strong>#{{ order.order_id }}</strong></span>
              <span>{{ formatDateTime(order.date) }}</span>
            </div>

            <table class="receipt-table">
              <thead>
                <tr>
                  <th>Item</th>
                  <th class="r-qty">Qtd</th>
                  <th class="r-amount">Preço</th>
                  <th class="r-amount">Subtotal</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="(item, i) in order.items" :key="i">
                  <td>{{ item.name }}</td>
                  <td class="r-qty">{{ item.quantity }}</td>
                  <td class="r-amount">{{ brl(item.unit_price) }}</td>
                  <td class="r-amount">{{ brl(item.subtotal) }}</td>
                </tr>
              </tbody>
            </table>

            <div v-if="order.discount > 0" class="receipt-discount">
              <span>Desconto</span>
              <strong>&minus;{{ brl(order.discount) }}</strong>
            </div>

            <div class="receipt-total">
              <span>TOTAL</span>
              <strong>{{ brl(order.total) }}</strong>
            </div>

            <template v-if="order.payments && order.payments.length">
              <div v-for="(payment, i) in order.payments" :key="'pay' + i" class="receipt-payment">
                <span>Pago ({{ payment.name }})</span>
                <strong>{{ brl(payment.amount) }}</strong>
              </div>
              <div v-if="order.troco > 0" class="receipt-payment receipt-troco">
                <span>Troco</span>
                <strong>{{ brl(order.troco) }}</strong>
              </div>
            </template>
            <div v-else class="receipt-payment">
              <span>Forma de pagamento</span>
              <strong>{{ order.payment_method }}</strong>
            </div>

            <div v-if="order.obs" class="receipt-obs">
              <span>Observações</span>
              <p>{{ order.obs }}</p>
            </div>

            <div class="receipt-foot">
              <span>Obrigado pela preferência!</span>
              <span>BeeFlux — Clayton Garcia da Silva, Br.</span>
            </div>
          </div>
        </template>

        <div v-else class="muted">Recibo não encontrado.</div>
      </div>

      <div class="modal-footer">
        <button type="button" class="btn btn-ghost modal-cancel" @click="emit('close')">Fechar <kbd>Esc</kbd></button>
        <button type="button" class="btn btn-primary" :disabled="loading || !order" @click="printReceipt">
          <i class="fas fa-print"></i> Imprimir recibo <kbd>F2</kbd>
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

.receipt-view-toggle {
  display: flex;
  width: 100%;
  margin-bottom: 16px;
}

.receipt-view-toggle button {
  flex: 1;
  justify-content: center;
}

</style>
