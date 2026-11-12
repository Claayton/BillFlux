import * as pdfjsLib from 'pdfjs-dist'
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url'
import { api } from '@/api/client'

// pdf.js 4 usa Promise.withResolvers (Chrome 119+). Garante compatibilidade
// com navegadores de caixa mais antigos.
if (typeof Promise.withResolvers !== 'function') {
  Promise.withResolvers = function withResolvers() {
    let resolve
    let reject
    const promise = new Promise((res, rej) => {
      resolve = res
      reject = rej
    })
    return { promise, resolve, reject }
  }
}

pdfjsLib.GlobalWorkerOptions.workerSrc = workerUrl

/** Resolução usada ao rasterizar o PDF (impressoras térmicas ficam entre 203 e 300 dpi). */
const RENDER_DPI = 203
const MM_PER_INCH = 25.4
const PRINT_ROOT_ID = 'danfe-print-root'
const PRINT_STYLE_ID = 'danfe-print-style'

/**
 * Renderiza o DANFE (PDF) em imagens e abre a caixa de impressão no clique.
 *
 * Rasterizamos com `pdf.js` para controlar a largura do papel: o DANFE da
 * NFC-e já vem em formato cupom, então ele sai na largura configurada
 * (padrão 80 mm) sem depender do visualizador de PDF do navegador.
 *
 * @param {number|string} documentId id do documento fiscal
 * @param {{ widthMm?: number }} options largura do papel em milímetros
 */
export async function printDanfe(documentId, { widthMm = 80 } = {}) {
  const blob = await api.getBlob(`/fiscal/${documentId}/danfe`)
  if (!blob.size) {
    throw new Error('O DANFE desta nota ainda não está disponível.')
  }

  const header = await blob.slice(0, 4).text()
  if (!header.toLowerCase().startsWith('%pdf')) {
    throw new Error(
      'O DANFE desta nota não veio em PDF. Baixe o arquivo em Vendas → Nota fiscal.'
    )
  }

  const pdf = await pdfjsLib.getDocument({ data: await blob.arrayBuffer() }).promise
  const images = []
  let heightMm = widthMm
  try {
    const widthPx = (widthMm / MM_PER_INCH) * RENDER_DPI
    for (let number = 1; number <= pdf.numPages; number++) {
      const page = await pdf.getPage(number)
      const base = page.getViewport({ scale: 1 })
      const viewport = page.getViewport({ scale: widthPx / base.width })
      const canvas = document.createElement('canvas')
      canvas.width = Math.ceil(viewport.width)
      canvas.height = Math.ceil(viewport.height)
      await page.render({ canvasContext: canvas.getContext('2d'), viewport }).promise
      images.push(canvas.toDataURL('image/png'))
      if (number === 1) {
        heightMm = Math.ceil((viewport.height / viewport.width) * widthMm)
      }
    }
  } finally {
    pdf.destroy()
  }

  await printImages(images, widthMm, heightMm)
}

function buildPrintStyle(widthMm, heightMm) {
  return `
    @page { size: ${widthMm}mm ${heightMm}mm; margin: 0; }
    #${PRINT_ROOT_ID} { display: none; }
    @media print {
      body > *:not(#${PRINT_ROOT_ID}) { display: none !important; }
      html, body { margin: 0; padding: 0; background: #fff; }
      #${PRINT_ROOT_ID} {
        display: block !important;
        visibility: visible !important;
        margin: 0;
        padding: 0;
      }
      #${PRINT_ROOT_ID} img {
        display: block;
        visibility: visible !important;
        width: ${widthMm}mm;
        height: auto;
        page-break-after: always;
        break-after: page;
      }
      #${PRINT_ROOT_ID} img:last-child {
        page-break-after: auto;
        break-after: auto;
      }
    }
  `
}

async function printImages(images, widthMm, heightMm) {
  const root = document.createElement('div')
  root.id = PRINT_ROOT_ID
  root.setAttribute('aria-hidden', 'true')

  const nodes = images.map((src) => {
    const img = document.createElement('img')
    img.src = src
    img.alt = ''
    root.appendChild(img)
    return img
  })
  document.body.appendChild(root)

  const style = document.createElement('style')
  style.id = PRINT_STYLE_ID
  style.textContent = buildPrintStyle(widthMm, heightMm)
  document.head.appendChild(style)

  const cleanup = () => {
    root.remove()
    style.remove()
  }

  try {
    // Garante que as imagens foram decodificadas antes de abrir a impressão.
    await Promise.all(
      nodes.map((img) =>
        typeof img.decode === 'function'
          ? img.decode().catch(() => undefined)
          : Promise.resolve()
      )
    )
    await new Promise((resolve) => window.setTimeout(resolve, 50))
    if (typeof window.print !== 'function') {
      throw new Error('Este navegador não permite imprimir.')
    }
    window.print()
  } finally {
    cleanup()
  }
}
