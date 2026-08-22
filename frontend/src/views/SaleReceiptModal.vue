<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl } from '@/utils/format'

const props = defineProps({
  sale: { type: Object, required: true },
})
const emit = defineEmits(['close'])

const order = ref(null)
const loading = ref(true)

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
    const data = await api.get(path)
    order.value = data.order
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

function printReceipt() {
  window.print()
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

onMounted(() => {
  load()
  document.addEventListener('keydown', onKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
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

        <div v-else-if="order" class="receipt" id="sale-receipt-print">
          <div class="receipt-head">
            <strong>BillFlux</strong>
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

          <template v-if="order.payments && order.payments.length > 1">
            <div v-for="(payment, i) in order.payments" :key="'pay' + i" class="receipt-payment">
              <span>Recebido ({{ payment.name }})</span>
              <strong>{{ brl(payment.amount) }}</strong>
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
            <span>BillFlux — Clayton Garcia da Silva, Br.</span>
          </div>
        </div>

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
</style>