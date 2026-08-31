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

    const statusSelect = wrapper.findAll('.filter-select').at(0)
    await statusSelect.setValue('rascunho')
    await flushPromises()

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('Fornecedor ABC')
  })

  it('filtra por busca de fornecedor', async () => {
    const wrapper = mount(PurchasesView)
    await flushPromises()

    const input = wrapper.find('.search-bar input')
    await input.setValue('ABC')
    await flushPromises()

    const rows = wrapper.findAll('tbody tr')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('Fornecedor ABC')
  })

  it('abre modal nova compra ao clicar no botão', async () => {
    const wrapper = mount(PurchasesView)
    await flushPromises()

    await wrapper.find('.page-header .btn-primary').trigger('click')
    await flushPromises()

    const modal = wrapper.find('.modal.is-open')
    expect(modal.exists()).toBe(true)
    expect(modal.text()).toContain('Nova compra')
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
})
