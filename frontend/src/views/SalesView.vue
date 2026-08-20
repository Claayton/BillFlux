<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, brdateShort, maskMoney, moneyToDecimal } from '@/utils/format'
import AppShell from '@/components/AppShell.vue'

const periods = [
  { key: 'hoje', label: 'Hoje', icon: 'fas fa-calendar-day' },
  { key: '7d', label: '7 dias', icon: 'fas fa-calendar-week' },
  { key: 'mes', label: 'Este mês', icon: 'fas fa-calendar' },
  { key: 'mes_anterior', label: 'Mês passado', icon: 'fas fa-calendar-minus' },
]

const active = ref('hoje')
const showValues = ref(false)
const data = ref(null)
const loading = ref(false)
const saving = ref(false)

const form = ref({
  date: new Date().toISOString().slice(0, 10),
  total: '',
  obs: '',
})

const currentPeriod = computed(() => (data.value?.periods || {})[active.value])

function mask(event) {
  form.value.total = maskMoney(event.target.value)
}

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/sales')
  } finally {
    loading.value = false
  }
}

async function submit() {
  const total = moneyToDecimal(form.value.total)
  if (!form.value.date || total === null || total <= 0) {
    ElMessage.warning('Informe data e um total válido.')
    return
  }
  saving.value = true
  try {
    data.value = await api.post('/sales', {
      date: form.value.date,
      total: String(total),
      obs: form.value.obs,
    })
    form.value = {
      date: new Date().toISOString().slice(0, 10),
      total: '',
      obs: '',
    }
    ElMessage.success('Venda lançada!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function removeSale(id) {
  if (!window.confirm('Excluir esta venda?')) return
  try {
    data.value = await api.del(`/sales/${id}`)
    ElMessage.success('Venda excluída.')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function fmt(value) {
  return showValues.value ? brl(value) : 'R$ ••••'
}

onMounted(load)
</script>

<template>
  <AppShell>
    <div class="dashboard">
      <div class="page-header">
        <div>
          <h1 class="page-title">Vendas</h1>
          <p class="page-subtitle">Lançamentos avulsos e vendas do PDV.</p>
        </div>
      </div>

      <div class="stats-toolbar">
        <div class="filter-segmented" role="group" aria-label="Período das métricas">
          <button
            v-for="p in periods"
            :key="p.key"
            type="button"
            :class="{ 'is-active': active === p.key }"
            @click="active = p.key"
          >
            <i :class="p.icon"></i> {{ p.label }}
          </button>
        </div>
        <button
          type="button"
          class="icon-btn eye-btn"
          :title="showValues ? 'Ocultar valores' : 'Mostrar valores'"
          :aria-pressed="showValues ? 'true' : 'false'"
          @click="showValues = !showValues"
        >
          <i :class="showValues ? 'fas fa-eye' : 'fas fa-eye-slash'"></i>
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="stats-row">
          <div class="stat-card">
            <span class="stat-label">Total vendido</span>
            <span class="stat-value stat-value-success">{{ fmt(currentPeriod?.total) }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Nº de vendas</span>
            <span class="stat-value">{{ showValues ? currentPeriod?.count : '•••' }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Dias com venda</span>
            <span class="stat-value">{{ showValues ? currentPeriod?.days : '•••' }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Média por dia</span>
            <span class="stat-value">{{ fmt(currentPeriod?.avg) }}</span>
          </div>
        </div>

        <div class="sales-form-card">
          <div class="sales-form-head">
            <i class="fas fa-hand-holding-usd"></i>
            <div>
              <span>Lançar venda avulsa</span>
              <small>Apenas valor, sem produtos.</small>
            </div>
          </div>
          <form class="sales-form" @submit.prevent="submit">
            <div class="form-field">
              <label for="sale_date">Data</label>
              <input id="sale_date" v-model="form.date" type="date" required />
            </div>
            <div class="form-field">
              <label for="sale_total">Total bruto</label>
              <input
                id="sale_total"
                :value="form.total"
                type="text"
                placeholder="R$ 0,00"
                inputmode="decimal"
                required
                @input="mask"
              />
            </div>
            <div class="form-field">
              <label for="sale_obs">Observações (opcional)</label>
              <input id="sale_obs" v-model="form.obs" type="text" placeholder="Ex: feira, balcão..." />
            </div>
            <div class="sales-form-actions">
              <button type="submit" class="btn btn-primary" :disabled="saving">
                <i class="fas fa-check"></i> {{ saving ? 'Lançando…' : 'Lançar' }}
              </button>
            </div>
          </form>
        </div>

        <div class="table-card">
          <div class="table-card-head">
            <h2>Vendas</h2>
          </div>
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Data</th>
                  <th>Origem</th>
                  <th>Observações</th>
                  <th class="th-amount">Total</th>
                  <th class="th-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="sale in data.sales" :key="sale.kind + '-' + sale.id" class="sale-row">
                  <td>
                    <span class="cell-title">{{ brdateShort(sale.date) }}</span>
                    <span v-if="sale.date === data.today" class="cell-sub cell-today">hoje</span>
                  </td>
                  <td>
                    <span :class="sale.kind === 'pdv' ? 'source-badge source-badge-pdv' : 'source-badge source-badge-manual'">
                      <i :class="sale.kind === 'pdv' ? 'fas fa-cash-register' : 'fas fa-hand-holding-usd'"></i>
                      {{ sale.kind === 'pdv' ? 'PDV' : 'Manual' }}
                    </span>
                  </td>
                  <td class="cell-obs">{{ sale.obs || '—' }}</td>
                  <td class="cell-amount">{{ fmt(sale.total) }}</td>
                  <td class="cell-actions">
                    <a v-if="sale.kind === 'pdv'" class="icon-btn" :href="'/pdv/recibo/' + sale.id" title="Ver recibo">
                      <i class="fas fa-receipt"></i>
                    </a>
                    <button
                      v-else
                      type="button"
                      class="icon-btn is-danger"
                      title="Excluir"
                      @click="removeSale(sale.id)"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </td>
                </tr>
                <tr v-if="!data.sales.length" class="empty-row">
                  <td colspan="5" class="empty-state">
                    <i class="fas fa-cash-register"></i>
                    <h3>Nenhuma venda ainda</h3>
                    <p>Lance uma venda avulsa ou feche uma venda no PDV.</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}
.icon-btn.is-danger {
  color: #e05d5d;
}
</style>