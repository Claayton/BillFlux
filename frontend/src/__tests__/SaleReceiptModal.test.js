import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
}))

vi.mock('@/api/client', () => ({ api: apiMock }))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import SaleReceiptModal from '@/views/SaleReceiptModal.vue'

const orderPayload = {
  order: {
    order_id: 42,
    date: '2026-08-24T18:41:33',
    items: [
      { name: 'Coca-Cola 2L', quantity: 2, unit_price: 9.9, subtotal: 19.8 },
      { name: 'Pão francês', quantity: 1, unit_price: 0.75, subtotal: 0.75 },
    ],
    discount: 0.55,
    total: 20,
    payments: [{ name: 'Dinheiro', amount: 50 }],
    troco: 30,
    obs: 'Entregar na portaria',
    payment_method: 'Dinheiro',
  },
}

const settingsThermal = {
  settings: {
    'receipt.width': '80',
    'receipt.header': 'Mercado Central\nRua A, 100\nCNPJ 11.222.333/0001-81',
    'receipt.footer': 'Volte sempre!',
    'pdv.auto_print': 'false',
    'company.name': 'Mercado Central',
  },
}

const settingsNoThermal = {
  settings: {
    'receipt.width': '',
    'receipt.header': '',
    'receipt.footer': '',
    'pdv.auto_print': 'false',
    'company.name': 'Mercado Central',
  },
}

let wrapper = null

function mountModal() {
  wrapper = mount(SaleReceiptModal, {
    props: { sale: { id: 42, kind: 'pdv' } },
  })
  return wrapper
}

describe('SaleReceiptModal', () => {
  let printSpy

  beforeEach(() => {
    vi.clearAllMocks()
    printSpy = vi.fn()
    window.print = printSpy
    apiMock.get.mockImplementation((path) => {
      if (path === '/settings') return Promise.resolve(settingsThermal)
      return Promise.resolve(orderPayload)
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
    delete window.print
  })

  it('sem receipt.width mostra só o recibo completo (comportamento antigo)', async () => {
    apiMock.get.mockImplementation((path) => {
      if (path === '/settings') return Promise.resolve(settingsNoThermal)
      return Promise.resolve(orderPayload)
    })
    const wrapper = mountModal()
    await flushPromises()

    expect(wrapper.find('.receipt-view-toggle').exists()).toBe(false)
    expect(wrapper.find('#sale-receipt-print').exists()).toBe(true)
    expect(wrapper.find('.receipt-thermal').exists()).toBe(false)
    expect(printSpy).not.toHaveBeenCalled()
  })

  it('com receipt.width=80 abre no cupom térmico com header, itens e rodapé', async () => {
    const wrapper = mountModal()
    await flushPromises()

    const coupon = wrapper.find('.receipt-thermal')
    expect(coupon.exists()).toBe(true)
    expect(coupon.attributes('id')).toBe('sale-receipt-print')
    expect(coupon.attributes('style')).toContain('width: 80mm')

    const toggle = wrapper.findAll('.receipt-view-toggle button')
    expect(toggle.map((b) => b.text())).toEqual(['Cupom 80 mm', 'Recibo'])
    expect(toggle[0].classes()).toContain('is-active')

    expect(coupon.text()).toContain('Mercado Central')
    expect(coupon.text()).toContain('CNPJ 11.222.333/0001-81')
    expect(coupon.text()).toContain('Venda #42')
    expect(coupon.text()).toContain('Coca-Cola 2L')
    expect(coupon.text()).toMatch(/2\s*R\$\s*9,90/)
    expect(coupon.text()).toMatch(/R\$\s*19,80/)
    expect(coupon.text()).toContain('Subtotal')
    expect(coupon.text()).toContain('Desconto')
    expect(coupon.text()).toContain('TOTAL')
    expect(coupon.text()).toMatch(/R\$\s*20,00/)
    expect(coupon.text()).toContain('Troco')
    expect(coupon.text()).toMatch(/R\$\s*30,00/)
    expect(coupon.text()).toContain('Entregar na portaria')
    expect(coupon.text()).toContain('Volte sempre!')
    expect(coupon.text()).toContain('Rua A, 100 · CNPJ 11.222.333/0001-81')
    expect(coupon.text()).toContain('TOTAL')
  })

  it('troca para o recibo completo pelo toggle', async () => {
    const wrapper = mountModal()
    await flushPromises()

    await wrapper.findAll('.receipt-view-toggle button')[1].trigger('click')

    expect(wrapper.find('.receipt-thermal').exists()).toBe(false)
    expect(wrapper.find('#sale-receipt-print').exists()).toBe(true)
    expect(wrapper.find('#sale-receipt-print').text()).toContain('Coca-Cola 2L')
  })

  it('imprime sozinho quando pdv.auto_print está ligado e não fecha o modal', async () => {
    apiMock.get.mockImplementation((path) => {
      if (path === '/settings') {
        return Promise.resolve({
          settings: { ...settingsThermal.settings, 'pdv.auto_print': 'true' },
        })
      }
      return Promise.resolve(orderPayload)
    })
    const wrapper = mountModal()
    await flushPromises()

    expect(printSpy).not.toHaveBeenCalled()
    await new Promise((r) => setTimeout(r, 320))

    expect(printSpy).toHaveBeenCalledTimes(1)
    expect(wrapper.find('.modal.is-open').exists()).toBe(true)
    expect(wrapper.emitted('close')).toBeUndefined()
  })

  it('F2 imprime e fecha o modal', async () => {
    const wrapper = mountModal()
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F2' }))
    await flushPromises()

    expect(printSpy).toHaveBeenCalledTimes(1)
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('remove a regra @page injetada ao desmontar', async () => {
    const wrapper = mountModal()
    await flushPromises()

    const styles = [...document.head.querySelectorAll('style')].filter((s) =>
      s.textContent.includes('@page')
    )
    expect(styles).toHaveLength(1)
    // fallback sem medida algura altura = largura (nunca paisagem)
    expect(styles[0].textContent).toContain('size: 80mm 80mm')

    wrapper.unmount()

    const after = [...document.head.querySelectorAll('style')].filter((s) =>
      s.textContent.includes('@page')
    )
    expect(after).toHaveLength(0)
  })
})
