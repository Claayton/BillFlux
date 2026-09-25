import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
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

import SuppliersView from '@/views/SuppliersView.vue'

const suppliers = [
  {
    id: 1, name: 'Spal Bebidas', cnpj: '61186888014496', phone: '1133334444',
    email: 'contato@spal.com', contact: 'Carlos', address: '', neighborhood: '',
    city: 'São Paulo', state: 'SP', obs: '', active: true,
  },
  {
    id: 2, name: 'Antiga Distribuidora', cnpj: '', phone: '', email: '',
    contact: '', address: '', neighborhood: '', city: '', state: '', obs: '',
    active: false,
  },
]

function mountView() {
  return mount(SuppliersView, {
    global: { stubs: { 'router-link': true } },
  })
}

function menuButtons() {
  return [...document.querySelectorAll('.row-menu-panel button')]
}

async function openMenu(wrapper, idx = 0) {
  await wrapper.findAll('.row-menu > .icon-btn')[idx].trigger('click')
  await flushPromises()
}

afterEach(() => {
  document.querySelectorAll('.row-menu-panel').forEach((el) => el.remove())
})

describe('SuppliersView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    apiMock.get.mockResolvedValue({ suppliers })
  })

  it('toolbar única com busca, status e CTA', async () => {
    const wrapper = mountView()
    await flushPromises()

    const toolbar = wrapper.find('.products-toolbar')
    expect(toolbar.exists()).toBe(true)
    expect(toolbar.find('.search-box input').exists()).toBe(true)
    expect(toolbar.find('.toolbar-select-status').exists()).toBe(true)
    expect(toolbar.find('.btn-brand').text()).toContain('Novo fornecedor')
  })

  it('tabela com as 7 colunas e badge de status', async () => {
    const wrapper = mountView()
    await flushPromises()

    const head = wrapper.find('thead tr').text()
    for (const col of ['Fornecedor', 'CNPJ', 'Telefone', 'Contato', 'Cidade', 'Status']) {
      expect(head).toContain(col)
    }
    const badges = wrapper.findAll('tbody tr:not(.empty-row) .status-badge').map((b) => b.text())
    expect(badges).toEqual(['Ativo', 'Inativo'])
    expect(wrapper.find('tbody').text()).toContain('61.186.888/0144-96')
  })

  it('busca filtra por nome, cnpj e telefone', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.search-box input').setValue('spal')
    await flushPromises()
    expect(wrapper.findAll('tbody tr:not(.empty-row)').length).toBe(1)

    await wrapper.find('.search-box input').setValue('1133334444')
    await flushPromises()
    expect(wrapper.findAll('tbody tr:not(.empty-row)').length).toBe(1)

    await wrapper.find('.search-box input').setValue('zzz')
    await flushPromises()
    expect(wrapper.findAll('tbody tr:not(.empty-row)').length).toBe(0)
    expect(wrapper.text()).toContain('Nenhum fornecedor encontrado')
  })

  it('filtro de status mostra só ativos ou inativos', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.toolbar-select-status').setValue('inativos')
    await flushPromises()
    let rows = wrapper.findAll('tbody tr:not(.empty-row)')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('Antiga Distribuidora')

    await wrapper.find('.toolbar-select-status').setValue('ativos')
    await flushPromises()
    rows = wrapper.findAll('tbody tr:not(.empty-row)')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('Spal Bebidas')
  })

  it('menu ⋮ com editar, toggle e excluir', async () => {
    const wrapper = mountView()
    await flushPromises()

    await openMenu(wrapper, 0)
    const items = menuButtons().map((b) => b.textContent.trim())
    expect(items).toEqual(expect.arrayContaining(['Editar', 'Desativar', 'Excluir']))
  })

  it('toggle ativa/desativa via POST', async () => {
    apiMock.post.mockResolvedValue({ suppliers })
    const wrapper = mountView()
    await flushPromises()

    await openMenu(wrapper, 1)
    const toggleBtn = menuButtons().find((b) => b.textContent.trim().startsWith('Ativar'))
    toggleBtn.click()
    await flushPromises()
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/suppliers/2/toggle')
  })

  it('excluir abre confirmação com label correto e deleta', async () => {
    apiMock.del.mockResolvedValue({ suppliers: [suppliers[0]] })
    const wrapper = mountView()
    await flushPromises()

    await openMenu(wrapper, 0)
    const delBtn = menuButtons().find((b) => b.textContent.trim().startsWith('Excluir'))
    delBtn.click()
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Excluir fornecedor')
    const confirmBtns = wrapper.findAll('.modal-footer .btn')
    await confirmBtns[confirmBtns.length - 1].trigger('click')
    await flushPromises()

    expect(apiMock.del).toHaveBeenCalledWith('/suppliers/1')
  })

  it('linha não é clicável; edição só pelo menu', async () => {
    const wrapper = mountView()
    await flushPromises()

    const row = wrapper.findAll('tbody tr:not(.empty-row)')[0]
    expect(row.attributes('style') || '').not.toContain('cursor')
    await row.trigger('click')
    await flushPromises()

    expect(wrapper.find('.modal.is-open').exists()).toBe(false)
  })
})
