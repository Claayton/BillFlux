import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  agentPrint,
  collectPageStyles,
  getAgentStatus,
  measureHeightMm,
  printElementWithAgent,
} from '@/utils/printBridge'

function jsonResponse(payload, ok = true) {
  return {
    ok,
    json: async () => payload,
  }
}

describe('printBridge', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    document.body.innerHTML = ''
    document.head.querySelectorAll('style[data-test]').forEach((node) => node.remove())
  })

  describe('getAgentStatus', () => {
    it('devolve o status quando o agente responde', async () => {
      const fetchMock = vi.fn().mockResolvedValue(
        jsonResponse({ ok: true, printer: 'EPSON', widthMm: 80 })
      )
      vi.stubGlobal('fetch', fetchMock)

      const status = await getAgentStatus()

      expect(status).toMatchObject({ printer: 'EPSON', widthMm: 80 })
      expect(fetchMock.mock.calls[0][0]).toMatch(/\/status$/)
    })

    it('devolve null quando o agente não está rodando', async () => {
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')))

      await expect(getAgentStatus()).resolves.toBeNull()
    })

    it('devolve null quando o agente responde erro', async () => {
      vi.stubGlobal('fetch', vi.fn().mockResolvedValue(jsonResponse({ ok: false }, false)))

      await expect(getAgentStatus()).resolves.toBeNull()
    })
  })

  describe('agentPrint', () => {
    it('envia o HTML, o papel e a impressora escolhida', async () => {
      const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
      vi.stubGlobal('fetch', fetchMock)

      const result = await agentPrint({
        bodyHtml: '<div>cupom</div>',
        css: '.cupom { color: red }',
        widthMm: 58,
        heightMm: 90,
        printer: 'EPSON TM-T20',
      })

      expect(result).toBe(true)
      const [url, options] = fetchMock.mock.calls[0]
      expect(url).toMatch(/\/print$/)
      expect(options.method).toBe('POST')
      const body = JSON.parse(options.body)
      expect(body.bodyHtml).toBe('<div>cupom</div>')
      expect(body.css).toBe('.cupom { color: red }')
      expect(body.widthMm).toBe(58)
      expect(body.heightMm).toBe(90)
      expect(body.printer).toBe('EPSON TM-T20')
    })

    it('devolve false quando o agente falha (fallback para window.print)', async () => {
      vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('sem agente')))

      await expect(agentPrint({ bodyHtml: '<div>x</div>' })).resolves.toBe(false)
    })

    it('devolve false quando o agente responde erro', async () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockResolvedValue(jsonResponse({ ok: false, error: 'sem papel' }, false))
      )

      await expect(agentPrint({ bodyHtml: '<div>x</div>' })).resolves.toBe(false)
    })

    it('nem tenta imprimir sem HTML', async () => {
      const fetchMock = vi.fn()
      vi.stubGlobal('fetch', fetchMock)

      await expect(agentPrint({})).resolves.toBe(false)
      expect(fetchMock).not.toHaveBeenCalled()
    })
  })

  describe('collectPageStyles', () => {
    it('junta as regras CSS da página', () => {
      const style = document.createElement('style')
      style.dataset.test = 'true'
      style.textContent = '.cupom-thermal { font-family: Arial; }'
      document.head.appendChild(style)

      const { css } = collectPageStyles(document)

      expect(css).toContain('.cupom-thermal')
      expect(css).toContain('font-family: Arial')
    })
  })

  describe('measureHeightMm', () => {
    it('converte a altura em mm com folga de 3 mm', () => {
      const element = { getBoundingClientRect: () => ({ height: 302.4 }) }

      // 302,4 px ≈ 80 mm; +3 mm de folga
      expect(measureHeightMm(element, 80)).toBe(84)
    })

    it('nunca devolve altura menor que a largura (evita paisagem)', () => {
      const element = { getBoundingClientRect: () => ({ height: 10 }) }

      expect(measureHeightMm(element, 80)).toBe(80)
    })
  })

  describe('printElementWithAgent', () => {
    it('clona o elemento com o CSS da aplicação e mede o papel', async () => {
      const style = document.createElement('style')
      style.dataset.test = 'true'
      style.textContent = '.receipt { padding: 4px; }'
      document.head.appendChild(style)

      const element = document.createElement('div')
      element.id = 'sale-receipt-print'
      element.innerHTML = '<strong>Cupom</strong>'
      document.body.appendChild(element)

      const fetchMock = vi.fn().mockResolvedValue(jsonResponse({ ok: true }))
      vi.stubGlobal('fetch', fetchMock)

      const result = await printElementWithAgent(element, { widthMm: 80 })

      expect(result).toBe(true)
      const body = JSON.parse(fetchMock.mock.calls[0][1].body)
      expect(body.bodyHtml).toContain('receipt-print-clone')
      expect(body.bodyHtml).toContain('sale-receipt-print')
      expect(body.bodyHtml).toContain('Cupom')
      expect(body.css).toContain('.receipt')
      expect(body.widthMm).toBe(80)
      expect(body.heightMm).toBeGreaterThanOrEqual(80)
    })

    it('devolve false sem elemento', async () => {
      await expect(printElementWithAgent(null)).resolves.toBe(false)
    })
  })
})
