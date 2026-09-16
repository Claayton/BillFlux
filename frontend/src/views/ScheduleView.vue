<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl } from '@/utils/format'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const loading = ref(false)
const week = ref([])
const selectedDay = ref(null)

const dayNamesFull = ['Segunda-feira', 'Terça-feira', 'Quarta-feira', 'Quinta-feira', 'Sexta-feira', 'Sábado', 'Domingo']

async function load() {
  loading.value = true
  try {
    const data = await api.get('/schedule/week')
    week.value = data.week || []
    const today = week.value.find(d => d.is_today)
    if (today) selectedDay.value = today
    else if (week.value.length) selectedDay.value = week.value[0]
  } catch (error) {
    ElMessage.error('Erro ao carregar agenda: ' + error.message)
  } finally {
    loading.value = false
  }
}

function selectDay(day) {
  selectedDay.value = day
}

async function createOrder(supplierId) {
  try {
    const res = await api.post('/schedule/create-order', { supplier_id: supplierId })
    ElMessage.success(`Pedido #${res.purchase_id} criado com ${res.items_count} itens!`)
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function totalProducts(day) {
  return day.suggestions.reduce((sum, s) => sum + s.products.length, 0)
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="page-header">
      <h1><i class="fas fa-calendar-alt"></i> Agenda de Pedidos</h1>
    </div>

    <div v-if="loading" class="muted">Carregando...</div>

    <div v-else class="schedule-layout">
      <div class="week-strip">
        <div
          v-for="day in week" :key="day.date"
          class="week-day"
          :class="{
            'is-today': day.is_today,
            'is-selected': selectedDay?.date === day.date,
            'has-orders': day.product_count > 0
          }"
          @click="selectDay(day)"
        >
          <span class="week-day-name">{{ day.day_name.slice(0, 3) }}</span>
          <span class="week-day-num">{{ new Date(day.date + 'T12:00:00').getDate() }}</span>
          <span v-if="day.product_count > 0" class="week-day-badge">{{ day.product_count }}</span>
        </div>
      </div>

      <div v-if="selectedDay" class="schedule-content">
        <h2>{{ dayNamesFull[selectedDay.day_of_week] }} — {{ selectedDay.date }}</h2>

        <div v-if="!selectedDay.suggestions.length" class="empty-state">
          <i class="fas fa-check-circle"></i>
          <p>Nenhum pedido sugerido para este dia.</p>
        </div>

        <div v-else class="supplier-cards">
          <div v-for="s in selectedDay.suggestions" :key="s.supplier_id" class="supplier-card">
            <div class="supplier-card-header">
              <div>
                <h3>{{ s.supplier_name }}</h3>
                <span class="supplier-product-count">{{ s.products.length }} produto(s)</span>
              </div>
              <button class="btn btn-primary btn-sm" @click="createOrder(s.supplier_id)">
                <i class="fas fa-file-alt"></i> Criar pedido
              </button>
            </div>
            <table class="data-table">
              <thead>
                <tr>
                  <th>Produto</th>
                  <th class="th-number">Estoque atual</th>
                  <th class="th-number">Estoque ideal</th>
                  <th class="th-number">Sugerido</th>
                  <th class="th-number">Média/dia (28d)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in s.products" :key="p.product_id">
                  <td>{{ p.product_name }}</td>
                  <td class="cell-number" :class="{ 'stock-low': p.current_stock <= 0 }">{{ p.current_stock }}</td>
                  <td class="cell-number">{{ p.ideal_stock }}</td>
                  <td class="cell-number cell-highlight">{{ p.suggested_qty }}</td>
                  <td class="cell-number">{{ p.avg_daily_sales.toFixed(1) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.page-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 20px; }
.page-header h1 { font-size: 20px; display: flex; align-items: center; gap: 8px; }
.muted { color: var(--text-muted); padding: 24px; }

.schedule-layout { display: flex; flex-direction: column; gap: 20px; }

.week-strip { display: flex; gap: 6px; }
.week-day {
  flex: 1; display: flex; flex-direction: column; align-items: center; gap: 4px;
  padding: 12px 8px; border-radius: 10px; cursor: pointer;
  background: var(--surface, #fff); border: 2px solid transparent;
  transition: all .15s;
}
.week-day:hover { border-color: var(--primary, #2563eb33); }
.week-day.is-today { border-color: var(--primary, #2563eb); }
.week-day.is-selected { background: var(--primary, #2563eb); color: #fff; }
.week-day-name { font-size: 12px; text-transform: uppercase; opacity: .7; }
.week-day-num { font-size: 20px; font-weight: 700; }
.week-day-badge {
  background: var(--danger, #ef4444); color: #fff; font-size: 11px; font-weight: 700;
  padding: 2px 6px; border-radius: 10px; min-width: 18px; text-align: center;
}
.week-day.is-selected .week-day-badge { background: #fff; color: var(--primary, #2563eb); }

.schedule-content h2 { font-size: 18px; margin-bottom: 16px; }

.empty-state { text-align: center; padding: 40px; color: var(--text-muted, #999); }
.empty-state i { font-size: 40px; margin-bottom: 12px; color: var(--success, #22c55e); display: block; }

.supplier-cards { display: flex; flex-direction: column; gap: 16px; }
.supplier-card {
  background: var(--surface, #fff); border-radius: 12px; padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.08);
}
.supplier-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; }
.supplier-card-header h3 { font-size: 16px; margin: 0; }
.supplier-product-count { font-size: 12px; color: var(--text-muted, #999); }

.stock-low { color: var(--danger, #ef4444); font-weight: 700; }
.cell-highlight { color: var(--primary, #2563eb); font-weight: 700; }
</style>
