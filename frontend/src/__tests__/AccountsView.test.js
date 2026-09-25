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

import AccountsView from '@/views/AccountsView.vue'

const sections = [
  {
    type: 'receita',
    label: 'Receitas',
    groups: [
      {
        account: { id: 1, name: 'Vendas', type: 'receita', color: '', parent_id: null },
        children: [
          { id: 3, name: 'Vendas balcão', type: 'receita', color: '', parent_id: 1 },
        ],
      },
    ],
  },
  { type: 'despesa', label: 'Despesas', groups: [] },
]

function mountView() {
  return mount(AccountsView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('AccountsView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    apiMock.get.mockResolvedValue({ sections })
  })

  it('lista seções com CTA em gradiente', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('.page-header .btn-brand').text()).toContain('Nova categoria')
    expect(wrapper.text()).toContain('Receitas')
    expect(wrapper.text()).toContain('Vendas')
    expect(wrapper.text()).toContain('Vendas balcão')
  })

  it('cria categoria via POST', async () => {
    apiMock.post.mockResolvedValue({ sections })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.page-header .btn-brand').trigger('click')
    await flushPromises()
    await wrapper.find('#account_name').setValue('Nova')
    await wrapper.find('.modal-form').trigger('submit')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/accounts',
      expect.objectContaining({ name: 'Nova' })
    )
  })

  it('excluir usa ConfirmDialog em vez de window.confirm', async () => {
    apiMock.del.mockResolvedValue({ sections })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('[data-menu]')[0].trigger('click')
    await flushPromises()
    const openPanel = wrapper.findAll('.dropdown-panel').find((p) => p.isVisible())
    const delBtn = openPanel
      .findAll('.dropdown-item')
      .find((b) => b.text().includes('Excluir'))
    await delBtn.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Excluir categoria')
    const confirmBtns = wrapper.findAll('.modal-footer .btn')
    await confirmBtns[confirmBtns.length - 1].trigger('click')
    await flushPromises()

    expect(apiMock.del).toHaveBeenCalledWith('/accounts/1')
  })
})
