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
import FiadoView from '@/views/FiadoView.vue'

const openReceivable = {
  id: 5,
  order_id: 42,
  customer_id: 7,
  customer_name: 'João da Silva',
  amount: 50,
  paid: 20,
  balance: 30,
  cancelled: false,
  obs: 'Venda #42',
  date: '2026-09-20T15:00:00',
}

const openPayload = {
  items: [openReceivable],
  totals: { open_amount: 30, open_count: 1, paid_count: 4, customers: 1 },
}

const paidPayload = {
  items: [
    { ...openReceivable, id: 6, paid: 15, balance: 0, customer_name: 'Maria' },
  ],
  totals: { open_amount: 30, open_count: 1, paid_count: 4, customers: 1 },
}

function mockApi() {
  apiMock.get.mockImplementation((url) => {
    const path = String(url)
    if (path.startsWith('/receivables?status=paid')) {
      return Promise.resolve(paidPayload)
    }
    if (path.startsWith('/receivables')) {
      return Promise.resolve(openPayload)
    }
    if (path.startsWith('/payments')) {
      return Promise.resolve({
        methods: [
          { id: 1, name: 'Dinheiro', active: true },
          { id: 2, name: 'PIX', active: true },
          { id: 3, name: 'Fiado', active: true },
        ],
      })
    }
    return Promise.resolve({})
  })
}

function mountView() {
  return mount(FiadoView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('FiadoView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockApi()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('carrega débitos em aberto com estatísticas e saldo', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/receivables?status=open')
    expect(wrapper.find('.fiado-stats').text()).toContain('30,00')
    expect(wrapper.find('.fiado-stats').text()).toContain('Clientes devendo')

    const row = wrapper.find('.fiado-table tbody tr')
    expect(row.text()).toContain('João da Silva')
    expect(row.text()).toContain('#42')
    expect(row.text()).toContain('Receber')
  })

  it('alternna para Quitados consultando a API com status=paid', async () => {
    const wrapper = mountView()
    await flushPromises()

    const buttons = wrapper
      .findAll('.filter-segmented button')
      .filter((b) => b.text() === 'Quitados')
    await buttons[0].trigger('click')
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/receivables?status=paid')
    expect(wrapper.find('.fiado-table tbody tr').text()).toContain('Maria')
    expect(wrapper.find('.fiado-table tbody tr').text()).toContain('Quitado')
  })

  it('busca por cliente filtra a lista no cliente', async () => {
    const wrapper = mountView()
    await flushPromises()

    const search = wrapper.find('input[aria-label="Buscar débito por cliente"]')
    await search.setValue('joão')
    await nextTick()
    const rows = wrapper.findAll('.fiado-table tbody tr')
    expect(rows).toHaveLength(1)
    expect(rows[0].text()).toContain('João da Silva')

    await search.setValue('ninguém')
    await nextTick()
    expect(wrapper.find('.empty-state').text()).toContain('Nenhum débito')
    expect(wrapper.find('.empty-state').text()).toContain('Tente buscar outro cliente.')
  })

  it('forma Fiado não aparece como opção de recebimento', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('[aria-label="Receber de João da Silva"]').trigger('click')
    await nextTick()

    const options = wrapper
      .findAll('#pay-method option')
      .map((o) => o.text())
    expect(options).toEqual(['Dinheiro', 'PIX'])
  })

  it('receber registra pagamento com o saldo total por padrão', async () => {
    apiMock.post.mockResolvedValue({
      receivable: { ...openReceivable, paid: 50, balance: 0 },
      in_caixa: true,
    })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('[aria-label="Receber de João da Silva"]').trigger('click')
    await nextTick()

    const amount = wrapper.find('#pay-amount')
    expect(amount.element.value).toBe('30,00')
    expect(wrapper.find('.confirm-summary').text()).toContain('30,00')

    await wrapper.find('.modal-footer .btn-primary').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/receivables/5/payments', {
      amount: '30.00',
      method_id: 1,
    })
    expect(ElMessage.success).toHaveBeenCalled()
    expect(apiMock.get).toHaveBeenCalledWith('/receivables?status=open')
  })

  it('bloqueia valor acima do saldo e avisa sem caixa aberto', async () => {
    apiMock.post.mockResolvedValue({
      receivable: { ...openReceivable, paid: 30, balance: 20 },
      in_caixa: false,
    })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('[aria-label="Receber de João da Silva"]').trigger('click')
    await nextTick()

    await wrapper.find('#pay-amount').setValue('999,00')
    await wrapper.find('.modal-footer .btn-primary').trigger('click')
    await nextTick()

    expect(apiMock.post).not.toHaveBeenCalled()
    expect(ElMessage.warning).toHaveBeenCalledWith(
      expect.stringContaining('acima do saldo')
    )

    await wrapper.find('#pay-amount').setValue('20,00')
    await wrapper.find('.modal-footer .btn-primary').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/receivables/5/payments', {
      amount: '20.00',
      method_id: 1,
    })
    expect(ElMessage.warning).toHaveBeenCalledWith(
      expect.stringContaining('Não há caixa aberto')
    )
  })
})
