import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

function menuButtons() {
  return [...document.querySelectorAll('.row-menu-panel button')]
}

afterEach(() => {
  vi.useRealTimers()
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
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

import PurchasesView from '@/views/PurchasesView.vue'

const purchases = [
  {
    id: 1, nf_number: '100', nf_serie: '1', nf_chave: '35260812345678000199550010000100011234567890',
    nf_modelo: '55', supplier_id: 1, supplier_name: 'Fornecedor ABC',
    total: '500.00', freight: '20.00', discount: '10.00', net_total: '510.00',
    status: 'rascunho', bill_id: null, due_date: null, obs: '', created_at: '2026-08-20T10:00:00',
  },
  {
    id: 2, nf_number: '200', nf_serie: '1', nf_chave: '', nf_modelo: '55',
    supplier_id: null, supplier_name: '',
    total: '150.00', freight: '0', discount: '0', net_total: '150.00',
    status: 'confirmada', bill_id: 1, due_date: '2026-09-01', obs: 'teste',
    created_at: '2026-08-21T10:00:00',
  },
]

describe('PurchasesView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    apiMock.get.mockResolvedValue({ purchases })
  })

  it('carrega e lista as compras', async () => {
    const wrapper = mount(PurchasesView)
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/purchases')
    expect(wrapper.text()).toContain('Fornecedor ABC')
    expect(wrapper.text()).toContain('100')
    expect(wrapper.text()).toContain('510,00')
  })

  it('filtra por status rascunho', async () => {
    const wrapper = mount(PurchasesView)
    await flushPromises()

    const statusSelect = wrapper.find('.toolbar-select-status')
    await statusSelect.setValue('rascunho')
    await flushPromises()

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('Fornecedor ABC')
  })

  it('filtra por busca de fornecedor', async () => {
    const wrapper = mount(PurchasesView)
    await flushPromises()

    const input = wrapper.find('.products-toolbar .search-box input')
    await input.setValue('ABC')
    await flushPromises()

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('Fornecedor ABC')
  })

  it('abre modal nova compra ao clicar no botão', async () => {
    const wrapper = mount(PurchasesView)
    await flushPromises()

    await wrapper.find('.page-header .btn-brand').trigger('click')
    await flushPromises()

    const modal = wrapper.find('.modal.is-open')
    expect(modal.exists()).toBe(true)
    expect(modal.text()).toContain('Nova compra')
  })

  it('menu ⋮ por status com ações corretas e chave com tooltip', async () => {
    const wrapper = mount(PurchasesView)
    await flushPromises()

    await wrapper.findAll('.row-menu > .icon-btn')[0].trigger('click')
    await flushPromises()

    const items = menuButtons().map((b) => b.textContent.trim())
    expect(items).toEqual(expect.arrayContaining(['Lançar no estoque', 'Editar', 'Excluir']))

    const chave = wrapper.find('.chave-short')
    expect(chave.attributes('title')).toContain('35260812345678000199550010000100011234567890')
  })

  it('abre modal importar NF-e', async () => {
    const wrapper = mount(PurchasesView)
    await flushPromises()

    const nfBtn = wrapper.findAll('.header-actions .btn-ghost').find(
      (b) => b.text().includes('Importar NF-e')
    )
    await nfBtn.trigger('click')
    await flushPromises()

    const modals = wrapper.findAll('.modal.is-open')
    const nfModal = modals.find((m) => m.text().includes('XML da NF-e'))
    expect(nfModal).toBeTruthy()
  })

  it('lançar compra envia os itens vinculados (product_id + fator)', async () => {
    const items = [
      {
        id: 10,
        product_id: null,
        product_name: 'CERV CX C/15',
        barcode: '789',
        quantity: 3,
        unit_cost: '35.40',
        unit_com: 'CX',
        factor: 1,
      },
    ]
    const product = {
      id: 5,
      name: 'CERV',
      stock_quantity: 0,
      cost: 0,
      units: [{ id: 50, name: 'Caixa c/ 15', factor: 15, is_default: true, price: 45 }],
    }
    apiMock.get.mockImplementation((url) => {
      const u = String(url)
      if (u === '/purchases/1') return Promise.resolve({ purchase: purchases[0], items })
      if (u.startsWith('/products/barcode/')) return Promise.resolve({ product })
      return Promise.resolve({ purchases })
    })
    apiMock.post.mockResolvedValue({ purchase: purchases[0] })
    const wrapper = mount(PurchasesView)
    await flushPromises()

    await wrapper.findAll('.row-menu > .icon-btn')[0].trigger('click')
    await flushPromises()
    const launchBtn = menuButtons().find((b) =>
      b.textContent.includes('Lançar no estoque')
    )
    launchBtn.click()
    await flushPromises()

    await wrapper.find('.btn-launch-confirm').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/purchases/1/confirm',
      expect.objectContaining({
        items: [
          expect.objectContaining({ id: 10, product_id: 5, quantity: 3, factor: 15 }),
        ],
      })
    )
  })

  it('nova compra: busca produto e adiciona item vinculado (teclado)', async () => {
    const product = { id: 5, name: 'CERV', stock_quantity: 3, cost: 2.5, price: 5, barcode: '789', active: true }
    apiMock.get.mockImplementation((url) => {
      const u = String(url)
      if (u === '/products') return Promise.resolve({ products: [product] })
      if (u === '/suppliers') return Promise.resolve({ suppliers: [] })
      return Promise.resolve({ purchases })
    })
    apiMock.post.mockResolvedValue({ purchase: purchases[0] })

    const wrapper = mount(PurchasesView)
    await flushPromises()

    await wrapper.find('.page-header .btn-brand').trigger('click')
    await flushPromises()

    const input = wrapper.find('.ps-input')
    await input.setValue('cer')
    await input.trigger('keydown', { key: 'ArrowDown' })
    await input.trigger('keydown', { key: 'Enter' })
    await flushPromises()

    const rows = wrapper.findAll('.item-row')
    expect(rows.length).toBe(1)
    expect(rows[0].find('input').element.value).toBe('CERV')

    await wrapper.find('.modal.is-open form').trigger('submit')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/purchases',
      expect.objectContaining({
        items: [expect.objectContaining({ product_id: 5, quantity: 1 })],
      })
    )
  })

  it('lançamento: padrão "Conta já paga" marcado e envia preço de venda com margem', async () => {
    const items = [
      {
        id: 10,
        product_id: 5,
        product_name: 'CERV',
        barcode: '',
        quantity: 2,
        unit_cost: '2.00',
        unit_com: '',
        factor: 1,
      },
    ]
    const product = { id: 5, name: 'CERV', stock_quantity: 0, cost: 1, price: 5, units: [] }
    apiMock.get.mockImplementation((url) => {
      const u = String(url)
      if (u === '/purchases/1') return Promise.resolve({ purchase: purchases[0], items })
      if (u === '/products/5') return Promise.resolve({ product })
      if (u === '/products') return Promise.resolve({ products: [product] })
      if (u === '/suppliers') return Promise.resolve({ suppliers: [] })
      return Promise.resolve({ purchases })
    })
    apiMock.post.mockResolvedValue({ purchase: purchases[0] })

    const wrapper = mount(PurchasesView)
    await flushPromises()

    await wrapper.findAll('.row-menu > .icon-btn')[0].trigger('click')
    await flushPromises()
    menuButtons().find((b) => b.textContent.includes('Lançar no estoque')).click()
    await flushPromises()

    const checks = wrapper.findAll('.launch-check input')
    expect(checks[0].element.checked).toBe(true) // Conta já paga
    expect(checks[1].element.checked).toBe(false) // Criar conta a pagar

    const priceInput = wrapper.find('.li-cell.is-price .li-input')
    expect(priceInput.element.value).toBe('5')
    expect(wrapper.find('.margin-badge').text()).toContain('%')

    // editar o custo unitário recalcula a margem (5 - 1)/5 = 80%
    await wrapper.find('.li-cell.is-cost .li-input').setValue('1')
    await flushPromises()
    expect(wrapper.find('.margin-badge').text()).toContain('80')

    await wrapper.find('.btn-launch-confirm').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/purchases/1/confirm',
      expect.objectContaining({
        paid: true,
        create_bill: false,
        items: [expect.objectContaining({ id: 10, price: 5 })],
      })
    )
  })
})
