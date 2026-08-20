<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import * as echarts from 'echarts/core'
import { BarChart } from 'echarts/charts'
import { GridComponent, TooltipComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'
import { api } from '@/api/client'
import { brl, brdateShort } from '@/utils/format'
import AppShell from '@/components/AppShell.vue'

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer])

const periods = [
  { key: 'hoje', label: 'Hoje', icon: 'fas fa-calendar-day' },
  { key: 'ontem', label: 'Ontem', icon: 'fas fa-calendar-minus' },
  { key: '7d', label: '7 dias', icon: 'fas fa-calendar-week' },
  { key: '30d', label: '30 dias', icon: 'fas fa-calendar' },
  { key: 'mes_anterior', label: 'Mês passado', icon: 'fas fa-calendar-minus' },
]

const active = ref('7d')
const customDate = ref('')
const data = ref(null)
const loading = ref(false)
const chartEl = ref(null)
let chart = null

async function load() {
  loading.value = true
  try {
    const params = new URLSearchParams()
    if (customDate.value) params.set('date', customDate.value)
    else params.set('periodo', active.value)
    data.value = await api.get(`/dashboard?${params}`)
  } finally {
    loading.value = false
  }
}

function selectPeriod(key) {
  customDate.value = ''
  active.value = key
  load()
}

function pickDate() {
  if (customDate.value) load()
}

function renderChart() {
  if (!chartEl.value || !data.value) return
  if (!chart) chart = echarts.init(chartEl.value)
  const series = data.value.series || []
  chart.setOption(
    {
      grid: { left: 8, right: 8, top: 24, bottom: 8, containLabel: true },
      tooltip: { trigger: 'axis', valueFormatter: (v) => brl(v) },
      xAxis: {
        type: 'category',
        data: series.map((s) => s.label),
        axisLabel: { color: '#8a94a6', fontSize: 11 },
        axisLine: { lineStyle: { color: '#e5e8ef' } },
        axisTick: { show: false },
      },
      yAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#eef1f6' } },
        axisLabel: { color: '#8a94a6', fontSize: 11 },
      },
      series: [
        {
          type: 'bar',
          data: series.map((s) => Number(s.value)),
          barMaxWidth: 22,
          itemStyle: { color: '#7c5cff', borderRadius: [5, 5, 0, 0] },
        },
      ],
    },
    true
  )
}

onMounted(() => {
  load().then(renderChart)
})
watch(data, renderChart)
onBeforeUnmount(() => {
  if (chart) chart.dispose()
})
</script>

<template>
  <AppShell>
    <div class="dashboard">
      <div class="page-header">
        <div>
          <h1 class="page-title">Visão geral</h1>
          <p class="page-subtitle">Resumo do faturamento e das contas.</p>
        </div>
      </div>

      <div class="stats-toolbar">
        <div class="filter-segmented" role="group" aria-label="Período do relatório">
          <button
            v-for="p in periods"
            :key="p.key"
            type="button"
            :class="{ 'is-active': active === p.key && !customDate }"
            @click="selectPeriod(p.key)"
          >
            <i :class="p.icon"></i> {{ p.label }}
          </button>
        </div>
        <label class="date-filter" title="Dia específico">
          <i class="fas fa-calendar-alt"></i>
          <input v-model="customDate" type="date" aria-label="Dia específico" @change="pickDate" />
        </label>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="stats-row">
          <div class="stat-card">
            <span class="stat-label">Faturamento</span>
            <span class="stat-value stat-value-success">{{ brl(data.metrics.faturamento) }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Nº de vendas</span>
            <span class="stat-value">{{ data.metrics.vendas }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Ticket médio</span>
            <span class="stat-value">{{ brl(data.metrics.ticket) }}</span>
          </div>
          <div class="stat-card">
            <span class="stat-label">Lucro bruto</span>
            <span class="stat-value">{{ brl(data.metrics.lucro) }}</span>
          </div>
        </div>

        <div class="table-card chart-card">
          <div class="table-card-head">
            <h2>Vendas por dia</h2>
            <span class="chart-period-label">{{ data.period.label }}</span>
          </div>
          <div v-if="Number(data.chart_max) > 0" ref="chartEl" class="chart-echarts" role="img"></div>
          <p v-else class="chart-empty">Nenhuma venda neste período.</p>
        </div>

        <div class="home-grid">
          <div class="table-card">
            <div class="home-card-head">
              <h2>Contas em aberto</h2>
              <router-link to="/bills">Ver todas</router-link>
            </div>
            <ul class="home-list">
              <li v-for="(bill, i) in data.open_bills" :key="i">
                <span class="home-list-main">{{ bill.reference || 'Sem descrição' }}</span>
                <span class="home-list-sub">{{ brdateShort(bill.due_date) }}</span>
                <span class="home-list-value">{{ brl(bill.value) }}</span>
              </li>
              <li v-if="!data.open_bills.length" class="home-list-empty">
                Nenhuma conta em aberto.
              </li>
            </ul>
          </div>

          <div class="table-card">
            <div class="home-card-head">
              <h2>Últimas vendas</h2>
              <router-link to="/sales">Ver todas</router-link>
            </div>
            <ul class="home-list">
              <li v-for="(item, i) in data.recent_sales" :key="i">
                <span class="home-list-main">{{ brdateShort(item.date) }}</span>
                <span class="home-list-sub">{{ item.source }}</span>
                <span class="home-list-value">{{ brl(item.value) }}</span>
              </li>
              <li v-if="!data.recent_sales.length" class="home-list-empty">
                Nenhuma venda lançada.
              </li>
            </ul>
          </div>
        </div>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.chart-echarts {
  height: 260px;
  width: 100%;
}
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}
</style>