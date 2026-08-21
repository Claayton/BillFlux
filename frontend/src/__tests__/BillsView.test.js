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
vi.mock('jsbarcode', () => ({ default: vi.fn() }))
vi.mock('qrcode-generator', () => ({
  default: () => ({ addData: vi.fn(), make: vi.fn(), createSvgTag: () => '' }),
}))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

import BillsView from '@/views/BillsView.vue'

const bills = [
  {
    id: 1,
    status: 'paga',
    reference: 'Energia',
    suplyer: 'CEMIG',
    category: 'Despesas',
    due_date: '2026-08-01',
    payday: '2026-08-01',
    value: 100,
    bar_code: null,
    pix_key: null,
    obs: null,
    date_from_add: '2026-07-01T10:00:00',
  },
  {
    id: 2,
    status: 'vencida',
    reference: 'Água',
    suplyer: 'COPASA',
    category: null,
    due_date: '2026-08-10',
    payday: null,
    value: 50.5,
    bar_code: null,
    pix_key: 'key',
    obs: 'obs',
    date_from_add: '2026-07-01T10:00:00',
  },
]

const payload = {
  today: '2026-08-21',
  stats: { open: 150.5, overdue: 50.5, paid_month: 100, total: 2 },
  account_groups: [
    { label: 'Despesas', accounts: [{ id: 1, name: 'Água e Luz', type: 'despesa' }] },
  ],
  bills,
}

describe('BillsView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    apiMock.get.mockResolvedValue(payload)
  })

  it('carrega e lista as contas', async () => {
    const wrapper = mount(BillsView)
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/bills')
    expect(wrapper.text()).toContain('Energia')
    expect(wrapper.text()).toContain('Água')
    expect(wrapper.text()).toContain('50,50')
    expect(wrapper.text()).toContain('100,00')
  })

  it('filtra por status vencida', async () => {
    const wrapper = mount(BillsView)
    await flushPromises()

    await wrapper.find('.filter-select').setValue('Vencidas')
    await flushPromises()

    const rows = wrapper.findAll('.account-row')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('Água')
  })

  it('abre o modal de pagamento ao clicar "Marcar como paga"', async () => {
    const wrapper = mount(BillsView)
    await flushPromises()

    const unpaidRow = wrapper.findAll('.account-row')[1]
    await unpaidRow.find('.row-menu-btn').trigger('click')
    await flushPromises()

    const payItem = unpaidRow
      .findAll('.dropdown-item')
      .find((el) => el.text().includes('Marcar como paga'))
    await payItem.trigger('click')
    await flushPromises()

    const payModal = wrapper.find('#pay-modal')
    expect(payModal.exists()).toBe(true)
    expect(payModal.classes()).toContain('is-open')
    expect(payModal.text()).toContain('50,50')
  })

  it('cadastra conta enviando status no payload', async () => {
    apiMock.post.mockResolvedValue(payload)
    const wrapper = mount(BillsView)
    await flushPromises()

    await wrapper.find('.page-header .btn-primary').trigger('click')
    await flushPromises()

    await wrapper.find('#bill_value').setValue('50,00')
    await wrapper.find('#bill_due').setValue('2026-09-01')
    await wrapper.find('#bill_reference').setValue('Internet')
    await wrapper.find('#bill_status').setValue(true)
    await wrapper.find('.modal-form').trigger('submit')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/bills',
      expect.objectContaining({
        value: '50',
        due_date: '2026-09-01',
        reference: 'Internet',
        status: true,
      })
    )
  })

  it('edita conta chamando PUT', async () => {
    apiMock.put.mockResolvedValue(payload)
    const wrapper = mount(BillsView)
    await flushPromises()

    const row = wrapper.findAll('.account-row')[1]
    await row.find('.row-menu-btn').trigger('click')
    await flushPromises()

    const editItem = row
      .findAll('.dropdown-item')
      .find((el) => el.text().includes('Editar'))
    await editItem.trigger('click')
    await flushPromises()

    expect(wrapper.find('.modal.is-open').text()).toContain('Editar conta')
    expect(wrapper.find('#bill_value').element.value).toBe('50,50')
    await wrapper.find('.modal-form').trigger('submit')
    await flushPromises()

    expect(apiMock.put).toHaveBeenCalledWith(
      '/bills/2',
      expect.objectContaining({ value: '50.5', status: false, reference: 'Água' })
    )
  })
})
