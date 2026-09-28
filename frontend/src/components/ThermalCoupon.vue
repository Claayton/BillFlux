<script setup>
import { brl } from '@/utils/format'

defineProps({
  /** Largura do papel em mm ('58' | '80'). */
  width: { type: String, default: '80' },
  /** Nome da empresa (fallback quando não há cabeçalho). */
  company: { type: String, default: 'BeeFlux' },
  /** Linhas do cabeçalho do cupom (já quebradas). */
  headerLines: { type: Array, default: () => [] },
  /** Linhas do rodapé do cupom (já quebradas). */
  footerLines: { type: Array, default: () => [] },
  /** Dados do pedido (mesmo formato do recibo da API). */
  order: { type: Object, required: true },
})

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
</script>

<template>
  <div class="receipt receipt-thermal" :style="{ width: width + 'mm' }">
    <div class="receipt-head">
      <strong>{{ headerLines[0] || company }}</strong>
      <span v-if="headerLines.length > 1">{{ headerLines.slice(1).join(' · ') }}</span>
      <span v-else>Recibo de venda</span>
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
      <template v-if="footerLines.length">
        <span v-for="(line, i) in footerLines" :key="i">{{ line }}</span>
      </template>
      <template v-else>
        <span>Obrigado pela preferência!</span>
        <span>BeeFlux — Clayton Garcia da Silva, Br.</span>
      </template>
    </div>
  </div>
</template>

<style scoped>
/* Mesmo visual do recibo antigo (pdv.css .receipt), ajustado à largura do papel. */
.receipt-thermal {
  box-sizing: border-box;
  margin: 0 auto;
  padding: 10px 8px;
  font-size: 11px;
  border-radius: 0;
  box-shadow: none;
}

.receipt-thermal .receipt-head {
  gap: 1px;
  padding-bottom: 6px;
  margin-bottom: 6px;
}

.receipt-thermal .receipt-head strong {
  font-size: 13px;
}

.receipt-thermal .receipt-head span {
  font-size: 10px;
}

.receipt-thermal .receipt-meta {
  margin-bottom: 6px;
  font-size: 10px;
}

.receipt-thermal .receipt-table {
  table-layout: fixed;
}

.receipt-thermal .receipt-table th {
  font-size: 9px;
  letter-spacing: 0.2px;
  padding-bottom: 4px;
}

.receipt-thermal .receipt-table td {
  padding: 4px 0;
  font-size: 10px;
  word-break: break-word;
}

.receipt-thermal .receipt-table .r-qty {
  width: 22px;
}

.receipt-thermal .receipt-table .r-amount {
  width: 62px;
}

.receipt-thermal .receipt-total,
.receipt-thermal .receipt-payment,
.receipt-thermal .receipt-discount {
  margin-top: 6px;
}

.receipt-thermal .receipt-discount {
  font-size: 11px;
}

.receipt-thermal .receipt-total {
  padding-top: 6px;
  font-size: 13px;
}

.receipt-thermal .receipt-payment.receipt-troco {
  font-size: 11px;
}

.receipt-thermal .receipt-obs {
  margin-top: 6px;
  font-size: 10px;
}

.receipt-thermal .receipt-foot {
  gap: 1px;
  margin-top: 8px;
  padding-top: 6px;
  font-size: 10px;
}
</style>
