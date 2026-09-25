import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { apiMock, chartMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
  chartMock: { setOption: vi.fn(), dispose: vi.fn() },
}))

vi.mock('@/api/client', () => ({ api: apiMock }))
vi.mock('@/components/AppShell.vue', () => ({
  default: { template: '<div><slot /></div>' },
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))
vi.mock('echarts/core', () => ({
  use: vi.fn(),
  init: vi.fn(() => chartMock),
}))
vi.mock('echarts/charts', () => ({ BarChart: {} }))
vi.mock('echarts/components', () => ({ GridComponent: {}, TooltipComponent: {} }))
vi.mock('echarts/renderers', () => ({ CanvasRenderer: {} }))

import DashboardView from '@/views/DashboardView.vue'

const payload = {
  metrics: { faturamento: 1000, vendas: 10, ticket: 100, lucro: 300 },
  series: [{ label: 'Seg', value: 100 }],
  chart_max: 100,
  period: { label: 'Últimos 7 dias' },
  open_bills: [{ reference: 'Luz', due_date: '2026-08-10', value: 50 }],
  recent_sales: [{ date: '2026-08-20', source: 'PDV', value: 25 }],
}

function mountView() {
  return mount(DashboardView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('DashboardView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    chartMock.setOption.mockReset()
    apiMock.get.mockResolvedValue(payload)
  })

  it('carrega métricas, gráfico e listas', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/dashboard?periodo=7d')
    expect(wrapper.findAll('.stat-card').length).toBe(4)
    expect(wrapper.findAll('.stat-card .icon-tile').length).toBe(4)
    expect(wrapper.text()).toContain('1.000,00')
    expect(wrapper.text()).toContain('Luz')
    expect(chartMock.setOption).toHaveBeenCalled()
  })

  it('troca de período recarrega com query certa', async () => {
    const wrapper = mountView()
    await flushPromises()

    const buttons = wrapper.findAll('.filter-segmented button')
    await buttons[0].trigger('click')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/dashboard?periodo=hoje')
  })

  it('sem vendas mostra empty do gráfico', async () => {
    apiMock.get.mockResolvedValue({ ...payload, chart_max: 0, series: [] })
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.text()).toContain('Nenhuma venda neste período.')
  })
})
