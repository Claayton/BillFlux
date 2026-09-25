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

import CustomersView from '@/views/CustomersView.vue'

const customers = [
  {
    id: 1, name: 'Maria Silva', cpf_cnpj: '12345678901', phone: '11988887777',
    email: 'maria@mail.com', city: 'São Paulo', active: true,
  },
  {
    id: 2, name: 'João Antigo', cpf_cnpj: '', phone: '', email: '',
    city: '', active: false,
  },
]

function mountView() {
  return mount(CustomersView, {
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

describe('CustomersView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    apiMock.put.mockReset()
    apiMock.del.mockReset()
    apiMock.get.mockResolvedValue({ customers })
  })

  it('toolbar com busca, status e CTA; tabela com badges', async () => {
    const wrapper = mountView()
    await flushPromises()

    const toolbar = wrapper.find('.products-toolbar')
    expect(toolbar.find('.search-box input').exists()).toBe(true)
    expect(toolbar.find('.toolbar-select-status').exists()).toBe(true)
    expect(toolbar.find('.btn-brand').text()).toContain('Novo cliente')

    const head = wrapper.find('thead tr').text()
    for (const col of ['Nome', 'CPF/CNPJ', 'Telefone', 'Cidade', 'Status']) {
      expect(head).toContain(col)
    }
    const badges = wrapper.findAll('tbody tr:not(.empty-row) .status-badge').map((b) => b.text())
    expect(badges).toEqual(['Ativo', 'Inativo'])
  })

  it('busca e filtro de status', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('.search-box input').setValue('maria')
    await flushPromises()
    expect(wrapper.findAll('tbody tr:not(.empty-row)').length).toBe(1)

    await wrapper.find('.search-box input').setValue('')
    await wrapper.find('.toolbar-select-status').setValue('inativos')
    await flushPromises()
    const rows = wrapper.findAll('tbody tr:not(.empty-row)')
    expect(rows.length).toBe(1)
    expect(rows[0].text()).toContain('João Antigo')
  })

  it('menu ⋮ com histórico, editar, toggle e excluir', async () => {
    const wrapper = mountView()
    await flushPromises()

    await openMenu(wrapper, 0)
    const items = menuButtons().map((b) => b.textContent.trim())
    expect(items).toEqual(expect.arrayContaining(['Histórico', 'Editar', 'Desativar', 'Excluir']))
  })

  it('toggle via menu chama POST', async () => {
    apiMock.post.mockResolvedValue({ customers })
    const wrapper = mountView()
    await flushPromises()

    await openMenu(wrapper, 1)
    menuButtons()
      .find((b) => b.textContent.trim().startsWith('Ativar'))
      .click()
    await flushPromises()
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith('/customers/2/toggle')
  })

  it('excluir abre confirmação com label correto e deleta', async () => {
    apiMock.del.mockResolvedValue({ customers: [customers[0]] })
    const wrapper = mountView()
    await flushPromises()

    await openMenu(wrapper, 0)
    menuButtons()
      .find((b) => b.textContent.trim().startsWith('Excluir'))
      .click()
    await flushPromises()
    await flushPromises()

    expect(wrapper.text()).toContain('Excluir cliente')
    const confirmBtns = wrapper.findAll('.modal-footer .btn')
    await confirmBtns[confirmBtns.length - 1].trigger('click')
    await flushPromises()

    expect(apiMock.del).toHaveBeenCalledWith('/customers/1')
  })
})
