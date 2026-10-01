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

import { ElMessage } from 'element-plus'
import ConfigView from '@/views/ConfigView.vue'

const settingsPayload = {
  settings: {
    'company.name': 'Loja X',
    'company.cnpj': '11.222.333/0001-81',
    'company.address': 'Rua A, 100',
    'company.phone': '(11) 98888-7777',
    'receipt.width': '80',
    'receipt.header': 'Loja X\nCNPJ 11.222.333/0001-81',
    'receipt.footer': 'Obrigado!',
    'pdv.auto_print': 'false',
    'stock.default_min': '5',
  },
}

function mountView() {
  return mount(ConfigView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('ConfigView', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    apiMock.get.mockResolvedValue(settingsPayload)
  })

  it('carrega e mostra as abas, com Fiscal desabilitada', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/settings')

    const labels = wrapper.findAll('.config-tabs button').map((b) => b.text())
    expect(labels).toEqual(['Empresa', 'PDV', 'Estoque', 'Impressão', 'Fiscal em breve'])

    const fiscal = wrapper.findAll('.config-tabs button')[4]
    expect(fiscal.attributes('disabled')).toBeDefined()
  })

  it('aba Empresa exibe os campos preenchidos', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(wrapper.find('#cfg-name').element.value).toBe('Loja X')
    expect(wrapper.find('#cfg-cnpj').element.value).toBe('11.222.333/0001-81')
    expect(wrapper.find('#cfg-address').element.value).toBe('Rua A, 100')
    expect(wrapper.find('#cfg-phone').element.value).toBe('(11) 98888-7777')
  })

  it('alterna para a aba Impressão e edita a largura do papel', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.config-tabs button')[3].trigger('click')

    const widthButtons = wrapper
      .findAll('.config-section .filter-segmented button')
      .filter((b) => b.text().includes('mm'))
    expect(widthButtons).toHaveLength(2)
    expect(widthButtons[1].classes()).toContain('is-active')

    await widthButtons[0].trigger('click')
    expect(wrapper.vm.form['receipt.width']).toBe('58')
  })

  it('salva todas as chaves via PUT e avisa', async () => {
    apiMock.put.mockResolvedValue(settingsPayload)
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#cfg-name').setValue('Loja Y')
    await wrapper.find('form.config-panel').trigger('submit')
    await flushPromises()

    expect(apiMock.put).toHaveBeenCalledWith('/settings', {
      settings: expect.objectContaining({
        'company.name': 'Loja Y',
        'receipt.width': '80',
        'stock.default_min': '5',
      }),
    })
    expect(ElMessage.success).toHaveBeenCalledWith('Configurações salvas!')
  })

  it('checkbox de auto-print grava true/false como string', async () => {
    apiMock.put.mockResolvedValue(settingsPayload)
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.config-tabs button')[1].trigger('click')
    const check = wrapper.find('.config-check input')
    expect(check.element.checked).toBe(false)

    await check.setValue(true)
    expect(wrapper.vm.form['pdv.auto_print']).toBe('true')

    await wrapper.find('form.config-panel').trigger('submit')
    await flushPromises()

    expect(apiMock.put).toHaveBeenCalledWith('/settings', {
      settings: expect.objectContaining({ 'pdv.auto_print': 'true' }),
    })
  })

  it('erro de rede vira toast de erro', async () => {
    apiMock.put.mockRejectedValue(new Error('Erro 500'))
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('form.config-panel').trigger('submit')
    await flushPromises()

    expect(ElMessage.error).toHaveBeenCalledWith('Erro 500')
    expect(ElMessage.success).not.toHaveBeenCalled()
  })

  it('prévia do cupom atualiza ao vivo com cabeçalho, rodapé e largura', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.findAll('.config-tabs button')[3].trigger('click')
    await flushPromises()

    let coupon = wrapper.find('.coupon-preview .receipt-thermal')
    expect(coupon.exists()).toBe(true)
    expect(coupon.attributes('style')).toContain('width: 80mm')
    expect(coupon.text()).toContain('Loja X')
    expect(coupon.text()).toContain('CNPJ 11.222.333/0001-81')

    await wrapper.find('#cfg-header').setValue('Loja Z\nRua Z, 1')
    await flushPromises()
    expect(coupon.text()).toContain('Loja Z')
    expect(coupon.text()).toContain('Rua Z, 1')
    expect(coupon.text()).not.toContain('CNPJ 11.222.333/0001-81')

    await wrapper.find('#cfg-footer').setValue('Até logo!')
    await flushPromises()
    expect(coupon.text()).toContain('Até logo!')

    const widthButtons = wrapper
      .findAll('.print-fields .filter-segmented button')
      .filter((b) => b.text().includes('mm'))
    await widthButtons[0].trigger('click')
    await flushPromises()
    expect(coupon.attributes('style')).toContain('width: 58mm')
  })
})
