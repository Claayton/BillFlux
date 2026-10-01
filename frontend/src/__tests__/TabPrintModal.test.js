import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'

const { apiMock } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
  },
}))

vi.mock('@/api/client', () => ({ api: apiMock }))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import TabPrintModal from '@/components/TabPrintModal.vue'

const tab = {
  id: 42,
  number: 7,
  identification: 'Mesa 2',
  status: 'open',
  total: 19.8,
  item_count: 3,
  units_count: 3,
  print_count: 0,
  opened_at: '2026-09-28T10:00:00',
  opened_by: 'admin',
  items: [
    { id: 101, product_id: 1, unit_id: 1, name: 'Doces arildo', quantity: 2, unit_price: 5, total: 10, factor: 1 },
    { id: 102, product_id: 2, unit_id: 2, name: 'Bolo de fubá', quantity: 1, unit_price: 9.8, total: 9.8, factor: 1 },
  ],
}

let wrapper = null
let printSpy = null

function mountModal(tabProps = tab) {
  wrapper = mount(TabPrintModal, { props: { tab: tabProps } })
  return wrapper
}

describe('TabPrintModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    printSpy = vi.fn()
    window.print = printSpy
    apiMock.get.mockResolvedValue({
      settings: {
        'receipt.width': '58',
        'receipt.header': 'Mercado Central\nRua A, 100',
        'company.name': 'Mercado Central',
      },
    })
    apiMock.post.mockResolvedValue({ tab: { id: 42, print_count: 1 } })
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
      wrapper = null
    }
    delete window.print
  })

  it('renderiza o cupom com empresa, comanda #0007 e itens', async () => {
    mountModal()
    await flushPromises()

    const ticket = wrapper.find('#tab-print')
    expect(ticket.exists()).toBe(true)
    expect(ticket.attributes('style')).toContain('width: 58mm')
    expect(ticket.text()).toContain('Mercado Central')
    expect(ticket.text()).toContain('COMANDA #0007')
    expect(ticket.text()).toContain('Mesa 2')
    expect(ticket.text()).toContain('2x Doces arildo')
    expect(ticket.text()).toContain('Bolo de fubá')
    expect(ticket.text()).toContain('LANÇADO NO SISTEMA')
    expect(ticket.text()).toMatch(/R\$\s*19,80/)
    expect(ticket.text()).toContain('ADICIONAIS / ANOTAÇÕES')
    expect(ticket.text()).toContain('Atendente: ___________________________')
    expect(ticket.text()).toContain('Lançado por: admin')
  })

  it('não mostra REIMPRESSÃO na primeira via nem na reimpressão', async () => {
    mountModal()
    await flushPromises()
    expect(wrapper.find('.tab-ticket-reprint').exists()).toBe(false)

    const reprint = mount(TabPrintModal, {
      props: { tab: { ...tab, print_count: 2 } },
    })
    await flushPromises()
    expect(reprint.find('.tab-ticket-reprint').exists()).toBe(true)
    expect(reprint.find('.modal-header h2').text()).toContain('Comanda #0007')
    reprint.unmount()
  })

  it('imprime sozinho ao abrir (opção "Imprimir comanda") e registra a contagem', async () => {
    mountModal()
    await flushPromises()

    expect(printSpy).not.toHaveBeenCalled()
    await new Promise((r) => setTimeout(r, 320))

    expect(printSpy).toHaveBeenCalledTimes(1)
    expect(apiMock.post).toHaveBeenCalledWith('/tabs/42/print')
    expect(wrapper.emitted('printed')).toHaveLength(1)
    // continua aberto para reimpressão manual
    expect(wrapper.find('.modal.is-open').exists()).toBe(true)
    expect(wrapper.emitted('close')).toBeUndefined()
  })

  it('F2 reimprime e Esc fecha', async () => {
    mountModal()
    await flushPromises()

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'F2' }))
    await flushPromises()

    expect(printSpy).toHaveBeenCalledTimes(1)
    expect(apiMock.post).toHaveBeenCalledWith('/tabs/42/print')

    document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    expect(wrapper.emitted('close')).toHaveLength(1)
  })

  it('injeta @page com a largura térmica e remove ao desmontar', async () => {
    mountModal()
    await flushPromises()

    const styles = [...document.head.querySelectorAll('style')].filter((s) =>
      s.textContent.includes('@page')
    )
    expect(styles).toHaveLength(1)
    expect(styles[0].textContent).toContain('size: 58mm')

    wrapper.unmount()
    wrapper = null

    const after = [...document.head.querySelectorAll('style')].filter((s) =>
      s.textContent.includes('@page')
    )
    expect(after).toHaveLength(0)
  })

  it('padrão é 80 mm quando receipt.width não está configurado', async () => {
    apiMock.get.mockResolvedValue({ settings: {} })
    mountModal()
    await flushPromises()

    expect(wrapper.find('#tab-print').attributes('style')).toContain('width: 80mm')
    const styles = [...document.head.querySelectorAll('style')].filter((s) =>
      s.textContent.includes('@page')
    )
    expect(styles[0].textContent).toContain('size: 80mm')
  })
})
