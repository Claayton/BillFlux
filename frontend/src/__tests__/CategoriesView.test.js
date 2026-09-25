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

import CategoriesView from '@/views/CategoriesView.vue'

const categories = [
  { id: 1, name: 'Bebidas', active: true, product_count: 5 },
  { id: 2, name: 'Antiga', active: false, product_count: 0 },
]

function mountView() {
  return mount(CategoriesView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('CategoriesView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    apiMock.get.mockResolvedValue({ categories })
  })

  it('toolbar com busca e CTA; tabela com badges', async () => {
    const wrapper = mountView()
    await flushPromises()

    const toolbar = wrapper.find('.products-toolbar')
    expect(toolbar.find('.search-box input').exists()).toBe(true)
    expect(toolbar.find('.btn-brand').text()).toContain('Nova categoria')

    const badges = wrapper.findAll('tbody tr:not(.empty-row) .status-badge').map((b) => b.text())
    expect(badges).toEqual(['Ativa', 'Inativa'])
  })

  it('busca filtra por nome', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.search-box input').setValue('beb')
    await flushPromises()
    const rows = wrapper.findAll('tbody tr:not(.empty-row)')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('Bebidas')

    await wrapper.find('.search-box input').setValue('zzz')
    await flushPromises()
    expect(wrapper.findAll('tbody tr:not(.empty-row)').length).toBe(0)
    expect(wrapper.text()).toContain('Nenhuma categoria encontrada')
  })

  it('cria categoria via POST', async () => {
    apiMock.post.mockResolvedValue({ categories })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.products-toolbar .btn-brand').trigger('click')
    await flushPromises()
    await wrapper.find('#category_name').setValue('Nova')
    await wrapper.find('.modal-form').trigger('submit')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/categories', { name: 'Nova' })
  })

  it('toggle via menu chama POST', async () => {
    apiMock.post.mockResolvedValue({ categories })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.row-menu-btn')[1].trigger('click')
    await flushPromises()
    const toggleBtn = wrapper
      .findAll('.dropdown-item')
      .find((b) => b.text().includes('Ativar'))
    await toggleBtn.trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/categories/2/toggle')
  })

  it('excluir com produtos vinculados fica desabilitado; sem vínculo deleta', async () => {
    apiMock.del.mockResolvedValue({ categories: [categories[0]] })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.row-menu-btn')[0].trigger('click')
    await flushPromises()
    const delLinked = wrapper
      .findAll('.dropdown-item')
      .find((b) => b.text().includes('Excluir'))
    expect(delLinked.attributes('disabled')).toBeDefined()

    await wrapper.findAll('.row-menu-btn')[1].trigger('click')
    await flushPromises()
    const openPanel = wrapper.findAll('.dropdown-panel').find((p) => p.isVisible())
    const delFree = openPanel
      .findAll('.dropdown-item')
      .find((b) => b.text().includes('Excluir'))
    await delFree.trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('Excluir categoria')
    const confirmBtns = wrapper.findAll('.modal-footer .btn')
    await confirmBtns[confirmBtns.length - 1].trigger('click')
    await flushPromises()

    expect(apiMock.del).toHaveBeenCalledWith('/categories/2')
  })
})
