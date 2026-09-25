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

import PaymentsView from '@/views/PaymentsView.vue'

const methods = [
  { id: 1, name: 'Dinheiro', active: true },
  { id: 2, name: 'Antiga', active: false },
]

function mountView() {
  return mount(PaymentsView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('PaymentsView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    apiMock.get.mockResolvedValue({ methods })
  })

  it('toolbar com busca e CTA; tabela com badges', async () => {
    const wrapper = mountView()
    await flushPromises()

    const toolbar = wrapper.find('.products-toolbar')
    expect(toolbar.find('.search-box input').exists()).toBe(true)
    expect(toolbar.find('.btn-brand').text()).toContain('Nova forma')

    const badges = wrapper.findAll('tbody tr:not(.empty-row) .status-badge').map((b) => b.text())
    expect(badges).toEqual(['Ativa', 'Inativa'])
  })

  it('busca filtra por nome', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.search-box input').setValue('din')
    await flushPromises()
    expect(wrapper.findAll('tbody tr:not(.empty-row)').length).toBe(1)

    await wrapper.find('.search-box input').setValue('zzz')
    await flushPromises()
    expect(wrapper.text()).toContain('Nenhuma forma encontrada')
  })

  it('cria forma via POST', async () => {
    apiMock.post.mockResolvedValue({ methods })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.products-toolbar .btn-brand').trigger('click')
    await flushPromises()
    await wrapper.find('#method_name').setValue('Boleto')
    await wrapper.find('.modal-form').trigger('submit')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/payments', { name: 'Boleto' })
  })

  it('toggle via menu chama POST', async () => {
    apiMock.post.mockResolvedValue({ methods })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.row-menu-btn')[1].trigger('click')
    await flushPromises()
    const openPanel = wrapper.findAll('.dropdown-panel').find((p) => p.isVisible())
    const toggleBtn = openPanel
      .findAll('.dropdown-item')
      .find((b) => b.text().includes('Ativar'))
    await toggleBtn.trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/payments/2/toggle')
  })

  it('excluir usa ConfirmDialog em vez de window.confirm', async () => {
    apiMock.del.mockResolvedValue({ methods: [methods[0]] })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.row-menu-btn')[0].trigger('click')
    await flushPromises()
    const openPanel = wrapper.findAll('.dropdown-panel').find((p) => p.isVisible())
    const delBtn = openPanel
      .findAll('.dropdown-item')
      .find((b) => b.text().includes('Excluir'))
    await delBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Excluir forma de pagamento')
    const confirmBtns = wrapper.findAll('.modal-footer .btn')
    await confirmBtns[confirmBtns.length - 1].trigger('click')
    await flushPromises()

    expect(apiMock.del).toHaveBeenCalledWith('/payments/1')
  })
})
