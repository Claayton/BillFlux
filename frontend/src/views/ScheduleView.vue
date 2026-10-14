<script setup>
import { ref, computed, onMounted } from 'vue'
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

function friendlyDate(iso) {
  if (!iso) return ''
  const d = new Date(iso + 'T12:00:00')
  if (Number.isNaN(d.getTime())) return iso
  return `${cap(WEEKDAYS_FULL[d.getDay()])}, ${d.getDate()} de ${MONTHS_FULL[d.getMonth()]}`
}

const URGENCY_LABEL = {
  critico: 'Crítico',
  abaixo_minimo: 'Abaixo do mínimo',
  abaixo_ideal: 'Abaixo do ideal',
}
function urgencyLabel(u) {
  return URGENCY_LABEL[u] || ''
}

/** Resumo do dia selecionado. */
const daySummary = computed(() => {
  const day = selectedDay.value
  if (!day) return { suppliers: 0, items: 0, critical: 0 }
  let items = 0
  let critical = 0
  for (const s of day.suggestions) {
    items += s.products.length
    critical += s.critical_count || 0
  }
  return { suppliers: day.suggestions.length, items, critical }
})

async function load() {
  loading.value = true
  try {
    const data = await api.get('/schedule/week')
    week.value = data.week || []
    const today = week.value.find((d) => d.is_today)
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
    ElMessage.success(`Compra #${res.purchase_id} criada com ${res.items_count} itens!`)
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
          <p class="page-subtitle">
            O sistema avisa quais fornecedores entregam em cada dia e o que está faltando repor.
          </p>
        </div>
      </div>

      <div v-if="loading" class="muted">Carregando...</div>

      <template v-else>
        <div class="week-strip">
          <div
            v-for="day in week" :key="day.date"
            class="week-day"
            :class="{ 'is-today': day.is_today, 'is-selected': selectedDay?.date === day.date }"
            @click="selectDay(day)"
          >
            <span class="week-day-name">{{ day.day_name.slice(0, 3) }}</span>
            <span class="week-day-num">{{ new Date(day.date + 'T12:00:00').getDate() }}</span>
            <span v-if="day.product_count > 0" class="week-day-badge">{{ day.product_count }}</span>
          </div>
        </div>

        <div v-if="selectedDay" class="schedule-content">
          <div class="schedule-head">
            <h2>{{ friendlyDate(selectedDay.date) }}</h2>
            <div v-if="daySummary.suppliers" class="day-chips">
              <span class="chip"><i class="fas fa-truck"></i> {{ daySummary.suppliers }} fornecedor(es)</span>
              <span class="chip"><i class="fas fa-box"></i> {{ daySummary.items }} item(ns)</span>
              <span v-if="daySummary.critical" class="chip is-critical">
                <i class="fas fa-triangle-exclamation"></i> {{ daySummary.critical }} crítico(s)
              </span>
            </div>
          </div>

          <div v-if="!selectedDay.suggestions.length" class="empty-state">
            <i class="fas fa-calendar-day"></i>
            <h3>Nenhum pedido sugerido</h3>
            <p>Nada para repor neste dia (ou sem vínculo de entrega/estoque ideal definido).</p>
          </div>

          <div v-else class="supplier-cards">
            <div v-for="s in selectedDay.suggestions" :key="s.supplier_id" class="supplier-card">
              <div class="supplier-card-header">
                <div>
                  <h3>{{ s.supplier_name || 'Fornecedor' }}</h3>
                  <span class="supplier-product-count">
                    {{ s.products.length }} produto(s) para repor
                    <strong v-if="s.critical_count" class="critical-text">· {{ s.critical_count }} crítico(s)</strong>
                  </span>
                </div>
                <button class="btn btn-primary btn-sm" @click="createOrder(s.supplier_id)">
                  <i class="fas fa-file-alt"></i> Criar compra ({{ s.products.length }})
                </button>
              </div>
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Produto</th>
                    <th class="th-number">Estoque</th>
                    <th class="th-number">Mín.</th>
                    <th class="th-number">Ideal</th>
                    <th class="th-number">Sugerido</th>
                    <th class="th-number">Média/dia</th>
                    <th>Por quê</th>
                  </tr>
                </thead>
                <tbody>
                  <tr
                    v-for="p in s.products"
                    :key="p.product_id"
                    :class="{ 'row-critical': p.urgency === 'critico', 'row-low': p.urgency === 'abaixo_minimo' }"
                  >
                    <td>{{ p.product_name }}</td>
                    <td class="cell-number" :class="{ 'stock-low': p.current_stock <= 0 }">{{ p.current_stock }}</td>
                    <td class="cell-number">{{ p.min_stock }}</td>
                    <td class="cell-number">{{ p.ideal_stock }}</td>
                    <td class="cell-number cell-highlight">{{ p.suggested_qty }}</td>
                    <td class="cell-number">{{ p.avg_daily_sales.toFixed(1) }}</td>
                    <td>
                      <span class="urgency" :class="'is-' + p.urgency">{{ urgencyLabel(p.urgency) }}</span>
                      <span class="reason">{{ p.reason }}</span>
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
.muted { color: var(--text-muted); padding: 24px 4px; }

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
.week-day:hover { border-color: var(--border-strong); }
.week-day.is-today { border-color: var(--primary); }
.week-day.is-selected { background: var(--brand-gradient); border-color: transparent; color: #fff; box-shadow: var(--brand-shadow-btn); }
.week-day-name { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.6px; opacity: 0.75; }
.week-day-num { font-size: 18px; font-weight: 800; letter-spacing: -0.4px; line-height: 1.2; }
.week-day-badge { background: var(--primary-soft); color: var(--primary); font-size: 11px; font-weight: 700; padding: 1px 7px; border-radius: 999px; min-width: 18px; text-align: center; }
.week-day.is-selected .week-day-badge { background: rgba(255, 255, 255, 0.25); color: #fff; }

.schedule-content { margin-top: 20px; }
.schedule-head { display: flex; align-items: center; gap: 14px; flex-wrap: wrap; margin-bottom: 12px; }
.schedule-head h2 { font-size: 19px; font-weight: 800; letter-spacing: -0.4px; margin: 0; }
.day-chips { display: flex; gap: 8px; flex-wrap: wrap; }
.chip {
  display: inline-flex; align-items: center; gap: 6px;
  padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 700;
  background: var(--surface-hover); color: var(--text-secondary);
}
.chip.is-critical { background: #fee2e2; color: #991b1b; }

.empty-state { padding: 12px 16px 28px; color: var(--text-secondary); }
.empty-state i { font-size: 30px; margin-bottom: 12px; color: var(--primary); background: var(--primary-soft); display: inline-flex; align-items: center; justify-content: center; width: 56px; height: 56px; border-radius: 16px; }
.empty-state h3 { font-size: 15px; font-weight: 700; color: var(--text); margin: 0 0 4px; }
.empty-state p { margin: 0; font-size: 13px; }

.supplier-cards { display: flex; flex-direction: column; gap: 16px; }
.supplier-card { background: var(--surface); border-radius: 12px; padding: 16px; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.supplier-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 12px; }
.supplier-card-header h3 { font-size: 16px; margin: 0; }
.supplier-product-count { font-size: 12px; color: var(--text-muted); }
.critical-text { color: #b91c1c; }

.stock-low { color: var(--danger); font-weight: 700; }
.cell-highlight { color: var(--primary); font-weight: 700; }
.row-critical td { background: color-mix(in srgb, #ef4444 8%, transparent); }
.row-low td { background: color-mix(in srgb, #f59e0b 7%, transparent); }

.urgency {
  display: inline-block; padding: 1px 8px; border-radius: 999px;
  font-size: 11px; font-weight: 700; margin-right: 8px; white-space: nowrap;
}
.urgency.is-critico { background: #fee2e2; color: #991b1b; }
.urgency.is-abaixo_minimo { background: #fef3c7; color: #92400e; }
.urgency.is-abaixo_ideal { background: var(--surface-hover); color: var(--text-secondary); }
.reason { font-size: 12px; color: var(--text-muted); }

@media (max-width: 640px) {
  .week-strip { overflow-x: auto; padding-bottom: 4px; }
  .week-day { min-width: 64px; }
}
</style>
