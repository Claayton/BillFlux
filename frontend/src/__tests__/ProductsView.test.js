import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises, DOMWrapper } from '@vue/test-utils'
import { nextTick } from 'vue'

function menuButtons() {
  return [...document.querySelectorAll('.row-menu-panel button')].map(
    (el) => new DOMWrapper(el)
  )
}

afterEach(() => {
  document.querySelectorAll('.row-menu-panel').forEach((el) => el.remove())
})

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

// ações via menu ⋮ (Teleport p/ body): abrir o menu da primeira linha e clicar em Editar
async function openEdit(wrapper) {
  await wrapper.findAll('.row-menu > .icon-btn')[0].trigger('click')
  await flushPromises()
  const editBtn = menuButtons().find((b) => b.text().includes('Editar'))
  await editBtn.trigger('click')
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

  it('mostra menu ⋮ com as 4 ações da linha', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.row-menu > .icon-btn')[0].trigger('click')
    await flushPromises()

    const items = menuButtons().map((b) => b.text())
    expect(items).toEqual(
      expect.arrayContaining(['Editar', 'Clonar', 'Ajustar estoque', 'Movimentações', 'Excluir'])
    )
    expect(
      menuButtons()
        .find((b) => b.classes().includes('is-danger'))
        .text()
    ).toContain('Excluir')
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

  it('clona direto do menu ⋮ sem abrir a edição', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.row-menu > .icon-btn')[0].trigger('click')
    await flushPromises()
    const cloneBtn = menuButtons().find((b) => b.text().includes('Clonar'))
    await cloneBtn.trigger('click')
    await flushPromises()

    expect(apiMock.post).not.toHaveBeenCalled()
    expect(wrapper.find('.modal.is-open').exists()).toBe(true)
    expect(wrapper.text()).toContain('Novo produto')
    expect(wrapper.text()).toContain('Clonando de "Doces arildo"')
    expect(wrapper.find('#product_name').element.value).toBe('Doces arildo')
    expect(wrapper.find('#product_barcode').element.value).toBe('')
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

    await wrapper.findAll('.row-menu > .icon-btn')[0].trigger('click')
    await flushPromises()
    const delBtn = menuButtons().find((b) => b.text().includes('Excluir'))
    await delBtn.trigger('click') // Excluir
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

  it('toolbar única com busca, selects e CTA, sem chips', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.products-sidebar').exists()).toBe(false)
    expect(wrapper.find('.filter-segmented').exists()).toBe(false)
    const toolbar = wrapper.find('.products-toolbar')
    expect(toolbar.exists()).toBe(true)
    expect(toolbar.find('.search-box input').exists()).toBe(true)
    expect(toolbar.findAll('.toolbar-select').length).toBe(2)
    expect(toolbar.find('.btn-brand').exists()).toBe(true)

    const catSelect = toolbar.findAll('.toolbar-select')[0]
    expect(catSelect.text()).toContain('Todas as categorias (1)')
    await catSelect.setValue(1)
    await flushPromises()
    expect(wrapper.findAll('tbody tr:not(.empty-row)').length).toBe(1)
  })

  it('busca por código de barras e mostra status de estoque', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.products-toolbar .search-box input').setValue('040141018496')
    await flushPromises()
    const rows = wrapper.findAll('tbody tr:not(.empty-row)')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('Doces arildo')
    expect(rows[0].find('.status-badge').text()).toBe('Em estoque')
  })

  it('zero sem min_stock não é sem estoque; com min_stock é', async () => {
    apiMock.get.mockImplementation((url) => {
      if (String(url).includes('/categories')) return Promise.resolve({ categories })
      return Promise.resolve({
        products: [
          {
            id: 11, name: 'Sem controle', price: 2, cost: 1, barcode: '', secondary_code: '',
            category_id: null, category_name: '', suppliers: '', supplier_id: null,
            stock_quantity: 0, min_stock: 0, ideal_stock: 0, obs: '', active: true,
          },
          {
            id: 12, name: 'Zerado rastreado', price: 3, cost: 1, barcode: '', secondary_code: '',
            category_id: null, category_name: '', suppliers: '', supplier_id: null,
            stock_quantity: 0, min_stock: 5, ideal_stock: 0, obs: '', active: true,
          },
        ],
        suppliers: [],
      })
    })
    const wrapper = mountView()
    await flushPromises()

    const badges = wrapper.findAll('tbody tr:not(.empty-row) .status-badge').map((b) => b.text())
    expect(badges).toEqual(['Em estoque', 'Sem estoque'])
  })

  it('zero sem controle mostra — neutro em vez de 0 un.', async () => {
    apiMock.get.mockImplementation((url) => {
      if (String(url).includes('/categories')) return Promise.resolve({ categories })
      return Promise.resolve({
        products: [
          {
            id: 11, name: 'Sem controle', price: 2, cost: 1, barcode: '', secondary_code: '',
            category_id: null, category_name: '', suppliers: '', supplier_id: null,
            stock_quantity: 0, min_stock: 0, ideal_stock: 0, obs: '', active: true,
          },
        ],
        suppliers: [],
      })
    })
    const wrapper = mountView()
    await flushPromises()

    const stock = wrapper.find('tbody tr:not(.empty-row) .cell-stock')
    expect(stock.text()).not.toContain('0 un.')
    expect(stock.text()).toContain('—')
  })

  it('filtro de estoque e paginação com contagem', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.table-count').text()).toContain('1 produto')
    const selects = wrapper.findAll('.toolbar-select')
    expect(selects.length).toBe(2)
    await selects[1].setValue('sem')
    await flushPromises()
    expect(wrapper.findAll('tbody tr:not(.empty-row)').length).toBe(0)
    expect(wrapper.text()).toContain('Nenhum produto encontrado')
  })

  it('esconde inativos por padrão; o check "Mostrar inativos" exibe', async () => {
    const inativo = { ...products[0], id: 9, name: 'Inativo X', active: false }
    apiMock.get.mockImplementation((url) => {
      if (String(url).includes('/categories')) return Promise.resolve({ categories })
      return Promise.resolve({ products: [...products, inativo], suppliers: [] })
    })
    const wrapper = mountView()
    await flushPromises()

    // por padrão só o ativo aparece
    expect(wrapper.findAll('tbody tr:not(.empty-row)').length).toBe(1)
    expect(wrapper.text()).not.toContain('Inativo X')
    expect(wrapper.find('.toolbar-check input').exists()).toBe(true)

    // marcando o check, o inativo aparece
    await wrapper.find('.toolbar-check input').setValue(true)
    await flushPromises()
    expect(wrapper.findAll('tbody tr:not(.empty-row)').length).toBe(2)
    expect(wrapper.text()).toContain('Inativo X')
  })
})
