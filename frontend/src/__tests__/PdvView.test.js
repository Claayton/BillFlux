import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

const { apiMock, routerPush } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
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
  { id: 1, name: 'Doces arildo', price: 5, stock: 9, barcode: '040141018496', units: [{ id: 1, name: 'Unidade', barcode: '', factor: 1, price: 5, is_default: true }] },
  { id: 2, name: 'Bolo de fubá', price: 3, stock: 4, barcode: null, units: [{ id: 2, name: 'Unidade', barcode: '', factor: 1, price: 3, is_default: true }] },
]
const methods = [{ id: 1, name: 'Dinheiro' }, { id: 2, name: 'PIX' }, { id: 3, name: 'Fiado' }]
const customers = [{ id: 7, name: 'João da Silva', cpf_cnpj: '123.456.789-00', active: true }]

function mountView() {
  return mount(PdvView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('PdvView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    routerPush.mockReset()
    sessionStorage.clear()
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
      return Promise.resolve({ products, methods, customers })
    })
  })

  it('não mostra aviso de caixa fechado antes de carregar', async () => {
    apiMock.get.mockImplementation((url) => {
      if (String(url).includes('/caixa')) return new Promise(() => {})
      return Promise.resolve({ products, methods, customers })
    })
    const wrapper = mountView()
    await wrapper.vm.$nextTick()
    expect(wrapper.find('.pdv-caixa-warning').exists()).toBe(false)
  })

  it('mostra aviso só quando confirmado caixa fechado', async () => {
    apiMock.get.mockImplementation((url) => {
      if (String(url).includes('/caixa')) return Promise.resolve({ open: null })
      return Promise.resolve({ products, methods, customers })
    })
    const wrapper = mountView()
    await flushPromises()
    expect(wrapper.find('.pdv-caixa-warning').exists()).toBe(true)
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
    expect(inputs).toHaveLength(1) // só a forma selecionada mostra o campo
    await inputs[0].setValue('500') // máscara -> R$ 5,00
    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/pdv/complete',
      expect.objectContaining({
        payments: [{ method_id: 1, amount: '5.00' }],
        items: [{ product_id: 1, quantity: 1, unit_id: 1 }],
        discount: 0,
      })
    )
    // recibo abre como modal, sem sair do PDV
    expect(wrapper.find('.sale-receipt-modal').exists()).toBe(true)
    expect(wrapper.text()).toContain('Recibo #7')
  })

  it('venda fiada exige cliente selecionado e envia customer_id', async () => {
    apiMock.post.mockResolvedValue({ order: { order_id: 12 } })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()
    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    // limpa o pré-preenchido e seleciona Fiado (linha 3), que recebe o restante
    await wrapper.find('.pdv-payfield input').setValue('')
    await wrapper.findAll('.pdv-payrow')[2].trigger('click')
    await nextTick()
    expect(wrapper.find('.pdv-payfield input').element.value).toBe('5,00')

    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()

    expect(ElMessage.warning).toHaveBeenCalledWith(
      'Venda fiada: selecione o cliente para gerar o débito.'
    )
    expect(apiMock.post).not.toHaveBeenCalled()

    // seleciona o cliente e a confirmação passa
    const customerInput = wrapper.find('.pdv-customer-search input')
    await customerInput.setValue('João')
    await flushPromises()
    await wrapper.find('.pdv-customer-option').trigger('click')

    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/pdv/complete',
      expect.objectContaining({
        customer_id: 7,
        payments: [{ method_id: 3, amount: '5.00' }],
      })
    )
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

    const input = () => wrapper.find('.pdv-payfield input')
    // digita 2 reais em dinheiro...
    await input().setValue('200')
    expect(input().element.value).toBe('2,00')
    // ...seta para baixo seleciona o PIX e completa o restante
    await input().trigger('keydown', { key: 'ArrowDown' })
    await nextTick()
    expect(input().element.value).toBe('3,00')

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

    expect(wrapper.find('.pdv-payfield input').element.value).toBe('5,00')
    await wrapper.find('.pdv-payfield input').trigger('keydown', { key: 'ArrowDown' })
    await nextTick()

    // o valor pulou para o PIX (linha 2), que agora é a forma selecionada
    expect(wrapper.findAll('.pdv-payrow')[1].classes()).toContain('is-selected')
    expect(wrapper.find('.pdv-payfield input').element.value).toBe('5,00')

    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()
    expect(apiMock.post).toHaveBeenCalledWith(
      '/pdv/complete',
      expect.objectContaining({
        payments: [{ method_id: 2, amount: '5.00' }],
      })
    )
  })

  it('clique na linha seleciona a forma e move o total (mouse)', async () => {
    apiMock.post.mockResolvedValue({ order: { order_id: 13 } })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()
    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    const rows = wrapper.findAll('.pdv-payrow')
    await rows[1].trigger('click') // PIX
    await nextTick()

    expect(rows[1].classes()).toContain('is-selected')
    expect(wrapper.find('.pdv-payfield input').element.value).toBe('5,00') // PIX com o total
    expect(rows[0].text()).toContain('Selecionar') // dinheiro sem valor

    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()
    expect(apiMock.post).toHaveBeenCalledWith(
      '/pdv/complete',
      expect.objectContaining({
        payments: [{ method_id: 2, amount: '5.00' }],
      })
    )
  })

  it('mostra o campo de valor só na forma selecionada', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()
    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    expect(wrapper.findAll('.pdv-payfield')).toHaveLength(1)
    expect(wrapper.findAll('.pdv-payrow')[0].find('.pdv-payfield').exists()).toBe(true)

    await wrapper.findAll('.pdv-payrow')[1].trigger('click')
    await nextTick()
    expect(wrapper.findAll('.pdv-payfield')).toHaveLength(1)
    expect(wrapper.findAll('.pdv-payrow')[1].find('.pdv-payfield').exists()).toBe(true)
    expect(wrapper.findAll('.pdv-payrow')[0].find('.pdv-payfield').exists()).toBe(false)
  })

  it('clicar na forma completa o restante quando já há valor digitado', async () => {
    apiMock.post.mockResolvedValue({ order: { order_id: 14 } })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()
    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    await wrapper.find('.pdv-payfield input').setValue('200') // 2,00 em dinheiro
    await wrapper.findAll('.pdv-payrow')[1].trigger('click') // PIX completa o restante
    await nextTick()

    expect(wrapper.find('.pdv-payfield input').element.value).toBe('3,00') // 5,00 - 2,00
    expect(wrapper.findAll('.pdv-payrow')[0].text()).toContain('2,00') // dinheiro visível

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
      return Promise.resolve({ products, methods, customers })
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
      products: [{ id: 9, name: 'Esgotado', price: 1, stock: 0, barcode: '999999999', units: [{ id: 90, name: 'Unidade', barcode: '', factor: 1, price: 1, is_default: true }] }],
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

// ---------------------------------------------------------------------------
// Comandas abertas
// ---------------------------------------------------------------------------

const tabListPayload = {
  tabs: [
    {
      id: 42,
      number: 7,
      identification: 'Mesa 2',
      status: 'open',
      total: 5,
      item_count: 1,
      units_count: 1,
      opened_at: '2026-09-28T10:00:00',
    },
  ],
}

const tabDetail = {
  tab: {
    id: 42,
    number: 7,
    identification: 'Mesa 2',
    status: 'open',
    subtotal: 5,
    discount: 0,
    total: 5,
    item_count: 1,
    units_count: 1,
    print_count: 0,
    opened_at: '2026-09-28T10:00:00',
    opened_by: 'admin',
    items: [
      {
        id: 101,
        product_id: 1,
        unit_id: 1,
        name: 'Doces arildo',
        quantity: 1,
        unit_price: 5,
        total: 5,
        factor: 1,
      },
    ],
  },
}

async function addProduct(wrapper, term) {
  await wrapper.find('#pdv-search').setValue(term)
  await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
  await nextTick()
}

function openWithActiveTab() {
  sessionStorage.setItem('pdv.active_tab', '42')
  apiMock.get.mockImplementation((url) => {
    const path = String(url)
    if (path === '/tabs/42') return Promise.resolve(tabDetail)
    if (path.startsWith('/tabs')) return Promise.resolve(tabListPayload)
    if (path.startsWith('/pdv/recibo')) {
      return Promise.resolve({
        order: {
          order_id: 99,
          date: '2026-09-28T12:00:00',
          total: 5,
          discount: 0,
          items: [],
          payments: [],
          payment_method: 'Dinheiro',
        },
      })
    }
    if (path.includes('/caixa')) {
      return Promise.resolve({ open: { id: 1, opened_by: 'test', status: 'open' } })
    }
    return Promise.resolve({ products, methods, customers })
  })
}

describe('PdvView — comandas abertas', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    routerPush.mockReset()
    sessionStorage.clear()
    apiMock.get.mockImplementation((url) => {
      const path = String(url)
      if (path.startsWith('/tabs?')) return Promise.resolve(tabListPayload)
      if (path.startsWith('/tabs/')) return Promise.resolve(tabDetail)
      if (path.includes('/caixa')) {
        return Promise.resolve({ open: { id: 1, opened_by: 'test', status: 'open' } })
      }
      return Promise.resolve({ products, methods, customers })
    })
  })

  it('F4 só abre a janela de comanda quando há itens no carrinho', async () => {
    const wrapper = mountView()
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F4' }))
    await nextTick()
    expect(wrapper.find('#tab_identification').exists()).toBe(false)

    await addProduct(wrapper, 'arildo')
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F4' }))
    await nextTick()
    expect(wrapper.find('#tab_identification').exists()).toBe(true)
    expect(wrapper.text()).toContain('Abrir comanda')
  })

  it('abre a comanda, entra no contexto e espelha o carrinho', async () => {
    apiMock.post.mockResolvedValue(tabDetail)
    const wrapper = mountView()
    await flushPromises()
    await addProduct(wrapper, 'arildo')

    await wrapper.find('.pdv-open-tab').trigger('click')
    await flushPromises()
    await wrapper.find('#tab_identification').setValue('Mesa 2')
    await wrapper.find('.tab-open-print input').setValue(false)
    const confirmOpen = wrapper
      .findAll('.modal-footer .btn-primary')
      .find((b) => b.text().includes('Abrir comanda'))
    await confirmOpen.trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/tabs', {
      identification: 'Mesa 2',
      items: [{ product_id: 1, quantity: 1, unit_id: 1 }],
    })
    // banner com a comanda ativa e carrinho igual ao servidor
    expect(wrapper.find('.pdv-tabbar').text()).toContain('Comanda #0007')
    expect(wrapper.find('.pdv-tabbar').text()).toContain('Mesa 2')
    expect(sessionStorage.getItem('pdv.active_tab')).toBe('42')
    expect(wrapper.find('#cart-count').text()).toBe('1 item')
    expect(wrapper.find('#pdv-finish').text()).toContain('Finalizar comanda')
    // sem o modal de impressão (checkbox desmarcado)
    expect(wrapper.find('.tab-ticket').exists()).toBe(false)
  })

  it('seleciona comanda da lista e carrega os itens no carrinho', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.pdv-tabs-btn').trigger('click')
    await flushPromises()
    expect(wrapper.findAll('.tab-card')).toHaveLength(1)

    await wrapper.find('.tab-card').trigger('click')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/tabs/42')
    expect(wrapper.find('.pdv-tabbar').text()).toContain('Comanda #0007')
    expect(wrapper.text()).toContain('Doces arildo')
    expect(wrapper.find('#cart-count').text()).toBe('1 item')
    expect(sessionStorage.getItem('pdv.active_tab')).toBe('42')
  })

  it('restaura a comanda ativa após recarregar a página', async () => {
    openWithActiveTab()
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.pdv-tabbar').text()).toContain('Comanda #0007')
    expect(wrapper.text()).toContain('Doces arildo')
    expect(ElMessage.info).toHaveBeenCalled()
  })

  it('cada mudança no carrinho sincroniza via PUT /tabs/:id/items', async () => {
    openWithActiveTab()
    apiMock.put.mockResolvedValue({ tab: tabDetail.tab })
    const wrapper = mountView()
    await flushPromises()

    await addProduct(wrapper, 'bolo')
    await flushPromises()

    expect(apiMock.put).toHaveBeenCalledWith('/tabs/42/items', {
      items: [
        { product_id: 1, quantity: 1, unit_id: 1 },
        { product_id: 2, quantity: 1, unit_id: 2 },
      ],
    })
  })

  it('finalizar comanda fecha via POST /tabs/:id/close sem reenviar itens', async () => {
    openWithActiveTab()
    apiMock.post.mockResolvedValue({ order: { order_id: 99 }, tab: tabDetail.tab })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()
    expect(wrapper.find('.pdv-checkout-modal').text()).toContain('Finalizar comanda')

    await wrapper.findAll('.pdv-payfield input')[0].setValue('500')
    await wrapper.find('.pdv-checkout-modal .btn-primary').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/tabs/42/close',
      expect.objectContaining({
        payments: [{ method_id: 1, amount: '5.00' }],
        discount: 0,
      })
    )
    const payload = apiMock.post.mock.calls[0][1]
    expect(payload.items).toBeUndefined()

    // contexto limpo + recibo comum da venda
    expect(wrapper.find('.pdv-tabbar').exists()).toBe(false)
    expect(sessionStorage.getItem('pdv.active_tab')).toBeNull()
    expect(wrapper.find('.sale-receipt-modal').text()).toContain('Recibo #99')
    expect(ElMessage.success).toHaveBeenCalledWith('Comanda #0007 finalizada com sucesso.')
  })

  it('cancelar comanda da lista pede confirmação e chama o endpoint', async () => {
    apiMock.post.mockResolvedValue({ tab: { ...tabDetail.tab, status: 'canceled' } })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.pdv-tabs-btn').trigger('click')
    await flushPromises()
    await wrapper.find('.tab-card-action.is-danger').trigger('click')
    await nextTick()

    expect(wrapper.find('.btn-danger').text()).toContain('Cancelar comanda')
    expect(wrapper.text()).toContain('O estoque dos itens será devolvido')

    await wrapper.find('.btn-danger').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/tabs/42/cancel', {})
    expect(ElMessage.success).toHaveBeenCalledWith('Comanda #0007 cancelada.')
    expect(wrapper.find('.tab-card').exists()).toBe(false)
  })

  it('sair da comanda libera o PDV sem fechar a comanda', async () => {
    openWithActiveTab()
    const wrapper = mountView()
    await flushPromises()

    const leave = wrapper
      .findAll('.pdv-tabbar-actions button')
      .find((b) => b.text().includes('Sair'))
    await leave.trigger('click')
    await flushPromises()

    expect(apiMock.post).not.toHaveBeenCalled()
    expect(wrapper.find('.pdv-tabbar').exists()).toBe(false)
    expect(sessionStorage.getItem('pdv.active_tab')).toBeNull()
    expect(wrapper.find('#cart-count').text()).toBe('0 itens')
    expect(wrapper.text()).toContain('Carrinho vazio')
  })

  it('mostra o botão "Comandas abertas" com a contagem', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.pdv-tabs-btn').text()).toContain('Comandas abertas')
    expect(wrapper.find('.pdv-tabs-count').text()).toBe('1')
    // sem comanda ativa o botão principal continua "Concluir venda"
    expect(wrapper.find('#pdv-finish').text()).toContain('Concluir venda')
    // "Abrir comanda" fica visível porém desabilitado com o carrinho vazio
    expect(wrapper.find('.pdv-open-tab').element.disabled).toBe(true)
    expect(wrapper.find('.pdv-tabbar').exists()).toBe(false)
  })
})
