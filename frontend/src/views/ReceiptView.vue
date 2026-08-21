<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl } from '@/utils/format'

const route = useRoute()
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
    const data = await api.get(`/pdv/recibo/${route.params.id}`)
    order.value = data.order
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="pdv-screen">
    <div class="receipt-wrap">
      <div class="receipt-actions no-print">
        <button type="button" class="btn btn-primary" @click="window.print()">
          <i class="fas fa-print"></i> Imprimir recibo
        </button>
        <router-link class="btn btn-ghost" to="/pdv"><i class="fas fa-plus"></i> Nova venda</router-link>
      </div>

      <div v-if="loading" class="receipt-empty no-print">Carregando recibo…</div>

      <div v-else-if="order" class="receipt" id="receipt">
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

        <div class="receipt-total">
          <span>TOTAL</span>
          <strong>{{ brl(order.total) }}</strong>
        </div>

        <div class="receipt-payment">
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

      <div v-else class="receipt-empty no-print">
        <p>Pedido não encontrado.</p>
        <router-link class="btn btn-ghost" to="/pdv">Voltar ao PDV</router-link>
      </div>
    </div>
  </div>
</template>

<style scoped>
.pdv-screen {
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f3f4f6;
  color: #111827;
}
.receipt-wrap {
  flex: 1;
  min-height: 0;
}
.receipt-empty {
  text-align: center;
  color: var(--text-muted);
  padding: 60px 20px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}
</style>