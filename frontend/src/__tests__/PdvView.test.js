import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { nextTick } from 'vue'

const { apiMock, routerPush } = vi.hoisted(() => ({
  apiMock: {
    get: vi.fn(),
    post: vi.fn(),
  },
  routerPush: vi.fn(),
}))

vi.mock('@/api/client', () => ({ api: apiMock }))
vi.mock('element-plus', () => ({
  ElMessage: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: routerPush }),
}))

import PdvView from '@/views/PdvView.vue'

const products = [
  { id: 1, name: 'Doces arildo', price: 5, stock: 9, barcode: '040141018496' },
]
const methods = [{ id: 1, name: 'Dinheiro' }, { id: 2, name: 'PIX' }]

function mountView() {
  return mount(PdvView, {
    global: { stubs: { 'router-link': true } },
  })
}

describe('PdvView', () => {
  beforeEach(() => {
    apiMock.get.mockReset()
    apiMock.post.mockReset()
    routerPush.mockReset()
    apiMock.get.mockResolvedValue({ products, methods })
  })

  it('carrega produtos e formas de pagamento', async () => {
    const wrapper = mountView()
    await flushPromises()

    expect(apiMock.get).toHaveBeenCalledWith('/pdv')
    expect(wrapper.text()).toContain('Dinheiro')
    expect(wrapper.text()).toContain('Carrinho vazio')
  })

  it('adiciona item por busca + Enter e mostra total', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    expect(wrapper.find('#cart-count').text()).toBe('1 item')
    expect(wrapper.find('#cart-total').text()).toBe('R$ 5,00')
    expect(wrapper.text()).toContain('Doces arildo')
  })

  it('multiplicador N* define a quantidade', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('3*040141018496')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    expect(wrapper.find('#cart-count').text()).toBe('3 itens')
    expect(wrapper.find('#cart-total').text()).toBe('R$ 15,00')
  })

  it('finaliza a venda e navega para o recibo', async () => {
    apiMock.post.mockResolvedValue({ order: { order_id: 7 } })
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    await wrapper.find('.pdv-method').trigger('click')
    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    expect(apiMock.post).toHaveBeenCalledWith(
      '/pdv/complete',
      expect.objectContaining({
        method_id: 1,
        items: [{ product_id: 1, quantity: 1 }],
      })
    )
    expect(routerPush).toHaveBeenCalledWith('/pdv/recibo/7')
  })

  it('não finaliza sem forma de pagamento', async () => {
    const wrapper = mountView()
    await flushPromises()

    await wrapper.find('#pdv-search').setValue('arildo')
    await wrapper.find('#pdv-search').trigger('keydown', { key: 'Enter' })
    await nextTick()

    await wrapper.find('#pdv-finish').trigger('click')
    await flushPromises()

    expect(apiMock.post).not.toHaveBeenCalled()
  })
})
