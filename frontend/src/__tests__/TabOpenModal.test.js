import { describe, it, expect, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'

import TabOpenModal from '@/components/TabOpenModal.vue'

let wrapper = null

function mountModal(props = {}) {
  wrapper = mount(TabOpenModal, {
    props: { total: 15, itemCount: 3, ...props },
  })
  return wrapper
}

describe('TabOpenModal', () => {
  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
  })

  it('mostra o total e começa com "Imprimir comanda" marcado', () => {
    mountModal()
    expect(wrapper.find('.modal.is-open').exists()).toBe(true)
    expect(wrapper.text()).toMatch(/R\$\s*15,00/)
    expect(wrapper.find('.tab-open-print input').element.checked).toBe(true)
  })

  it('confirma desabilitado sem identificação ou sem itens', async () => {
    mountModal()
    const confirm = wrapper.find('.modal-footer .btn-primary')
    expect(confirm.element.disabled).toBe(true)

    await wrapper.find('#tab_identification').setValue('Mesa 2')
    expect(confirm.element.disabled).toBe(false)

    // sem itens no carrinho não abre
    const empty = mount(TabOpenModal, { props: { total: 0, itemCount: 0 } })
    expect(empty.find('.modal-footer .btn-primary').element.disabled).toBe(true)
    empty.unmount()
  })

  it('Enter confirma com identificação aparada e print true', async () => {
    mountModal()
    await wrapper.find('#tab_identification').setValue('  Mesa 2  ')
    await wrapper.find('#tab_identification').trigger('keydown', { key: 'Enter' })

    expect(wrapper.emitted('confirm')).toHaveLength(1)
    expect(wrapper.emitted('confirm')[0][0]).toEqual({
      identification: 'Mesa 2',
      print: true,
    })
  })

  it('desmarcar a impressão envia print false', async () => {
    mountModal()
    await wrapper.find('#tab_identification').setValue('João')
    await wrapper.find('.tab-open-print input').setValue(false)
    await wrapper.find('.modal-footer .btn-primary').trigger('click')

    expect(wrapper.emitted('confirm')[0][0]).toEqual({
      identification: 'João',
      print: false,
    })
  })

  it('Esc e Cancelar emitem cancel', async () => {
    mountModal()
    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(wrapper.emitted('cancel')).toHaveLength(1)

    await wrapper.find('.modal-cancel').trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(2)
  })

  it('botão mostra "Abrindo…" e bloqueia duplo envio durante loading', async () => {
    mountModal({ loading: true })
    await wrapper.find('#tab_identification').setValue('Mesa 3')

    const confirm = wrapper.find('.modal-footer .btn-primary')
    expect(confirm.element.disabled).toBe(true)
    expect(confirm.text()).toContain('Abrindo…')
    await confirm.trigger('click')
    expect(wrapper.emitted('confirm')).toBeUndefined()
  })
})
