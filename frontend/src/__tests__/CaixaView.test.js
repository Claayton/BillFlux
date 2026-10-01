import { describe, it, expect, vi, beforeEach } from 'vitest'
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
vi.mock('@/components/AppShell.vue', () => ({
  default: { template: '<div><slot /></div>' },
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import { ElMessage } from 'element-plus'
import CaixaView from '@/views/CaixaView.vue'

const payloadOpen = {
  open: {
    id: 3,
    opened_by: 'coqueiral',
    opened_at: '2026-08-24 18:41:33',
    opening_amount: 100,
    closed_by: null,
    closed_at: null,
    closing_amount: null,
    expected_amount: null,
    status: 'open',
    obs: null,
  },
  last_closed: null,
  history: [
    {
      id: 2,
      opened_by: 'coqueiral',
      opened_at: '2026-08-23 08:00:00',
      opening_amount: 50,
      closed_by: 'coqueiral',
      closed_at: '2026-08-23 18:00:00',
      closing_amount: 470,
      expected_amount: 470,
      status: 'closed',
      obs: null,
    },
  ],
  system_totals: { 1: 420.5, 2: 0 },
  system_totals_named: {
    1: { method_id: 1, name: 'Dinheiro', total: 420.5 },
    2: { method_id: 2, name: 'PIX', total: 0 },
    3: { method_id: 3, name: 'Crédito', total: 0 },
  },
  payment_methods: { 1: 'Dinheiro', 2: 'PIX', 3: 'Crédito' },
}

const payloadClosed = {
  open: null,
  last_closed: null,
  history: [],
  system_totals: {},
  system_totals_named: {},
  payment_methods: { 1: 'Dinheiro', 2: 'PIX' },
}

const payloadWithMovements = {
  ...payloadOpen,
  movement_totals: { sangria: 20, suprimento: 50, entrada: 15 },
  movements: [
    {
      id: 7,
      kind: 'sangria',
      amount: 20,
      obs: 'Pagamento fornecedor',
      created_by: 'coqueiral',
      created_at: '2026-08-24 19:00:00',
    },
    {
      id: 8,
      kind: 'suprimento',
      amount: 50,
      obs: '',
      created_by: 'coqueiral',
      created_at: '2026-08-24 19:10:00',
    },
    {
      id: 9,
      kind: 'entrada',
      amount: 15,
      obs: 'Recebimento fiado: João (débito #4)',
      created_by: 'coqueiral',
      created_at: '2026-08-24 19:20:00',
    },
  ],
}

function mountView() {
  return mount(CaixaView, {
    global: {
      stubs: { 'router-link': true },
    },
  })
}

describe('CaixaView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.get.mockResolvedValue(payloadOpen)
  })

  it('status mostra caixa aberto, operador, data BR e saldo inicial', async () => {
    const wrapper = mountView()
    await flushPromises()

    const status = wrapper.find('.caixa-status-card.is-open')
    expect(status.exists()).toBe(true)
    expect(status.text()).toContain('Caixa aberto')
    expect(status.text()).toContain('coqueiral')
    expect(status.text()).toContain('24/08/2026 às 18:41')
    expect(status.text()).toContain('Saldo inicial')
    expect(status.text()).toContain('100,00')
  })

  it('resumo traz saldo inicial, vendas e saldo esperado', async () => {
    const wrapper = mountView()
    await flushPromises()

    const summary = wrapper.find('.caixa-summary')
    expect(summary.exists()).toBe(true)
    expect(summary.text()).toContain('Saldo inicial')
    expect(summary.text()).toContain('Vendas')
    expect(summary.text()).toContain('Saldo esperado')
    expect(summary.text()).toContain('520,50')
  })

  it('conferência tem cabeçalho de colunas e traduz diferenças', async () => {
    const wrapper = mountView()
    await flushPromises()

    const head = wrapper.find('.close-table-head').text()
    expect(head).toContain('Forma de pagamento')
    expect(head).toContain('Valor contado')
    expect(head).toContain('Registrado')
    expect(head).toContain('Diferença')

    const inputs = wrapper.findAll('.close-table-row .method-input input')
    await inputs[0].setValue('420,50')
    await inputs[1].setValue('0,00')
    await inputs[2].setValue('0,00')
    await flushPromises()

    const diffs = wrapper.findAll('.close-table-row .method-diff')
    expect(diffs[0].text()).toContain('✓ Correto')

    await inputs[0].setValue('400,00')
    await flushPromises()
    expect(wrapper.findAll('.close-table-row .method-diff')[0].text()).toContain(
      '20,50 faltando'
    )

    await inputs[0].setValue('430,50')
    await flushPromises()
    expect(wrapper.findAll('.close-table-row .method-diff')[0].text()).toContain(
      '10,00 sobrando'
    )
  })

  it('fechamento pede confirmação com resumo e envia payload', async () => {
    apiMock.post.mockResolvedValue(payloadClosed)
    const wrapper = mountView()
    await flushPromises()

    const inputs = wrapper.findAll('.close-table-row .method-input input')
    await inputs[0].setValue('420,50')
    await inputs[1].setValue('0,00')
    await inputs[2].setValue('0,00')
    await flushPromises()

    await wrapper.find('.close-actions .btn-brand').trigger('click')
    await flushPromises()

    expect(wrapper.find('.confirm-summary').exists()).toBe(true)
    expect(wrapper.find('.confirm-summary').text()).toContain('Valor contado')
    expect(wrapper.find('.confirm-summary').text()).toContain('Valor registrado')
    expect(wrapper.find('.confirm-summary').text()).toContain('Diferença')

    const confirmBtns = wrapper.findAll('.modal-footer .btn')
    await confirmBtns[confirmBtns.length - 1].trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/caixa/close',
      expect.objectContaining({
        closing_details: { 1: '420.5', 2: '0', 3: '0' },
      })
    )
  })

  it('fechado mostra abertura e esconde conferência', async () => {
    apiMock.get.mockResolvedValue(payloadClosed)
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.caixa-status-card.is-closed').exists()).toBe(true)
    expect(wrapper.find('.close-table').exists()).toBe(false)
    expect(wrapper.find('.caixa-summary').exists()).toBe(false)
    expect(wrapper.text()).toContain('Abrir caixa')
    expect(ElMessage.warning).not.toHaveBeenCalled()
  })

  it('resumo considera entradas/saídas e lista movimentos', async () => {
    apiMock.get.mockResolvedValue(payloadWithMovements)
    const wrapper = mountView()
    await flushPromises()

    const summary = wrapper.find('.caixa-summary')
    expect(summary.text()).toContain('Entradas')
    expect(summary.text()).toContain('Saídas')
    expect(summary.text()).toContain('Recebimentos')
    // 100 abertura + 420,50 vendas + 50 suprimento + 15 entrada − 20 sangria = 565,50
    expect(summary.text()).toContain('565,50')

    const rows = wrapper.findAll('.movement-row')
    expect(rows).toHaveLength(3)
    expect(rows[0].text()).toContain('− Sangria')
    expect(rows[0].text()).toContain('20,00')
    expect(rows[0].text()).toContain('Pagamento fornecedor')
    expect(rows[1].text()).toContain('+ Suprimento')
    expect(rows[1].text()).toContain('50,00')
    expect(rows[1].text()).toContain('Sem motivo')
    expect(rows[2].text()).toContain('+ Entrada')
    expect(rows[2].text()).toContain('15,00')
    expect(rows[2].text()).toContain('Recebimento fiado')
  })

  it('registra movimentação com valor e motivo', async () => {
    apiMock.get.mockResolvedValue(payloadWithMovements)
    apiMock.post.mockResolvedValue({ ok: true })
    const wrapper = mountView()
    await flushPromises()

    const form = wrapper.find('.movement-form')
    expect(form.exists()).toBe(true)

    await form
      .findAll('.filter-segmented button')[1]
      .trigger('click')
    await form.find('.method-input input').setValue('75,00')
    await form.find('.movement-obs').setValue('Troco do dia')
    await form.trigger('submit')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/caixa/movement', {
      kind: 'suprimento',
      amount: '75',
      obs: 'Troco do dia',
    })
    expect(ElMessage.success).toHaveBeenCalled()
    expect(apiMock.get).toHaveBeenCalledTimes(2)
  })

  it('bloqueia movimentação sem valor', async () => {
    apiMock.get.mockResolvedValue(payloadOpen)
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.movement-form').trigger('submit')
    await flushPromises()

    expect(ElMessage.warning).toHaveBeenCalledWith('Informe um valor maior que zero.')
    expect(apiMock.post).not.toHaveBeenCalled()
  })
})
