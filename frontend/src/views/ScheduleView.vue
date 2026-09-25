<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'

const loading = ref(false)
const week = ref([])
const selectedDay = ref(null)

const WEEKDAYS_FULL = ['domingo', 'segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado']
const MONTHS_FULL = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

function cap(text) {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

/** Data amigável pt-BR a partir do ISO (montada manualmente para o
 *  formato ser idêntico em qualquer navegador; API intacta). */
function friendlyDate(iso) {
  if (!iso) return ''
  const d = new Date(iso + 'T12:00:00')
  if (Number.isNaN(d.getTime())) return iso
  return `${cap(WEEKDAYS_FULL[d.getDay()])}, ${d.getDate()} de ${MONTHS_FULL[d.getMonth()]}`
}

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

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="dashboard">
      <div class="page-header">
        <div>
          <h1 class="page-title">Agenda de pedidos</h1>
          <p class="page-subtitle">Organize e acompanhe as sugestões de pedidos por dia.</p>
        </div>
      </div>

      <div v-if="loading" class="muted">Carregando...</div>

      <div v-else class="schedule-layout">
      <div class="week-strip">
        <div
          v-for="day in week" :key="day.date"
          class="week-day"
          :class="{
            'is-today': day.is_today,
            'is-selected': selectedDay?.date === day.date
          }"
          @click="selectDay(day)"
        >
          <span class="week-day-name">{{ day.day_name.slice(0, 3) }}</span>
          <span class="week-day-num">{{ new Date(day.date + 'T12:00:00').getDate() }}</span>
          <span v-if="day.product_count > 0" class="week-day-badge">{{ day.product_count }}</span>
        </div>
      </div>

      <div v-if="selectedDay" class="schedule-content">
        <h2>{{ friendlyDate(selectedDay.date) }}</h2>

        <div v-if="!selectedDay.suggestions.length" class="empty-state">
          <i class="fas fa-calendar-day"></i>
          <h3>Nenhum pedido sugerido</h3>
          <p>Não há sugestões de pedido para este dia.</p>
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
    </div>
  </AppShell>
</template>

<style scoped>
.muted { color: var(--text-muted); padding: 24px 4px; }

.schedule-layout { display: flex; flex-direction: column; gap: 20px; }

.week-strip { display: flex; gap: 8px; }

.week-day {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 8px 4px;
  border-radius: var(--brand-radius-sm);
  cursor: pointer;
  background: var(--surface);
  border: 1px solid var(--border);
  box-shadow: var(--shadow-xs);
  transition: border-color 150ms ease, box-shadow 150ms ease;
}

.week-day:hover {
  border-color: var(--border-strong);
}

.week-day.is-today {
  border-color: var(--primary);
}

.week-day.is-selected {
  background: var(--brand-gradient);
  border-color: transparent;
  color: #fff;
  box-shadow: var(--brand-shadow-btn);
}

.week-day-name {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  opacity: 0.75;
}

.week-day-num {
  font-size: 18px;
  font-weight: 800;
  letter-spacing: -0.4px;
  font-variant-numeric: tabular-nums;
  line-height: 1.2;
}

.week-day-badge {
  background: var(--primary-soft);
  color: var(--primary);
  font-size: 11px;
  font-weight: 700;
  padding: 1px 7px;
  border-radius: 999px;
  min-width: 18px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.week-day.is-selected .week-day-badge {
  background: rgba(255, 255, 255, 0.25);
  color: #fff;
}

.schedule-content h2 {
  font-size: 19px;
  font-weight: 800;
  letter-spacing: -0.4px;
  margin: 0 0 10px;
}

.empty-state {
  padding: 12px 16px 28px;
  color: var(--text-secondary);
}

.empty-state i {
  font-size: 30px;
  margin-bottom: 12px;
  color: var(--primary);
  background: var(--primary-soft);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 56px;
  height: 56px;
  border-radius: 16px;
}

.empty-state h3 {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  margin: 0 0 4px;
}

.empty-state p {
  margin: 0;
  font-size: 13px;
}

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

@media (max-width: 640px) {
  .week-strip {
    overflow-x: auto;
    padding-bottom: 4px;
  }

  .week-day {
    min-width: 64px;
  }
}
</style>
