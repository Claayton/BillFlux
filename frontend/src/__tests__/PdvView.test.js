import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

const { apiMock, routerPush } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
  },
  routerPush: vi.fn(),
}))

vi.mock('@/api/client', () => ({ api: apiMock }))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

import { ElMessage } from 'element-plus'
import PdvView from '@/views/PdvView.vue'

const products = [
  { id: 1, name: 'Doces arildo', price: 5, stock: 9, barcode: '040141018496' },
  { id: 2, name: 'Bolo de fubá', price: 3, stock: 4, barcode: null },
]
const methods = [{ id: 1, name: 'Dinheiro' }, { id: 2, name: 'PIX' }]

function mountView() {
  return mount(PdvView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('PdvView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    routerPush.mockReset()
    apiMock.get.mockImplementation((url) => {
      if (String(url).startsWith('/pdv/recibo')) {
        const id = String(url).split('/').pop()
        return Promise.resolve({
          order: {
            order_id: Number(id),
            date: '2026-08-21T12:00:00',
            total: 5,
            discount: 0,
            items: [],
            payments: [],
            payment_method: 'Dinheiro',
          },
        })
      }
      if (String(url).includes('/caixa')) {
        return Promise.resolve({
          open: { id: 1, opened_by: 'test', opening_amount: 100, status: 'open' },
        })
      }
      return Promise.resolve({ products, methods })
    })
  })

  it('carrega produtos e formas de pagamento', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/pdv')
    expect(wrapper.text()).toContain('Dinheiro')
    expect(wrapper.text()).toContain('Carrinho vazio')
  })

  it('adiciona item por busca + Enter e mostra total', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    expect(wrapper.find('#cart-count').text()).toBe('1 item')
    expect(wrapper.find('#cart-total').text()).toBe('R$ 5,00')
    expect(wrapper.text()).toContain('Doces arildo')
  })

  it('multiplicador N* define a quantidade', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('3*040141018496')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    expect(wrapper.find('#cart-count').text()).toBe('3 itens')
    expect(wrapper.find('#cart-total').text()).toBe('R$ 15,00')
  })

  it('finaliza a venda informando o valor na primeira forma', async () => {
    apiMock.post.mockResolvedValue({ order: { order_id: 7 } })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    // abre o modal de fechamento com foco pronto e digita o valor em dinheiro
    expect(wrapper.find('.pdv-checkout-modal').exists()).toBe(true)
    const inputs = wrapper.findAll('.pdv-payfield input')
    expect(inputs).toHaveLength(methods.length)
    await inputs[0].setValue('500') // máscara -> R$ 5,00
    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/pdv/complete',
      expect.objectContaining({
        payments: [{ method_id: 1, amount: '5.00' }],
        items: [{ product_id: 1, quantity: 1 }],
        discount: 0,
      })
    )
    // recibo abre como modal, sem sair do PDV
    expect(wrapper.find('.sale-receipt-modal').exists()).toBe(true)
    expect(wrapper.text()).toContain('Recibo #7')
  })

  it('divide o pagamento entre duas formas navegando com a seta', async () => {
    apiMock.post.mockResolvedValue({ order: { order_id: 8 } })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()
    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    const inputs = wrapper.findAll('.pdv-payfield input')
    // digita 2 reais em dinheiro...
    await inputs[0].setValue('200')
    expect(inputs[0].element.value).toBe('2,00')
    // ...seta para baixo vai para o PIX e digita o restante
    await inputs[0].trigger('keydown', { key: 'ArrowDown' })
    await inputs[1].setValue('300')

    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/pdv/complete',
      expect.objectContaining({
        payments: [
          { method_id: 1, amount: '2.00' },
          { method_id: 2, amount: '3.00' },
        ],
      })
    )
    expect(wrapper.find('.sale-receipt-modal').exists()).toBe(true)
    expect(wrapper.text()).toContain('Recibo #8')
  })

  it('F2 abre com Dinheiro pré-preenchido e selecionado para digitar por cima', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()
    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    const inputs = wrapper.findAll('.pdv-payfield input')
    expect(inputs[0].element.value).toBe('5,00') // total pré-preenchido
    // selecionado: digitar sobrescreve (ex: nota de 10,00 -> 1000)
    expect(inputs[0].element.selectionStart).toBe(0)
    expect(inputs[0].element.selectionEnd).toBe(4)
    await inputs[0].setValue('1000')
    expect(inputs[0].element.value).toBe('10,00')
  })

  it('seta para baixo carrega o valor pré-preenchido para a próxima forma', async () => {
    apiMock.post.mockResolvedValue({ order: { order_id: 11 } })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()
    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    const inputs = wrapper.findAll('.pdv-payfield input')
    expect(inputs[0].element.value).toBe('5,00')
    await inputs[0].trigger('keydown', { key: 'ArrowDown' })
    await nextTick()

    // o valor pulou para o PIX e o dinheiro ficou vazio
    expect(inputs[0].element.value).toBe('')
    expect(inputs[1].element.value).toBe('5,00')

    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()
    expect(apiMock.post).toHaveBeenCalledWith(
      '/pdv/complete',
      expect.objectContaining({
        payments: [{ method_id: 2, amount: '5.00' }],
      })
    )
  })

  it('não finaliza sem valor ou com valor menor que o total', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    const inputs = wrapper.findAll('.pdv-payfield input')
    // apaga o pré-preenchido: sem valor, confirmar não dispara a venda
    await inputs[0].setValue('')
    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()
    expect(apiMock.post).not.toHaveBeenCalled()

    // valor menor que o total também bloqueia
    await inputs[0].setValue('100')
    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()
    expect(apiMock.post).not.toHaveBeenCalled()
  })

  async function completeSale(wrapper, orderId = 9) {
    apiMock.post.mockResolvedValue({ order: { order_id: orderId } })
    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()
    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()
    await wrapper.findAll('.pdv-payfield input')[0].setValue('500')
    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()
  }

  it('recibo mostra quanto foi pago em cada forma e o troco', async () => {
    apiMock.get.mockImplementation((url) => {
      if (String(url).startsWith('/pdv/recibo')) {
        return Promise.resolve({
          order: {
            order_id: 21,
            date: '2026-08-21T12:00:00',
            total: 5,
            discount: 0,
            items: [],
            payments: [{ name: 'Dinheiro', amount: 10 }],
            troco: 5,
            payment_method: 'Dinheiro',
          },
        })
      }
      return Promise.resolve({ products, methods })
    })
    const wrapper = mountView()
    await flushPromises()
    await completeSale(wrapper, 21)

    expect(wrapper.find('.sale-receipt-modal').exists()).toBe(true)
    expect(wrapper.text()).toContain('Pago (Dinheiro)')
    expect(wrapper.text()).toContain('10,00')
    expect(wrapper.text()).toContain('Troco')
    expect(wrapper.text()).toContain('5,00')
  })

  it('recibo: F2 imprime e o modal fecha sozinho', async () => {
    const printSpy = vi.fn()
    window.print = printSpy
    const wrapper = mountView()
    await flushPromises()
    await completeSale(wrapper)

    expect(wrapper.find('.sale-receipt-modal').exists()).toBe(true)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F2' }))
    expect(printSpy).toHaveBeenCalled()
    await nextTick()
    expect(wrapper.find('.sale-receipt-modal').exists()).toBe(false)
  })

  it('recibo: Esc fecha o modal voltando ao PDV', async () => {
    const wrapper = mountView()
    await flushPromises()
    await completeSale(wrapper, 10)

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await nextTick()
    expect(wrapper.find('.sale-receipt-modal').exists()).toBe(false)
    expect(wrapper.find('#pdv-search').exists()).toBe(true)
  })

  it('não quebra a busca quando existe produto sem código de barras', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('040141018496')
    await nextTick()
    expect(wrapper.findAll('.pdv-suggestion').length).toBeGreaterThan(0)
  })

  it('permite vender produto sem estoque (estoque pode ficar negativo)', async () => {
    apiMock.get.mockResolvedValue({
      products: [{ id: 9, name: 'Esgotado', price: 1, stock: 0, barcode: '999999999' }],
      methods,
    })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('999999999')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    expect(wrapper.find('#cart-count').text()).toBe('1 item')
    // consegue passar do estoque atual (sem teto)
    const ctrlButtons = wrapper.findAll('.pdv-row-qty-ctrl button')
    await ctrlButtons[ctrlButtons.length - 1].trigger('click')
    await nextTick()
    expect(wrapper.find('#cart-count').text()).toBe('2 itens')
  })

  it('avisa quando o código de barras não é encontrado', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('123456789')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    expect(ElMessage.warning).toHaveBeenCalledWith('Produto não encontrado.')
  })

  it('aplica desconto percentual e recalcula o total', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    // F3 / botão Desconto abre o modal
    await wrapper.find('.pdv-discount-btn').trigger('click')
    await flushPromises()
    expect(wrapper.find('.modal.is-open').text()).toContain('Desconto')

    await wrapper.find('#discount_input').setValue('10')
    await flushPromises()
    await wrapper.find('.modal.is-open .btn-primary').trigger('click')
    await flushPromises()

    // 10% de R$ 5,00 = R$ 0,50 de desconto -> total R$ 4,50
    expect(wrapper.find('#cart-total').text()).toBe('R$ 4,50')
    expect(wrapper.find('.pdv-footer-discount').exists()).toBe(true)
  })
})
