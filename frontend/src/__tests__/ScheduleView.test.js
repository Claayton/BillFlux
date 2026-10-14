import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { apiMock } = vi.hoisted(() => ({
  apiMock: { get: vi.fn(), post: vi.fn(), put: vi.fn(), del: vi.fn() },
}))

vi.mock('@/api/client', () => ({ api: apiMock }))
vi.mock('@/components/AppShell.vue', () => ({
  default: { template: '<div><slot /></div>' },
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import ScheduleView from '@/views/ScheduleView.vue'

const weekPayload = {
  week: [
    {
      date: '2026-11-20',
      day_name: 'sexta-feira',
      day_of_week: 4,
      is_today: true,
      supplier_count: 1,
      product_count: 2,
      suggestions: [
        {
          supplier_id: 1,
          supplier_name: 'Distribuidora X',
          critical_count: 1,
          products: [
            {
              product_id: 10,
              product_name: 'Gelo 5kg',
              current_stock: 0,
              min_stock: 2,
              ideal_stock: 10,
              suggested_qty: 10,
              avg_daily_sales: 1.5,
              coverage_days: 0,
              urgency: 'critico',
              reason: 'Sem estoque · ~0 dia(s) de cobertura',
            },
            {
              product_id: 11,
              product_name: 'Carvão 5kg',
              current_stock: 4,
              min_stock: 2,
              ideal_stock: 8,
              suggested_qty: 4,
              avg_daily_sales: 0.5,
              coverage_days: 8,
              urgency: 'abaixo_ideal',
              reason: 'Abaixo do ideal · ~8 dia(s) de cobertura',
            },
          ],
        },
      ],
    },
  ],
}

describe('ScheduleView (Agenda de reposição)', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.get.mockResolvedValue(weekPayload)
  })

  it('mostra os fornecedores do dia e os produtos a repor com o motivo', async () => {
    const wrapper = mount(ScheduleView)
    await flushPromises()

    expect(wrapper.text()).toContain('Distribuidora X')
    expect(wrapper.text()).toContain('Gelo 5kg')
    expect(wrapper.text()).toContain('Carvão 5kg')
    // resumo do dia
    expect(wrapper.text()).toContain('1 fornecedor(es)')
    expect(wrapper.text()).toContain('2 item(ns)')
    expect(wrapper.text()).toContain('1 crítico(s)')
    // motivo + urgência
    expect(wrapper.find('.urgency.is-critico').text()).toBe('Crítico')
    expect(wrapper.text()).toContain('Sem estoque')
    // botão de criar compra
    expect(wrapper.text()).toContain('Criar compra (2)')
  })

  it('cria a compra a partir das sugestões do fornecedor', async () => {
    apiMock.post.mockResolvedValue({ purchase_id: 55, items_count: 2 })
    const wrapper = mount(ScheduleView)
    await flushPromises()

    await wrapper.find('.supplier-card .btn-primary').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/schedule/create-order', { supplier_id: 1 })
  })
})