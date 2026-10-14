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
vi.mock('@/components/ProductSearch.vue', () => ({
  default: { props: ['products'], template: '<div class="ps-stub" />' },
}))

import ScheduleView from '@/views/ScheduleView.vue'

const orders = [
  {
    id: 1,
    customer_name: 'Maria Souza',
    order_date: '2026-11-20',
    order_time: '10:00',
    status: 'pendente',
    obs: '',
    items: [{ name: 'Gelo 5kg', quantity: 2, unit_price: '30' }],
    total: '60',
  },
]

describe('ScheduleView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    apiMock.get.mockImplementation((url) => {
      const u = String(url)
      if (u.startsWith('/scheduled-orders')) return Promise.resolve({ orders })
      if (u === '/customers') return Promise.resolve({ customers: [{ id: 7, name: 'Maria Souza' }] })
      if (u === '/products') return Promise.resolve({ products: [] })
      if (u === '/schedule/week') return Promise.resolve({ week: [] })
      return Promise.resolve({})
    })
  })

  it('lista os pedidos agendados com cliente e total', async () => {
    const wrapper = mount(ScheduleView)
    await flushPromises()

    expect(wrapper.find('.schedule-table').exists()).toBe(true)
    expect(wrapper.findAll('.schedule-table tbody tr').length).toBe(1)
    expect(wrapper.text()).toContain('Maria Souza')
    expect(wrapper.text()).toMatch(/R\$\s*60,00/)
    expect(wrapper.find('.status-select').element.value).toBe('pendente')
  })

  it('abre o modal de novo pedido', async () => {
    const wrapper = mount(ScheduleView)
    await flushPromises()

    await wrapper.find('.page-header .btn-brand').trigger('click')
    await flushPromises()

    const modal = wrapper.find('.modal.is-open')
    expect(modal.exists()).toBe(true)
    expect(modal.text()).toContain('Novo pedido')
    expect(modal.text()).toContain('Cliente')
  })
})