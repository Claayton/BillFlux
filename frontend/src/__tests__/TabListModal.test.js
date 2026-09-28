import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

import TabListModal from '@/components/TabListModal.vue'

const tabs = [
  {
    id: 42,
    number: 7,
    identification: 'Mesa 2',
    status: 'open',
    total: 15,
    item_count: 3,
    units_count: 4,
    opened_at: '2026-09-28T10:00:00',
  },
  {
    id: 43,
    number: 8,
    identification: 'Rapaz da Saveiro',
    status: 'open',
    total: 7.5,
    item_count: 1,
    units_count: 1,
    opened_at: '2026-09-27T18:30:00',
  },
]

let wrapper = null

function mountModal(props = {}) {
  wrapper = mount(TabListModal, {
    props: { tabs, loading: false, activeId: null, ...props },
  })
  return wrapper
}

describe('TabListModal', () => {
  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  it('lista comandas com rótulo #0007, identificação e total', () => {
    mountModal()
    const cards = wrapper.findAll('.tab-card')
    expect(cards).toHaveLength(2)
    expect(cards[0].text()).toContain('#0007')
    expect(cards[0].text()).toContain('Mesa 2')
    expect(cards[0].text()).toMatch(/R\$\s*15,00/)
    expect(wrapper.find('.tab-list-count').text()).toBe('2')
  })

  it('destaca a comanda em atendimento', () => {
    mountModal({ activeId: 43 })
    const active = wrapper.findAll('.tab-card.is-active')
    expect(active).toHaveLength(1)
    expect(active[0].text()).toContain('#0008')
    expect(active[0].text()).toContain('Em atendimento')
  })

  it('filtra por número ou identificação ignorando acento/caixa', async () => {
    mountModal()
    await wrapper.find('.tab-list-search input').setValue('saveiro')
    expect(wrapper.findAll('.tab-card')).toHaveLength(1)
    expect(wrapper.find('.tab-card').text()).toContain('Rapaz da Saveiro')

    await wrapper.find('.tab-list-search input').setValue('#0007')
    expect(wrapper.findAll('.tab-card')).toHaveLength(1)
    expect(wrapper.find('.tab-card').text()).toContain('Mesa 2')

    await wrapper.find('.tab-list-search input').setValue('999')
    expect(wrapper.findAll('.tab-card')).toHaveLength(0)
    expect(wrapper.find('.tab-list-empty').text()).toContain('Nenhuma comanda encontrada')
  })

  it('sem comandas mostra estado vazio', () => {
    mountModal({ tabs: [] })
    expect(wrapper.find('.tab-list-empty').text()).toContain('Nenhuma comanda aberta')
  })

  it('emite select ao clicar no card e print/cancel nos atalhos', async () => {
    mountModal()
    const cards = wrapper.findAll('.tab-card')
    await cards[0].trigger('click')
    expect(wrapper.emitted('select')[0][0].id).toBe(42)

    const actions = cards[1].findAll('.tab-card-action')
    await actions[0].trigger('click')
    expect(wrapper.emitted('print')[0][0].id).toBe(43)

    await actions[1].trigger('click')
    expect(wrapper.emitted('cancel')[0][0].id).toBe(43)
    // clicar no atalho NÃO seleciona a comanda
    expect(wrapper.emitted('select')).toHaveLength(1)
  })

  it('Esc fecha a lista', async () => {
    mountModal()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('mostra carregando quando loading', () => {
    mountModal({ loading: true })
    expect(wrapper.find('.tab-list-empty').text()).toContain('Carregando')
    expect(wrapper.findAll('.tab-card')).toHaveLength(0)
  })
})
