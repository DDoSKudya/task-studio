const LANG_KEYWORDS: Record<string, string[]> = {
  python: [
    'False', 'None', 'True', 'and', 'as', 'assert', 'async', 'await', 'break', 'class', 'continue',
    'def', 'del', 'elif', 'else', 'except', 'finally', 'for', 'from', 'global', 'if', 'import',
    'in', 'is', 'lambda', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return', 'try', 'while',
    'with', 'yield',
  ],
  sql: [
    'select', 'from', 'where', 'join', 'inner', 'left', 'right', 'outer', 'on', 'group', 'by',
    'order', 'limit', 'insert', 'into', 'update', 'set', 'delete', 'create', 'table', 'and', 'or',
    'not', 'as', 'distinct', 'having', 'union', 'all', 'null', 'is', 'in', 'like', 'between',
    'case', 'when', 'then', 'else', 'end', 'count', 'sum', 'avg', 'min', 'max',
  ],
  javascript: [
    'await', 'break', 'case', 'catch', 'class', 'const', 'continue', 'debugger', 'default', 'delete',
    'do', 'else', 'export', 'extends', 'finally', 'for', 'function', 'if', 'import', 'in',
    'instanceof', 'let', 'new', 'return', 'super', 'switch', 'this', 'throw', 'try', 'typeof',
    'var', 'void', 'while', 'with', 'yield', 'async', 'of',
  ],
}

const HINT_ALIASES: Record<string, string> = {
  py: 'python',
  python: 'python',
  python3: 'python',
  py3: 'python',
  js: 'javascript',
  javascript: 'javascript',
  jsx: 'javascript',
  ts: 'javascript',
  typescript: 'javascript',
  tsx: 'javascript',
  sql: 'sql',
  postgresql: 'sql',
  postgres: 'sql',
  mysql: 'sql',
  sqlite: 'sql',
  plsql: 'sql',
  text: 'text',
  plain: 'text',
  plaintext: 'text',
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
}

function normalizeHint(hinted: string): string {
  const raw = hinted.trim().toLowerCase().replace(/^language-/, '')
  if (!raw) {
    return ''
  }
  return HINT_ALIASES[raw] || (raw in LANG_KEYWORDS ? raw : raw)
}

function looksLikePython(code: string): boolean {
  if (/^\s*(?:async\s+)?def\s+\w+/m.test(code)) {
    return true
  }
  if (/^\s*class\s+\w+/m.test(code)) {
    return true
  }
  if (/^\s*(?:from\s+\S+\s+import|import\s+\S+)/m.test(code)) {
    return true
  }
  if (/^\s*print\s*\(/m.test(code)) {
    return true
  }

  if (/^\s*with\s+.+\s+as\s+\w+\s*:/m.test(code)) {
    return true
  }
  if (/^\s*@(?:pytest|app|router|dataclass|staticmethod|classmethod|property|override)\b/m.test(code)) {
    return true
  }
  if (/\bself\.\w+/.test(code)) {
    return true
  }
  if (/\bf['"]/.test(code) || (/\br?['"].*\{/.test(code) && /\.format\s*\(/.test(code))) {
    return true
  }
  if (/\b(?:session|engine)\.(?:add|commit|flush|execute|query|scalars|get|rollback)\s*\(/i.test(code)) {
    return true
  }

  if (/^\s*\w+\s*=\s*[A-Z]\w*\s*\(/m.test(code) && /\.\w+\s*\(/.test(code)) {
    return true
  }
  if (/\bExcept(?:ion|Error)\b/.test(code) || /^\s*except\s+/m.test(code)) {
    return true
  }
  if (/^\s*#/.test(code) && /:\s*$/m.test(code) && /^\s{2,}\S/m.test(code)) {
    return true
  }
  return false
}

function looksLikeSql(code: string): boolean {
  if (/^\s*(?:SELECT|INSERT|UPDATE|DELETE|CREATE|ALTER|DROP|TRUNCATE|GRANT|REVOKE)\b/im.test(code)) {
    return true
  }

  if (/^\s*WITH\s+\w+\s+AS\s*\(/im.test(code)) {
    return true
  }
  return false
}

function looksLikeJavascript(code: string): boolean {
  if (/^\s*(?:const|let|var|function|export|import)\b/m.test(code)) {
    return true
  }
  if (/=>\s*\{/.test(code) || /\bconsole\.(?:log|error|warn)\s*\(/.test(code)) {
    return true
  }
  return false
}

export function detectCodeLanguage(code: string, hinted = ''): string {
  const hint = normalizeHint(hinted)
  const python = looksLikePython(code)
  const sql = looksLikeSql(code)
  const javascript = looksLikeJavascript(code)

  if (hint && hint in LANG_KEYWORDS) {

    if (hint === 'sql' && python && !sql) {
      return 'python'
    }
    if (hint === 'javascript' && python && !javascript) {
      return 'python'
    }
    if (hint !== 'text') {
      return hint
    }

  }

  if (python) {
    return 'python'
  }
  if (sql) {
    return 'sql'
  }
  if (javascript) {
    return 'javascript'
  }

  if (hint && hint !== 'text') {
    return hint
  }
  return 'text'
}

type Slot = { kind: 'str' | 'com'; text: string }

const SLOT_START = '\uE000'
const SLOT_END = '\uE001'
const SLOT_BASE = 0xE100

export function highlightStudyCode(code: string, language = ''): string {
  const lang = detectCodeLanguage(code, language)
  const keywords = LANG_KEYWORDS[lang]
  let html = escapeHtml(code)
  if (!keywords?.length) {
    return html
  }

  const slots: Slot[] = []
  const stash = (kind: Slot['kind'], text: string) => {
    const index = slots.length
    if (index > 0xff) {
      return text
    }
    slots.push({ kind, text })
    return `${SLOT_START}${String.fromCharCode(SLOT_BASE + index)}${SLOT_END}`
  }

  html = html.replace(/(^|\s)(#.*|\/\/.*)$/gm, (_full, prefix: string, comment: string) => {
    return `${prefix}${stash('com', comment)}`
  })
  html = html.replace(/(['"`])(?:\\.|(?!\1)[\s\S])*?\1/g, (match) => stash('str', match))

  const pattern = new RegExp(
    `\\b(?:${keywords.map((item) => item.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`,
    lang === 'sql' ? 'gi' : 'g',
  )
  html = html.replace(pattern, (match) => `<span class="tok-kw">${match}</span>`)
  html = html.replace(/\b(\d+(?:\.\d+)?)\b/g, '<span class="tok-num">$1</span>')

  const slotPattern = new RegExp(`${SLOT_START}([\\uE100-\\uE1FF])${SLOT_END}`, 'g')
  html = html.replace(slotPattern, (_full, marker: string) => {
    const index = marker.charCodeAt(0) - SLOT_BASE
    const slot = slots[index]
    if (!slot) {
      return ''
    }
    const cls = slot.kind === 'com' ? 'tok-com' : 'tok-str'
    return `<span class="${cls}">${slot.text}</span>`
  })

  return html
}
