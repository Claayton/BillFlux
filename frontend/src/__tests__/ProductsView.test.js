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
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import ProductsView from '@/views/ProductsView.vue'

const categories = [
  { id: 1, name: 'Doces', active: true, product_count: 1 },
  { id: 2, name: 'Guloseimas', active: true, product_count: 0 },
]

const products = [
  {
    id: 3,
    name: 'Doces arildo',
    price: 5,
    cost: 2,
    barcode: '040141018496',
    secondary_code: 'SEC-1',
    category_id: 1,
    category_name: 'Doces',
    suppliers: 'Fornecedor X',
    supplier_id: 1,
    supplier_name: 'Fornecedor X',
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

// ícones diretos na linha: [Editar, Ajustar estoque, Movimentações, Excluir]
async function openEdit(wrapper) {
  await wrapper.findAll('.product-actions button')[0].trigger('click')
  await flushPromises()
}

describe('ProductsView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    apiMock.get.mockImplementation((url) => {
      if (String(url).includes('/categories')) return Promise.resolve({ categories })
      if (String(url).includes('/products')) return Promise.resolve({ products, suppliers: [{ id: 1, name: 'Fornecedor X', active: true }] })
      return Promise.resolve({ products })
    })
  })

  it('mostra ações diretas com ícones na linha', async () => {
    const wrapper = mountView()
    await flushPromises()

    const buttons = wrapper.findAll('.product-actions button')
    expect(buttons.length).toBe(4)
    expect(buttons[0].find('i').classes()).toContain('fa-pen') // Editar
    expect(buttons[3].classes()).toContain('is-danger') // Excluir
  })

  it('editar mostra código, categoria, código secundário e fornecedores', async () => {
    const wrapper = mountView()
    await flushPromises()

    await openEdit(wrapper)
    await flushPromises()

    expect(wrapper.find('input[readonly]').element.value).toBe('#3')
    expect(wrapper.find('#product_category').element.value).toBe('1')
    expect(wrapper.find('#product_secondary_code').element.value).toBe('SEC-1')
    expect(wrapper.find('#product_supplier').element.value).toBe('1')
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

    await openEdit(wrapper)

    const tabs = wrapper.findAll('.modal-tabs button')
    await tabs[1].trigger('click')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/products/3/movements')
    expect(wrapper.text()).toContain('Estoque inicial')
    expect(wrapper.text()).toContain('+9')
  })

  it('clona pré-preenchendo o formulário sem fechar o modal', async () => {
    const wrapper = mountView()
    await flushPromises()

    await openEdit(wrapper)
    await flushPromises()

    await wrapper.find('.modal-clone').trigger('click')
    await flushPromises()

    // não posta nem fecha: vira produto novo preenchido
    expect(apiMock.post).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('Novo produto')
    expect(wrapper.text()).toContain('Clonando de "Doces arildo"')
    expect(wrapper.find('#product_name').element.value).toBe('Doces arildo')
    expect(wrapper.find('#product_category').element.value).toBe('1')
    expect(wrapper.find('#product_supplier').element.value).toBe('1')
    expect(wrapper.find('#product_barcode').element.value).toBe('')
    expect(wrapper.find('#product_stock').element.value).toBe('0')

    // altera o que precisar e salva como produto novo
    await wrapper.find('#product_name').setValue('Doces arildo Lata')
    await wrapper.find('form').trigger('submit')
    await flushPromises()
    expect(apiMock.post).toHaveBeenCalledWith(
      '/products',
      expect.objectContaining({
        name: 'Doces arildo Lata',
        category_id: 1,
        supplier_id: 1,
      })
    )
  })

  it('Enter (leitor) não salva o modal; F2 salva', async () => {
    apiMock.put.mockResolvedValue({ products })
    const wrapper = mountView()
    await flushPromises()

    await openEdit(wrapper)

    // Enter em qualquer campo não dispara o salvar
    await wrapper.find('#product_name').trigger('keydown', { key: 'Enter' })
    await flushPromises()
    expect(apiMock.put).not.toHaveBeenCalled()
    expect(wrapper.find('.modal.is-open').exists()).toBe(true)

    // F2 salva
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F2' }))
    await flushPromises()
    expect(apiMock.put).toHaveBeenCalledWith('/products/3', expect.anything())
  })

  it('excluir abre modal de confirmação do sistema (sem window.confirm)', async () => {
    const confirmSpy = vi.fn()
    window.confirm = confirmSpy
    apiMock.del.mockResolvedValue({ products: [] })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.product-actions button')[3].trigger('click') // Excluir
    await nextTick()

    expect(wrapper.text()).toContain('Excluir o produto "Doces arildo"?')
    expect(confirmSpy).not.toHaveBeenCalled()

    await wrapper.find('.btn-danger').trigger('click')
    await flushPromises()
    expect(apiMock.del).toHaveBeenCalledWith('/products/3')
  })

  it('salva edição enviando os campos novos', async () => {
    apiMock.put.mockResolvedValue({ products })
    const wrapper = mountView()
    await flushPromises()

    await openEdit(wrapper)
    await flushPromises()

    await wrapper.find('#product_category').setValue('2')
    await wrapper.find('form').trigger('submit')
    await flushPromises()

    expect(apiMock.put).toHaveBeenCalledWith(
      '/products/3',
      expect.objectContaining({
        category_id: 2,
        secondary_code: 'SEC-1',
        suppliers: 'Fornecedor X',
        name: 'Doces arildo',
      })
    )
  })
})
