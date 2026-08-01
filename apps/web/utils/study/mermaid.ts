
const MERMAID_HINT = /^(?:mermaid|mmd)$/i

const MERMAID_START =
  /^(?:graph|flowchart|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|erDiagram|journey|gantt|pie|mindmap|timeline|quadrantChart|gitGraph|C4Context|C4Container|C4Component|C4Dynamic|C4Deployment|block(?:-beta)?|architecture(?:-beta)?|sankey(?:-beta)?|xychart(?:-beta)?|packet(?:-beta)?|kanban|requirementDiagram|zenuml|radar(?:-beta)?)\b/i

const MERMAID_EDGE = /(?:-->|---|-\.->|==>|--|-\.-)/

const LABEL_NEEDS_QUOTES = /[(){}<>#;:%\\]|[\u0400-\u04FF]/

export function isMermaidBlock(code: string, hinted = ''): boolean {
  const hint = hinted.trim().replace(/^language-/i, '')
  if (MERMAID_HINT.test(hint)) {
    return true
  }

  if (hint && !/^(?:text|plain|txt|md|markdown)?$/i.test(hint) && !MERMAID_HINT.test(hint)) {
    if (!/^(?:diagram|graph|flow)$/i.test(hint)) {

      const stripped = stripMermaidNoise(code)
      if (!MERMAID_START.test(stripped)) {
        return false
      }
    }
  }
  return looksLikeMermaidSource(code)
}

export function looksLikeMermaidSource(code: string): boolean {
  const stripped = stripMermaidNoise(code)
  if (!stripped) {
    return false
  }
  if (MERMAID_START.test(stripped)) {
    return true
  }

  const lines = stripped.split('\n').map((line) => line.trim()).filter(Boolean)
  if (lines.length < 2) {
    return false
  }
  const edgeLines = lines.filter((line) => {
    if (!MERMAID_EDGE.test(line)) {
      return false
    }
    return /[A-Za-z][\w.-]*\s*(?:\[|\(|-->|---|==>)/.test(line)
  })
  if (edgeLines.length >= 2 && edgeLines.length >= Math.ceil(lines.length * 0.6)) {
    return true
  }
  return false
}

function stripMermaidNoise(code: string): string {
  return code
    .replace(/\r\n/g, '\n')
    .replace(/^\s*```(?:mermaid|mmd)?\s*\n?/i, '')
    .replace(/\n?```\s*$/i, '')
    .replace(/^\s*%%\{[\s\S]*?\}%%\s*/m, '')
    .replace(/^\s*%%[^\n]*\n/gm, '')
    .replace(/^\s+/, '')
    .trim()
}

export function repairMermaidSource(raw: string): string {
  let text = raw.replace(/\r\n/g, '\n').trim()
  if (!text) {
    return text
  }

  text = text.replace(/^\s*```(?:mermaid|mmd)?\s*\n?/i, '').replace(/\n?```\s*$/i, '')

  text = text.replace(/^\s*graphs?\s+(TD|TB|BT|RL|LR)\b/im, 'graph $1')
  text = text.replace(/^\s*flow[\s-]?chart\s+(TD|TB|BT|RL|LR)\b/im, 'flowchart $1')
  text = text.replace(/^\s*flow[\s-]?chart\b/im, 'flowchart')
  text = text.replace(/^\s*sequence\s+diagram\b/im, 'sequenceDiagram')
  text = text.replace(/^\s*class\s+diagram\b/im, 'classDiagram')
  text = text.replace(/^\s*state\s+diagram(?:-v2)?\b/im, 'stateDiagram-v2')
  text = text.replace(/^\s*er\s+diagram\b/im, 'erDiagram')
  text = text.replace(/^\s*git\s+graph\b/im, 'gitGraph')
  text = text.replace(/^\s*requirement\s+diagram\b/im, 'requirementDiagram')

  const strippedHead = text.replace(/^\s*%%\{[\s\S]*?\}%%\s*/m, '').replace(/^\s*%%[^\n]*\n/gm, '').trimStart()
  if (strippedHead && !MERMAID_START.test(strippedHead) && looksLikeMermaidSource(text)) {
    text = `flowchart TD\n${text}`
  }

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
