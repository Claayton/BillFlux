import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { apiMock, routerPush } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
  routerPush: vi.fn(),
}))

vi.mock('@/api/client', () => ({ api: apiMock }))
vi.mock('@/components/AppShell.vue', () => ({
  default: { template: '<div><slot /></div>' },
}))
vi.mock('@/views/SaleEditModal.vue', () => ({
  default: { template: '<div />' },
}))
vi.mock('@/views/SaleReceiptModal.vue', () => ({
  default: {
    props: ['sale'],
    template: '<div class="sale-receipt-stub">RECEIPT #{{ sale.id }} ({{ sale.kind }})</div>',
  },
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

import SalesView from '@/views/SalesView.vue'

const payload = {
  today: '2026-08-21',
  periods: {
    hoje: { total: 150, count: 2, days: 1, avg: 150 },
    '7d': { total: 150, count: 2, days: 1, avg: 150 },
    mes: { total: 150, count: 2, days: 1, avg: 150 },
    mes_anterior: { total: 0, count: 0, days: 0, avg: 0 },
  },
  sales: [
    {
      kind: 'pdv',
      id: 10,
      date: '2026-08-21',
      total: 50,
      obs: null,
      time: '14:30',
      items: [
        { name: 'Doces', quantity: 2 },
        { name: 'Refri', quantity: 1 },
        { name: 'Salgado', quantity: 1 },
        { name: 'Suco', quantity: 1 },
      ],
      payment: 'Dinheiro',
      cancelled: false,
    },
    {
      kind: 'manual',
      id: 5,
      date: '2026-08-20',
      total: 100,
      obs: 'Feira',
      time: null,
      items: [],
      payment: null,
      cancelled: false,
    },
    {
      kind: 'pdv',
      id: 7,
      date: '2026-08-19',
      total: 30,
      obs: null,
      time: '10:00',
      items: [{ name: 'Cancelado', quantity: 1 }],
      payment: 'PIX',
      cancelled: true,
    },
  ],
}

function mountView() {
  return mount(SalesView, {
    global: {
      stubs: { 'router-link': true },
    },
  })
}

describe('SalesView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    routerPush.mockReset()
    apiMock.get.mockResolvedValue(payload)
  })

  it('lista vendas com header, id, valor, itens e ações', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.sales-list-header').text()).toContain('Valor')
    expect(wrapper.find('.sales-list-header').text()).toContain('Origem')
    const rows = wrapper.findAll('.sale-row')
    expect(rows.length).toBe(3)
    expect(rows[0].text()).toContain('#10')
    expect(rows[0].text()).toContain('50,00')
    expect(rows[0].text()).toContain('2x Doces')
    expect(rows[0].findAll('.sale-actions .icon-btn').length).toBe(3)
    expect(rows[1].text()).toContain('#5')
    expect(rows[1].text()).toContain('Sem itens')
  })

  it('marca a venda cancelada com estilo e sem editar/cancelar', async () => {
    const wrapper = mountView()
    await flushPromises()

    const cancelledRow = wrapper.findAll('.sale-row')[2]
    expect(cancelledRow.classes()).toContain('is-cancelled')
    expect(cancelledRow.text()).toContain('Cancelada')
    // só o imprimir fica visível (1 ação)
    expect(cancelledRow.findAll('.sale-actions .icon-btn').length).toBe(1)
  })

  it('filtra vendas ativas e canceladas', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.findAll('.sale-row').length).toBe(3) // Todas

    const buttons = wrapper.findAll('.sales-filter button')
    await buttons[1].trigger('click') // Ativas
    await flushPromises()
    const active = wrapper.findAll('.sale-row')
    expect(active.length).toBe(2)
    expect(active.every((row) => !row.classes().includes('is-cancelled'))).toBe(true)

    await buttons[2].trigger('click') // Canceladas
    await flushPromises()
    const cancelled = wrapper.findAll('.sale-row')
    expect(cancelled.length).toBe(1)
    expect(cancelled[0].classes()).toContain('is-cancelled')
  })

  it('oculta somente os valores do topo, não os da lista', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.eye-btn').trigger('click')
    await flushPromises()

    const cards = wrapper.findAll('.stat-card .stat-value')
    expect(cards[0].text()).toBe('R$ ••••')
    expect(wrapper.find('.sale-value').text()).toContain('50,00')
  })

  it('abre o modal de recibo ao clicar em imprimir', async () => {
    const wrapper = mountView()
    await flushPromises()

    const printButtons = wrapper.findAll('.sale-actions .icon-btn')
    await printButtons[0].trigger('click')
    await flushPromises()

    const stub = wrapper.find('.sale-receipt-stub')
    expect(stub.exists()).toBe(true)
    expect(stub.text()).toContain('RECEIPT #10')

    // fecha o modal
    expect(routerPush).not.toHaveBeenCalled()
  })

  it('edita venda avulsa via PUT', async () => {
    apiMock.put.mockResolvedValue(payload)
    const wrapper = mountView()
    await flushPromises()

    const manualRow = wrapper.findAll('.sale-row')[1]
    await manualRow.findAll('.sale-actions .icon-btn')[1].trigger('click')
    await flushPromises()

    expect(wrapper.find('.modal.is-open').text()).toContain('Editar venda #5')
    await wrapper.find('#edit_total').setValue('120,00')
    await wrapper.find('.modal-form').trigger('submit')
    await flushPromises()

    expect(apiMock.put).toHaveBeenCalledWith(
      '/sales/5',
      expect.objectContaining({ total: '120', date: '2026-08-20' })
    )
  })

  it('cancela venda do PDV via dialog próprio (POST cancel)', async () => {
    apiMock.post.mockResolvedValue(payload)
    const wrapper = mountView()
    await flushPromises()

    const pdvRow = wrapper.findAll('.sale-row')[0]
    await pdvRow.findAll('.sale-actions .icon-btn')[2].trigger('click')
    await flushPromises()

    const dialog = wrapper.find('.confirm-body')
    expect(dialog.exists()).toBe(true)
    expect(dialog.text()).toContain('#10')

    await wrapper.find('.btn-danger').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/sales/orders/10/cancel', {})
    expect(wrapper.find('.confirm-body').exists()).toBe(false)
  })

  it('expande os itens quando há mais de 3', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.sale-items-expanded').exists()).toBe(false)
    await wrapper.find('.sale-items-more').trigger('click')
    await flushPromises()
    expect(wrapper.find('.sale-items-expanded').exists()).toBe(true)
    expect(wrapper.findAll('.sale-item-expanded').length).toBe(4)
  })
})
