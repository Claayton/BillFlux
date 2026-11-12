import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'

const { apiMock } = vi.hoisted(() => ({
  apiMock: { getBlob: vi.fn() },
}))

vi.mock('@/api/client', () => ({ api: apiMock }))
vi.mock('pdfjs-dist', () => ({ GlobalWorkerOptions: {}, getDocument: vi.fn() }))
vi.mock('pdfjs-dist/build/pdf.worker.min.mjs?url', () => ({ default: 'worker.js' }))
// Sem agente rodando durante os testes: cai sempre no window.print.
vi.mock('@/utils/printBridge', () => ({ agentPrint: vi.fn(async () => false) }))

import { printDanfe } from '@/utils/danfe'

const DATA_URL = 'data: image / png;base64,AAAA'
const HTML_DANFE = `<html><head><style>td { border: 1px solid #000; }</style></head>
<body><div class="container" style="max-width:300px;padding:5px">
<script>alert('xss')</script>
<table><tbody><tr><td>NFC-e</td></tr></tbody></table>
<img src="${DATA_URL}" alt="" style="max-width:150px;">
<a href="javascript:alert(1)">chave</a>
</div></body></html>`

let printSpy
let captured

describe('printDanfe', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    captured = null
    printSpy = vi.fn(() => {
      const root = document.getElementById('danfe-print-root')
      const shadow = root?.shadowRoot
      captured = {
        css: shadow?.querySelector('style')?.textContent || '',
        img: shadow?.querySelector('img') || null,
      }
    })
    window.print = printSpy
  })

  afterEach(() => {
    delete window.print
    document
      .querySelectorAll(
        '#danfe-print-root, #danfe-print-style, #danfe-print-base-style'
      )
      .forEach((node) => node.remove())
  })

  it('imprime o DANFE em HTML devolvido pelo provedor', async () => {
    apiMock.getBlob.mockResolvedValue(new Blob([HTML_DANFE], { type: 'text/html' }))

    await printDanfe(9, { widthMm: 80 })

    expect(apiMock.getBlob).toHaveBeenCalledWith('/fiscal/9/danfe')
    expect(printSpy).toHaveBeenCalledTimes(1)
    // o tamanho do QR Code do provedor (style inline) precisa prevalecer
    expect(captured.img?.getAttribute('style')).toContain('max-width:150px')
    expect(captured.css).not.toMatch(/img\s*\{[^}]*max-width:\s*100%\s*!important/)
    // limpa tudo depois de imprimir
    expect(document.getElementById('danfe-print-root')).toBeNull()
    expect(document.getElementById('danfe-print-style')).toBeNull()
    expect(document.getElementById('danfe-print-base-style')).toBeNull()
  })

  it('avisa quando o arquivo não é PDF nem HTML', async () => {
    apiMock.getBlob.mockResolvedValue(new Blob(['PK\u0003\u0004'], { type: 'application/octet-stream' }))

    await expect(printDanfe(9)).rejects.toThrow(/formato imprimível/)
    expect(printSpy).not.toHaveBeenCalled()
  })

  it('avisa quando o DANFE ainda não existe', async () => {
    apiMock.getBlob.mockResolvedValue(new Blob([], { type: 'application/pdf' }))

    await expect(printDanfe(9)).rejects.toThrow(/ainda não está disponível/)
    expect(printSpy).not.toHaveBeenCalled()
  })
})
