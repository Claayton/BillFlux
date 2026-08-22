import { describe, it, expect, vi, beforeEach } from 'vitest'
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
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

import ProductsView from '@/views/ProductsView.vue'

const products = [
  {
    id: 3,
    name: 'Doces arildo',
    price: 5,
    cost: 2,
    barcode: '040141018496',
    secondary_code: 'SEC-1',
    category: 'Doces',
    suppliers: 'Fornecedor X',
    stock_quantity: 9,
    min_stock: 2,
    obs: '',
    active: true,
  },
]

function mountView() {
  return mount(ProductsView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('ProductsView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    apiMock.get.mockResolvedValue({ products })
  })

  it('abre o menu de ações da linha sem cortar (position fixed)', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.row-menu-btn').trigger('click')
    await nextTick()
    expect(wrapper.find('.dropdown-panel').isVisible()).toBe(true)
    expect(wrapper.find('.dropdown-panel').attributes('style')).toContain('top:')
  })

  it('editar mostra código, categoria, código secundário e fornecedores', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.row-menu-btn').trigger('click')
    await wrapper.findAll('.dropdown-item')[0].trigger('click')
    await flushPromises()

    expect(wrapper.find('input[readonly]').element.value).toBe('#3')
    expect(wrapper.find('#product_category').element.value).toBe('Doces')
    expect(wrapper.find('#product_secondary_code').element.value).toBe('SEC-1')
    expect(wrapper.find('#product_suppliers').element.value).toBe('Fornecedor X')
  })

  it('aba Transações carrega as movimentações do produto', async () => {
    apiMock.get.mockImplementation((url) => {
      if (String(url).includes('/movements')) {
        return Promise.resolve({
          movements: [{ id: 1, movement_type: 'entrada', quantity: 9, obs: 'Estoque inicial', date: '2026-08-20T10:00:00' }],
        })
      }
      return Promise.resolve({ products })
    })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.row-menu-btn').trigger('click')
    await wrapper.findAll('.dropdown-item')[0].trigger('click')
    await flushPromises()

    const tabs = wrapper.findAll('.modal-tabs button')
    await tabs[1].trigger('click')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/products/3/movements')
    expect(wrapper.text()).toContain('Estoque inicial')
    expect(wrapper.text()).toContain('+9')
  })

  it('clona o produto criando uma cópia sem códigos', async () => {
    apiMock.post.mockResolvedValue({ products })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.row-menu-btn').trigger('click')
    await wrapper.findAll('.dropdown-item')[0].trigger('click')
    await flushPromises()

    await wrapper.find('.modal-clone').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/products',
      expect.objectContaining({
        name: 'Doces arildo (cópia)',
        barcode: null,
        secondary_code: null,
        category: 'Doces',
        suppliers: 'Fornecedor X',
        stock_quantity: 0,
      })
    )
  })

  it('salva edição enviando os campos novos', async () => {
    apiMock.put.mockResolvedValue({ products })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.row-menu-btn').trigger('click')
    await wrapper.findAll('.dropdown-item')[0].trigger('click')
    await flushPromises()

    await wrapper.find('#product_category').setValue('Guloseimas')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(apiMock.put).toHaveBeenCalledWith(
      '/products/3',
      expect.objectContaining({
        category: 'Guloseimas',
        secondary_code: 'SEC-1',
        suppliers: 'Fornecedor X',
        name: 'Doces arildo',
      })
    )
  })
})
