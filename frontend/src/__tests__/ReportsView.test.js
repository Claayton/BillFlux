import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
}))

vi.mock('@/api/client', () => ({ api: apiMock }))
vi.mock('@/components/AppShell.vue', () => ({
  default: { template: '<div><slot /></div>' },
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import { ElMessage } from 'element-plus'
import ReportsView from '@/views/ReportsView.vue'

const movementsPayload = {
  movements: [
    {
      id: 1,
      product_id: 10,
      product_name: 'Açúcar',
      movement_type: 'entrada',
      quantity: 12,
      obs: 'Estoque inicial',
      created_at: '2026-09-20T10:00:00',
    },
    {
      id: 2,
      product_id: 11,
      product_name: 'Café',
      movement_type: 'saida',
      quantity: 2,
      obs: 'Venda #9',
      created_at: '2026-09-21T11:30:00',
    },
    {
      id: 3,
      product_id: 10,
      product_name: 'Açúcar',
      movement_type: 'ajuste',
      quantity: -1,
      obs: 'Inventário: contado 11',
      created_at: '2026-09-22T09:00:00',
    },
  ],
  total: 3,
  limit: 100,
  offset: 0,
}

const lowStockPayload = {
  products: [
    {
      id: 21,
      name: 'Refrigerante 2L',
      stock_quantity: 0,
      min_stock: 6,
      ideal_stock: 12,
      category_name: 'Bebidas',
      deficit: 6,
      out_of_stock: true,
    },
    {
      id: 22,
      name: 'Arroz 5kg',
      stock_quantity: 3,
      min_stock: 5,
      ideal_stock: 10,
      category_name: 'Mercearia',
      deficit: 2,
      out_of_stock: false,
    },
    {
      id: 23,
      name: 'Guaraná 2L',
      stock_quantity: -1,
      min_stock: 0,
      ideal_stock: 4,
      category_name: 'Bebidas',
      deficit: 1,
      out_of_stock: false,
    },
  ],
  count: 3,
}

const productsPayload = {
  products: [
    { id: 1, name: 'Arroz', barcode: '111', active: true, stock_quantity: 5 },
    { id: 2, name: 'Feijão', barcode: '222', active: true, stock_quantity: 2 },
    { id: 3, name: 'Inativo', barcode: null, active: false, stock_quantity: 9 },
  ],
}

function mockApi() {
  apiMock.get.mockImplementation((url) => {
    const path = String(url)
    if (path.startsWith('/reports/movements')) {
      return Promise.resolve(movementsPayload)
    }
    if (path.startsWith('/reports/low-stock')) {
      return Promise.resolve(lowStockPayload)
    }
    if (path.startsWith('/products/search')) {
      return Promise.resolve({ products: [{ id: 9, name: 'Coca-Cola' }] })
    }
    if (path.startsWith('/products')) {
      return Promise.resolve(productsPayload)
    }
    return Promise.resolve({})
  })
}

function mountView() {
  return mount(ReportsView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('ReportsView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApi()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('abre em Movimentações e renderiza linhas com tipo e saldo', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith(
      expect.stringContaining('/reports/movements?')
    )
    const rows = wrapper
      .find('[data-tab="movements"]')
      .findAll('.reports-table tbody tr')
    expect(rows).toHaveLength(3)
    expect(wrapper.text()).toContain('Açúcar')
    expect(wrapper.text()).toContain('Entrada')
    expect(wrapper.text()).toContain('Saída')
    expect(wrapper.text()).toContain('Ajuste')
    expect(wrapper.text()).toContain('3 de 3 movimentação(ões)')
  })

  it('filtro por tipo recarrega o relatório com o parâmetro', async () => {
    const wrapper = mountView()
    await flushPromises()

    const select = wrapper.find('select[aria-label="Filtrar por tipo"]')
    await select.setValue('ajuste')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith(
      expect.stringContaining('type=ajuste')
    )
  })

  it('busca de produto sugere e aplica o filtro por product_id', async () => {
    vi.useFakeTimers()
    const wrapper = mountView()
    await flushPromises()

    await wrapper
      .find('input[aria-label="Filtrar por produto"]')
      .setValue('coca')
    vi.advanceTimersByTime(300)
    await flushPromises()

    const options = wrapper.findAll('.product-results button')
    expect(options).toHaveLength(1)
    await options[0].trigger('click')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith(
      expect.stringContaining('product_id=9')
    )
    expect(wrapper.find('.product-chip').text()).toContain('Coca-Cola')
    vi.useRealTimers()
  })

  it('aba Estoque baixo lista produtos críticos com status', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.reports-tabs button')[1].trigger('click')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/reports/low-stock')
    const text = wrapper.find('[data-tab="low"]').text()
    expect(text).toContain('Refrigerante 2L')
    expect(text).toContain('Zerado')
    expect(text).toContain('Abaixo do mínimo')
    expect(text).toContain('Negativo')
    expect(text).toContain('Produtos críticos')
  })

  it('aba Inventário: contagem pendente pede confirmação e aplica', async () => {
    apiMock.post.mockResolvedValue({
      counted: 1,
      adjusted: 1,
      changes: [{ product_id: 1, name: 'Arroz', before: 5, after: 7, delta: 2 }],
    })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.reports-tabs button')[2].trigger('click')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/products')
    // produto inativo fora da contagem
    expect(wrapper.find('[data-tab="inventory"]').text()).toContain('Arroz')
    expect(wrapper.find('[data-tab="inventory"]').text()).not.toContain('Inativo')

    const applyBtn = wrapper.find('.products-toolbar .btn-brand')
    expect(applyBtn.attributes('disabled')).toBeDefined()

    const inputs = wrapper.findAll('.count-input')
    expect(inputs).toHaveLength(2)
    await inputs[0].setValue('7')
    await nextTick()

    expect(applyBtn.attributes('disabled')).toBeUndefined()
    expect(applyBtn.text()).toContain('Aplicar contagem')
    expect(applyBtn.text()).toContain('1')

    await applyBtn.trigger('click')
    await flushPromises()

    expect(wrapper.find('.confirm-summary').text()).toContain('Produtos contados')

    const confirmBtns = wrapper.findAll('.modal-footer .btn')
    await confirmBtns[confirmBtns.length - 1].trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/inventory/count', {
      items: [{ product_id: 1, counted: 7 }],
    })
    expect(ElMessage.success).toHaveBeenCalled()
  })

  it('diferença calculada mostra sinal e volta a zerar ao limpar', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.reports-tabs button')[2].trigger('click')
    await flushPromises()

    const inputs = wrapper.findAll('.count-input')
    await inputs[1].setValue('5')
    await nextTick()

    const diff = wrapper.findAll('.inventory-table tbody tr')[1].find('.col-diff')
    expect(diff.text()).toContain('+3')

    await inputs[1].setValue('')
    await nextTick()
    expect(wrapper.findAll('.inventory-table tbody tr')[1].find('.col-diff').text()).toContain('—')
  })
})
