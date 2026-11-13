import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { nextTick } from 'vue'
import { mount, flushPromises } from '@vue/test-utils'

const { apiMock, printDanfeMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    del: vi.fn(),
  },
  printDanfeMock: vi.fn(),
}))

vi.mock('@/api/client', () => ({ api: apiMock }))
vi.mock('@/utils/danfe', () => ({ printDanfe: printDanfeMock }))
vi.mock('@/utils/printBridge', () => ({
  printElementWithAgent: vi.fn(async () => false),
}))
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
    'company.name': 'Mercado Central',
  },
}

const authorizedDocument = {
  id: 9,
  order_id: 42,
  status: 'autorizada',
  series: '1',
  number: 251,
  access_key: '41260968596191000130650010000002511000002518',
  protocol: '141260000012345',
  has_danfe: true,
  error_message: '',
}

let wrapper = null

function mountModal(props = {}) {
  wrapper = mount(SaleReceiptModal, {
    props: { sale: { id: 42, kind: 'pdv' }, ...props },
    // O cupom é buscado por id no documento na hora de imprimir.
    attachTo: document.body,
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
    apiMock.post.mockResolvedValue({
      ok: true,
      status: 'autorizada',
      message: '',
      document: authorizedDocument,
    })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
    delete window.print
  })

  it('sempre usa o cupom configurado (sem opção de recibo completo)', async () => {
    apiMock.get.mockImplementation((path) => {
      if (path === '/settings') {
        return Promise.resolve({ settings: { 'receipt.width': '' } })
      }
      return Promise.resolve(orderPayload)
    })
    const wrapper = mountModal()
    await flushPromises()

    expect(wrapper.find('.receipt-view-toggle').exists()).toBe(false)
    const coupon = wrapper.find('.receipt-thermal')
    expect(coupon.exists()).toBe(true)
    expect(coupon.attributes('style')).toContain('width: 80mm')
    expect(printSpy).not.toHaveBeenCalled()
  })

  it('mostra header, itens, pagamento e rodapé configurados', async () => {
    const wrapper = mountModal()
    await flushPromises()

    const coupon = wrapper.find('.receipt-thermal')
    expect(coupon.exists()).toBe(true)
    expect(coupon.attributes('id')).toBe('sale-receipt-print')
    expect(coupon.attributes('style')).toContain('width: 80mm')

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
    expect(coupon.text()).not.toContain('Clayton')
  })

  describe('modo pós-venda', () => {
    it('sem X, sem preview do cupom e com as três ações na horizontal', async () => {
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      expect(wrapper.find('.modal-close').exists()).toBe(false)
      expect(wrapper.text()).toContain('Venda #42 finalizada')
      // Sem preview visual, mas com o cupom real escondido para imprimir.
      expect(wrapper.find('.sale-receipt-body').exists()).toBe(false)
      expect(wrapper.find('#sale-receipt-print').exists()).toBe(true)
      expect(wrapper.find('.sale-receipt-print-hidden').exists()).toBe(true)
      expect(wrapper.find('.sale-receipt-print-hidden').attributes('aria-hidden')).toBe('true')
      expect(wrapper.find('.sale-receipt-actions.is-horizontal').exists()).toBe(true)
      expect(wrapper.find('.sale-receipt-actions').text()).toContain('Imprimir comprovante')
      expect(wrapper.find('.sale-receipt-actions').text()).toContain('Emitir NFC-e')
      expect(wrapper.find('.sale-receipt-actions').text()).toContain('Concluir')
      expect(wrapper.find('.sale-receipt-hint').text()).toContain('Esc')

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
      await flushPromises()
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('P imprime o cupom real (não uma folha em branco) e fecha', async () => {
      let printedText = ''
      printSpy.mockImplementation(() => {
        printedText = document.querySelector('.receipt-print-clone')?.textContent || ''
      })
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'p' }))
      await flushPromises()

      expect(printSpy).toHaveBeenCalledTimes(1)
      expect(printedText).toContain('Coca-Cola 2L')
      expect(printedText).toContain('TOTAL')
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('P digitado num campo de texto não imprime', async () => {
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      const input = document.createElement('input')
      document.body.appendChild(input)
      input.dispatchEvent(new KeyboardEvent('keydown', { key: 'p', bubbles: true }))
      await flushPromises()
      input.remove()

      expect(printSpy).not.toHaveBeenCalled()
      expect(wrapper.emitted('close')).toBeUndefined()
    })

    it('F3 emite a NFC-e e pergunta se imprime o DANFE', async () => {
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F3' }))
      await flushPromises()

      expect(apiMock.post).toHaveBeenCalledWith('/fiscal/emitir', { order_id: 42 })
      expect(wrapper.text()).toContain('NFC-e autorizada')
      expect(wrapper.text()).toContain('Deseja imprimir o DANFE')
      expect(wrapper.find('.sale-receipt-actions .btn-primary').text()).toContain(
        'Imprimir DANFE'
      )
      // emitir não fecha: pergunta antes se imprime o DANFE
      expect(wrapper.emitted('close')).toBeUndefined()
    })

    it('setas escolhem a ação e Enter executa a escolhida', async () => {
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      expect(wrapper.find('.sale-receipt-actions .btn-outline').classes()).toContain(
        'is-selected'
      )

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight' }))
      await nextTick()
      expect(wrapper.find('.sale-receipt-actions .btn-primary').classes()).toContain(
        'is-selected'
      )

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
      await flushPromises()

      expect(apiMock.post).toHaveBeenCalledWith('/fiscal/emitir', { order_id: 42 })
      expect(wrapper.text()).toContain('Deseja imprimir o DANFE')
    })

    it('passar o mouse destaca a ação sem executar', async () => {
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      await wrapper.find('.sale-receipt-actions .btn-ghost').trigger('mouseenter')

      expect(wrapper.find('.sale-receipt-actions .btn-ghost').classes()).toContain(
        'is-selected'
      )
      expect(apiMock.post).not.toHaveBeenCalled()
      expect(wrapper.emitted('close')).toBeUndefined()
    })

    it('falha na emissão mostra o motivo e oferece tentar de novo', async () => {
      apiMock.post.mockResolvedValue({
        ok: false,
        status: 'rejeitada',
        message: 'Rejeição 539: duplicidade de NF-e',
        document: { ...authorizedDocument, status: 'rejeitada', has_danfe: false },
      })
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      await wrapper.find('.sale-receipt-actions .btn-primary').trigger('click')
      await flushPromises()

      expect(wrapper.text()).toContain('Rejeição 539: duplicidade de NF-e')
      expect(wrapper.text()).toContain('Tentar de novo')
      expect(wrapper.emitted('close')).toBeUndefined()
    })

    it('depois de autorizada, confirmar imprime o DANFE e fecha', async () => {
      printDanfeMock.mockResolvedValue(undefined)
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      await wrapper.find('.sale-receipt-actions .btn-primary').trigger('click')
      await flushPromises()
      expect(wrapper.find('.confirm-body').exists()).toBe(true)

      await wrapper.find('.modal-footer .btn-primary').trigger('click')
      await flushPromises()

      expect(printDanfeMock).toHaveBeenCalledWith(9, { widthMm: 80 })
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('depois de autorizada, recusar a impressão só fecha', async () => {
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      await wrapper.find('.sale-receipt-actions .btn-primary').trigger('click')
      await flushPromises()

      await wrapper.find('.modal-footer .modal-cancel').trigger('click')
      await flushPromises()

      expect(printDanfeMock).not.toHaveBeenCalled()
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('depois de autorizada, Enter no diálogo imprime o DANFE e fecha', async () => {
      printDanfeMock.mockResolvedValue(undefined)
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      await wrapper.find('.sale-receipt-actions .btn-primary').trigger('click')
      await flushPromises()

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
      await flushPromises()

      expect(printDanfeMock).toHaveBeenCalledWith(9, { widthMm: 80 })
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('depois de autorizada, P no diálogo imprime o DANFE e fecha', async () => {
      printDanfeMock.mockResolvedValue(undefined)
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      await wrapper.find('.sale-receipt-actions .btn-primary').trigger('click')
      await flushPromises()

      expect(wrapper.find('.modal-footer .modal-cancel').text()).toContain('Esc')
      expect(wrapper.find('.modal-footer .btn-primary').text()).toContain('P')

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'p' }))
      await flushPromises()

      expect(printDanfeMock).toHaveBeenCalledWith(9, { widthMm: 80 })
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('depois de autorizada, Esc no diálogo não imprime e fecha', async () => {
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      await wrapper.find('.sale-receipt-actions .btn-primary').trigger('click')
      await flushPromises()

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
      await flushPromises()

      expect(printDanfeMock).not.toHaveBeenCalled()
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('no diálogo, setas escolhem e Enter executa a escolha', async () => {
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      await wrapper.find('.sale-receipt-actions .btn-primary').trigger('click')
      await flushPromises()

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowLeft' }))
      await nextTick()
      expect(wrapper.find('.modal-footer .modal-cancel').classes()).toContain('is-selected')

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Enter' }))
      await flushPromises()

      expect(printDanfeMock).not.toHaveBeenCalled()
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('imprimir cupom sem emitir imprime e fecha', async () => {
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      await wrapper.find('.sale-receipt-actions .btn-outline').trigger('click')
      await flushPromises()

      expect(printSpy).toHaveBeenCalledTimes(1)
      expect(wrapper.emitted('close')).toHaveLength(1)
      expect(apiMock.post).not.toHaveBeenCalled()
    })

    it('F2 fecha como nova venda', async () => {
      const wrapper = mountModal({ mode: 'post-sale' })
      await flushPromises()

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F2' }))
      await flushPromises()

      expect(wrapper.emitted('close')).toHaveLength(1)
      expect(printSpy).not.toHaveBeenCalled()
    })
  })

  describe('reimpressão em Vendas', () => {
    it('P imprime o cupom e fecha', async () => {
      const wrapper = mountModal()
      await flushPromises()

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'P' }))
      await flushPromises()

      expect(printSpy).toHaveBeenCalledTimes(1)
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('F2 imprime o cupom e fecha', async () => {
      const wrapper = mountModal()
      await flushPromises()

      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F2' }))
      await flushPromises()

      expect(printSpy).toHaveBeenCalledTimes(1)
      expect(wrapper.emitted('close')).toHaveLength(1)
    })

    it('venda autorizada imprime o DANFE direto', async () => {
      printDanfeMock.mockResolvedValue(undefined)
      const wrapper = mountModal({
        sale: {
          id: 42,
          kind: 'pdv',
          fiscal: { id: 9, status: 'autorizada', has_danfe: true },
        },
      })
      await flushPromises()

      expect(wrapper.find('.modal-footer .btn-primary').text()).toContain('Imprimir DANFE')
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F2' }))
      await flushPromises()

      expect(printDanfeMock).toHaveBeenCalledWith(9, { widthMm: 80 })
    })
  })

  it('remove a regra @page injetada ao desmontar', async () => {
    const wrapper = mountModal()
    await flushPromises()

    const styles = [...document.head.querySelectorAll('style')].filter((s) =>
      s.textContent.includes('@page')
    )
    expect(styles).toHaveLength(1)
    expect(styles[0].textContent).toContain('size: 80mm 80mm')

    wrapper.unmount()

    const after = [...document.head.querySelectorAll('style')].filter((s) =>
      s.textContent.includes('@page')
    )
    expect(after).toHaveLength(0)
  })
})
