/**
 * Ponte com o "BillFlux — Agente de impressão" instalado no caixa.
 *
 * O agente é um app pequeno (Windows) que fica na bandeja e escuta só em
 * 127.0.0.1. Quando ele está rodando, o BillFlux manda o HTML do cupom/DANFE
 * e a impressão sai direto na impressora escolhida, sem diálogo e sem o
 * cabeçalho/rodapé do navegador. Se ele não estiver rodando, tudo cai no
 * `window.print()` de sempre — ninguém fica sem imprimir.
 */

const DEFAULT_AGENT_URL = 'http://127.0.0.1:9911'
const STATUS_TIMEOUT_MS = 1200
// Generoso de propósito: se o agente já começou a imprimir e o navegador
// desiste, o fallback abriria o diálogo e sairiam duas vias.
const PRINT_TIMEOUT_MS = 60000

function agentBaseUrl() {
  let configured = ''
  try {
    configured = import.meta.env?.VITE_PRINT_AGENT_URL || ''
  } catch {
    configured = ''
  }
  return (configured || DEFAULT_AGENT_URL).replace(/\/+$/, '')
}

/** fetch com AbortController: o agente é local, não pode travar a tela. */
async function request(path, options = {}, timeoutMs = PRINT_TIMEOUT_MS) {
  const controller = typeof AbortController === 'function' ? new AbortController() : null
  const timer = controller ? setTimeout(() => controller.abort(), timeoutMs) : null
  try {
    return await fetch(`${agentBaseUrl()}${path}`, {
      ...options,
      signal: controller ? controller.signal : undefined,
    })
  } finally {
    if (timer) clearTimeout(timer)
  }
}

/**
 * Estado do agente ou `null` quando ele não está rodando.
 * Usado para avisar o operador/Configurações; nunca lança.
 */
export async function getAgentStatus() {
  try {
    const response = await request('/status', {}, STATUS_TIMEOUT_MS)
    if (!response.ok) return null
    const data = await response.json()
    return data?.ok ? data : null
  } catch {
    return null
  }
}

/**
 * Envia um documento para o agente imprimir.
 * @returns {Promise<boolean>} true só quando o agente confirmou a impressão.
 */
export async function agentPrint({
  bodyHtml,
  css = '',
  links = [],
  widthMm = 80,
  heightMm = widthMm,
  printer = '',
} = {}) {
  if (!bodyHtml) return false
  try {
    const response = await request('/print', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ bodyHtml, css, links, widthMm, heightMm, printer }),
    })
    if (!response.ok) return false
    const data = await response.json().catch(() => null)
    return Boolean(data?.ok)
  } catch {
    return false
  }
}

/**
 * Reúne o CSS da página para levar junto com o HTML (o agente abre um
 * documento novo, sem o app em volta). `cssRules` só funciona em folhas
 * de mesma origem; as demais viram <link>.
 */
export function collectPageStyles(doc) {
  const target = doc || (typeof document !== 'undefined' ? document : null)
  if (!target) return { css: '', links: [] }

  const chunks = []
  const links = []
  const seen = new Set()

  let sheets = []
  try {
    sheets = Array.from(target.styleSheets || [])
  } catch {
    sheets = []
  }

  for (const sheet of sheets) {
    if (!sheet) continue
    try {
      const rules = sheet.cssRules
      if (!rules) continue
      const text = Array.from(rules)
        .map((rule) => rule.cssText)
        .join('\n')
      if (text) chunks.push(text)
    } catch {
      // Folha de outra origem: manda o endereço e deixa o WebView2 buscar.
      if (sheet.href && !seen.has(sheet.href)) {
        seen.add(sheet.href)
        links.push(sheet.href)
      }
    }
  }

  return { css: chunks.join('\n'), links }
}

/** Altura real do elemento em mm, com uma folga de 3 mm (mesma regra do @page). */
export function measureHeightMm(element, widthMm = 80) {
  const heightPx = element?.getBoundingClientRect?.().height || 0
  let heightMm = heightPx > 0 ? Math.ceil((heightPx * 25.4) / 96) + 3 : widthMm
  if (heightMm < widthMm) heightMm = widthMm
  return heightMm
}

/**
 * Imprime um elemento da tela (cupom/comanda) pelo agente.
 * Clona o nó e leva o CSS da aplicação, então o papel sai igual ao preview.
 */
export async function printElementWithAgent(element, { widthMm = 80, heightMm } = {}) {
  if (!element) return false

  const clone = element.cloneNode(true)
  clone.classList.add('receipt-print-clone')
  const { css, links } = collectPageStyles(element.ownerDocument)

  return agentPrint({
    bodyHtml: clone.outerHTML,
    css,
    links,
    widthMm,
    heightMm: heightMm || measureHeightMm(element, widthMm),
  })
}
