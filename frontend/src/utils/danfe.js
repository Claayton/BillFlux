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
const PRINT_BASE_STYLE_ID = 'danfe-print-base-style'

/**
 * Renderiza o DANFE e abre a caixa de impressão no clique.
 *
 * O provedor pode devolver o DANFE em PDF (rasterizamos com pdf.js) ou em HTML
 * (cupom pronto). Nos dois casos a impressão respeita a largura configurada,
 * padrão 80 mm, sem depender do visualizador do navegador.
 *
 * @param {number|string} documentId id do documento fiscal
 * @param {{ widthMm?: number }} options largura do papel em milímetros
 */
export async function printDanfe(documentId, { widthMm = 80 } = {}) {
  const blob = await api.getBlob(`/fiscal/${documentId}/danfe`)
  if (!blob.size) {
    throw new Error('O DANFE desta nota ainda não está disponível.')
  }

  const buffer = await blob.arrayBuffer()
  const head = new TextDecoder('utf-8').decode(buffer.slice(0, 8)).trimStart().toLowerCase()

  if (head.startsWith('%pdf')) {
    await printPdf(buffer, widthMm)
    return
  }
  if (head.startsWith('<')) {
    await printHtml(new TextDecoder('utf-8').decode(buffer), widthMm)
    return
  }

  throw new Error(
    'O DANFE desta nota não veio em um formato imprimível. Baixe o arquivo em Vendas → Nota fiscal.'
  )
}

async function printPdf(buffer, widthMm) {
  const pdf = await pdfjsLib.getDocument({ data: buffer }).promise
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

function buildPdfPrintStyle(widthMm, heightMm) {
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
  style.textContent = buildPdfPrintStyle(widthMm, heightMm)
  document.head.appendChild(style)

  try {
    await waitForImages(nodes)
    await delay(50)
    callPrint()
  } finally {
    root.remove()
    style.remove()
  }
}

/**
 * Extrai o conteúdo imprimível do HTML do provedor, removendo scripts e
 * mantendo apenas o CSS do próprio documento (necessário pro cupom).
 */
function extractHtmlDanfe(html) {
  const parsed = new DOMParser().parseFromString(html, 'text/html')
  parsed
    .querySelectorAll('script, iframe, object, embed, link, meta, base, form')
    .forEach((node) => node.remove())

  const css = [...parsed.querySelectorAll('style')]
    .map((node) => node.textContent || '')
    .join('\n')
  parsed.querySelectorAll('style').forEach((node) => node.remove())

  parsed.querySelectorAll('*').forEach((element) => {
    for (const attr of [...element.attributes]) {
      const name = attr.name.toLowerCase()
      if (name.startsWith('on')) {
        element.removeAttribute(attr.name)
      } else if (
        (name === 'href' || name === 'src') &&
        /^\s*javascript:/i.test(attr.value)
      ) {
        element.removeAttribute(attr.name)
      }
    }
  })

  // O provedor às vezes escreve "data: image / png;base64,..." com espaços:
  // normaliza o MIME pra o QR Code não sumir na impressão.
  parsed.querySelectorAll('img[src^="data:"]').forEach((img) => {
    const src = img.getAttribute('src') || ''
    img.setAttribute(
      'src',
      src.replace(/^data:\s*([^,]*?)\s*,/i, (_, meta) => `data:${meta.replace(/\s+/g, '')},`)
    )
  })

  return { css, body: parsed.body.innerHTML }
}

function buildHtmlBaseStyle(widthMm) {
  return `
    #${PRINT_ROOT_ID} {
      position: absolute;
      left: -10000px;
      top: 0;
      width: ${widthMm}mm;
      background: #fff;
    }
  `
}

/** Regras do cupom dentro do shadow DOM (isoladas do resto do app). */
const SHADOW_BASE_CSS = `
  :host {
    display: block;
    width: 100%;
    background: #fff;
    color: #000;
    font-family: Arial, Helvetica, sans-serif;
    font-size: 9px;
  }
  .container {
    max-width: 100% !important;
    width: 100% !important;
    padding: 0 !important;
    box-sizing: border-box;
  }
  /* Sem !important: o provedor limita o QR Code no style inline
     (ex.: max-width:150px) e essa medida precisa prevalecer. */
  img { max-width: 100%; height: auto; }
  table { width: 100% !important; border-collapse: collapse; }
`

function buildHtmlPrintStyle(widthMm, heightMm) {
  return `
    @page { size: ${widthMm}mm ${heightMm}mm; margin: 0; }
    @media print {
      body > *:not(#${PRINT_ROOT_ID}) { display: none !important; }
      html, body {
        margin: 0;
        padding: 0;
        background: #fff;
        visibility: visible !important;
      }
      #${PRINT_ROOT_ID} {
        position: static !important;
        display: block !important;
        visibility: visible !important;
        width: ${widthMm}mm !important;
      }
      #${PRINT_ROOT_ID} * {
        visibility: visible !important;
      }
    }
  `
}

async function printHtml(html, widthMm) {
  const { css, body } = extractHtmlDanfe(html)

  const root = document.createElement('div')
  root.id = PRINT_ROOT_ID
  root.setAttribute('aria-hidden', 'true')
  // Shadow DOM: o CSS do provedor fica isolado e não vaza pro app.
  const shadow = root.attachShadow({ mode: 'open' })
  shadow.innerHTML = `<style>${css}\n${SHADOW_BASE_CSS}</style>${body}`
  document.body.appendChild(root)

  // Posiciona o cupom fora da tela pra medirmos a altura real do papel.
  const baseStyle = document.createElement('style')
  baseStyle.id = PRINT_BASE_STYLE_ID
  baseStyle.textContent = buildHtmlBaseStyle(widthMm)
  document.head.appendChild(baseStyle)

  let printStyle = null
  try {
    const heightPx = root.getBoundingClientRect().height
    let heightMm = heightPx > 0 ? Math.ceil((heightPx * 25.4) / 96) + 4 : widthMm
    if (heightMm < widthMm) heightMm = widthMm

    printStyle = document.createElement('style')
    printStyle.id = PRINT_STYLE_ID
    printStyle.textContent = buildHtmlPrintStyle(widthMm, heightMm)
    document.head.appendChild(printStyle)

    await waitForImages([...shadow.querySelectorAll('img')])
    await delay(50)
    callPrint()
  } finally {
    root.remove()
    baseStyle.remove()
    printStyle?.remove()
  }
}

function waitForImages(nodes) {
  return Promise.all(
    nodes.map(
      (img) =>
        new Promise((resolve) => {
          if (img.complete) {
            resolve()
            return
          }
          // `img.decode()` pode ficar pendente no Chromium quando a imagem
          // está num shadow DOM fora da tela; load/error + timeout é seguro.
          const done = () => resolve()
          img.addEventListener('load', done, { once: true })
          img.addEventListener('error', done, { once: true })
          window.setTimeout(done, 2000)
        })
    )
  )
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms))
}

function callPrint() {
  if (typeof window.print !== 'function') {
    throw new Error('Este navegador não permite imprimir.')
  }
  window.print()
}
