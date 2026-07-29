

const MERMAID_HINT = /^(?:mermaid|mmd)$/i

const MERMAID_BODY =
  /^\s*(?:graph|flowchart|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|erDiagram|journey|gantt|pie|mindmap|timeline|quadrantChart|gitGraph|C4Context|C4Container|C4Component|C4Dynamic|C4Deployment)\b/m


const LABEL_NEEDS_QUOTES = /[(){}<>#;:%\\]|[\u0400-\u04FF]/

export function isMermaidBlock(code: string, hinted = ''): boolean {
  if (MERMAID_HINT.test(hinted.trim().replace(/^language-/i, ''))) {
    return true
  }
  return MERMAID_BODY.test(code)
}


export function repairMermaidSource(raw: string): string {
  let text = raw.replace(/\r\n/g, '\n').trim()
  if (!text) {
    return text
  }


  text = text.replace(/^\s*```(?:mermaid|mmd)?\s*\n?/i, '').replace(/\n?```\s*$/i, '')


  text = text.replace(/^\s*graphs?\s+(TD|TB|BT|RL|LR)\b/im, 'graph $1')
  text = text.replace(/^\s*flow[\s-]?chart\s+(TD|TB|BT|RL|LR)\b/im, 'flowchart $1')

  text = quoteShapeLabels(text, '[', ']')


  text = text.replace(/\|([^|\n]+)\|/g, (_full, label: string) => {
    const trimmed = label.trim()
    if (!trimmed || (trimmed.startsWith('"') && trimmed.endsWith('"'))) {
      return `|${trimmed}|`
    }
    if (LABEL_NEEDS_QUOTES.test(trimmed) || /\s/.test(trimmed)) {
      return `|"${escapeMermaidLabel(trimmed)}"|`
    }
    return `|${trimmed}|`
  })

  return text.trim()
}

function escapeMermaidLabel(label: string): string {
  return label.replace(/\\/g, '\\\\').replace(/"/g, '#quot;')
}

function quoteShapeLabels(source: string, open: string, close: string): string {
  const openEsc = open.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const closeEsc = close.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')

  const re = new RegExp(
    `(\\b[A-Za-z][\\w.-]*)\\s*${openEsc}(?!")([^${closeEsc}\\n]*)${closeEsc}`,
    'g',
  )
  return source.replace(re, (_full, id: string, label: string) => {
    const trimmed = label.trim()
    if (!trimmed) {
      return `${id}${open}${close}`
    }
    if (!LABEL_NEEDS_QUOTES.test(trimmed)) {
      return `${id}${open}${trimmed}${close}`
    }
    return `${id}${open}"${escapeMermaidLabel(trimmed)}"${close}`
  })
}
