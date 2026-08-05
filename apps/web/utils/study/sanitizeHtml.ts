import { decodeLiteralEntities, repairMojibake } from './sanitizeEncoding'
import { isMermaidBlock, repairMermaidSource } from './mermaid'
import { purifyStudyHtml } from './purifyStudyHtml'

const SCRIPTISH =
  /<\/?(?:script|style|iframe|object|embed|form|input|button|link|meta)[^>]*>/gi
const ON_ATTR = /\s+on[a-z]+\s*=\s*(?:'[^']*'|"[^"]*"|[^\s>]+)/gi
const JS_HREF = /\s+(?:href|src)\s*=\s*(['"])\s*javascript:[^'"]*\1/gi

export { repairMojibake } from './sanitizeEncoding'
export { purifyStudyHtml } from './purifyStudyHtml'

export function sanitizeStudyHtml(dirty: string): string {
  if (!dirty) {
    return ''
  }
  let html = repairMojibake(dirty)

  const preBlocks: string[] = []
  html = html.replace(/<pre\b[\s\S]*?<\/pre>/gi, (block) => {
    const index = preBlocks.length
    preBlocks.push(block)
    return `\uE010PRE${index}\uE011`
  })

  html = decodeLiteralEntities(html)
  html = html.replace(SCRIPTISH, '').replace(ON_ATTR, '').replace(JS_HREF, '')

  html = html.replace(/\uE010PRE(\d+)\uE011/g, (_m, index: string) => {
    return normalizePreCodeBlock(preBlocks[Number(index)] ?? '')
  })

  html = html.replace(
    /<table(\b[^>]*)>\s*(?:<tbody[^>]*>)?\s*<tr>([\s\S]*?)<\/tr>/gi,
    (match, attrs: string, rowInner: string) => {
      if (/<th\b/i.test(rowInner)) {
        return match
      }
      const headed = rowInner.replace(/<\/?td\b/gi, (tag) => tag.replace(/td/i, 'th'))
      return `<table${attrs}><thead><tr>${headed}</tr></thead><tbody>`
    },
  )

  html = html.replace(
    /<p(?:\s[^>]*)?>\s*<(strong|b)(?:\s[^>]*)?>([\s\S]*?)<\/\1>\s*<\/p>/gi,
    (match, _tag: string, inner: string) => {
      const text = inner.replace(/<[^>]+>/g, '').replace(/\s+/g, ' ').trim()
      if (!text || text.length > 120 || /[.!?…]$/.test(text)) {
        return match
      }
      return `<h3 class="study-section-title">${inner.trim()}</h3>`
    },
  )

  html = html.replace(/<p>(?:\s|&nbsp;|<br\s*\/?>)*<\/p>/gi, '')

  html = hydrateAsciiTablesInHtml(html)

  html = stripTablePresentation(html)

  html = html.replace(/<table\b[\s\S]*?<\/table>/gi, (table) => {
    if (table.includes('table-wrap')) {
      return table
    }
    return `<div class="table-wrap">${table}</div>`
  })
  return purifyStudyHtml(html)
}

export function normalizePreCodeBlock(block: string): string {
  if (!block) {
    return block
  }
  return block.replace(
    /<pre(\b[^>]*)>([\s\S]*?)<\/pre>/i,
    (_full, attrs: string, inner: string) => {
      const codeMatch = inner.match(/^(\s*<code(\b[^>]*)>)([\s\S]*?)(<\/code>\s*)$/i)
      if (codeMatch) {
        const [, open, , body, close] = codeMatch
        return `<pre${attrs}>${open}${escapePreCodeBody(body)}${close}</pre>`
      }
      return `<pre${attrs}>${escapePreCodeBody(inner)}</pre>`
    },
  )
}

function escapePreCodeBody(body: string): string {
  const normalized = body.replace(/<br\s*\/?>/gi, '\n')
  const hasRawTags = /<\/?[a-zA-Z][!?\w:-]*\b[^>]*>/.test(normalized)
  if (!hasRawTags) {
    return normalized
  }

  const plain = normalized
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
  return escapeHtml(plain)
}

function stripTablePresentation(html: string): string {
  return html.replace(
    /<(table|thead|tbody|tfoot|tr|th|td)(\s[^>]*)?>/gi,
    (_match, tag: string, attrs: string | undefined) => {
      if (!attrs) {
        return `<${tag}>`
      }
      const cleaned = attrs
        .replace(/\s+style\s*=\s*(['"])[\s\S]*?\1/gi, '')
        .replace(/\s+bgcolor\s*=\s*(['"]?)[^'\s>]*\1/gi, '')
        .replace(/\s+color\s*=\s*(['"]?)[^'\s>]*\1/gi, '')
        .replace(/\s+background\s*=\s*(['"]?)[^'\s>]*\1/gi, '')
      return `<${tag}${cleaned}>`
    },
  )
}

function htmlBlockToPlain(inner: string): string {
  return inner
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<\/p>/gi, '\n')
    .replace(/<[^>]+>/g, '')
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
}

export function hydrateAsciiTablesInHtml(html: string): string {
  if (!html) {
    return html
  }
  let out = html.replace(/<pre(?:\s[^>]*)?>([\s\S]*?)<\/pre>/gi, (match, inner: string) => {
    const plain = htmlBlockToPlain(inner)
    return asciiTableToHtml(plain) ?? match
  })
  out = out.replace(/<p(?:\s[^>]*)?>((?:[\s\S]*?<br\s*\/?>){2,}[\s\S]*?)<\/p>/gi, (match, inner: string) => {
    if (/<table\b/i.test(inner)) {
      return match
    }
    const plain = htmlBlockToPlain(inner)
    return asciiTableToHtml(plain) ?? match
  })
  return out
}

export function isSubstantialStudyHtml(html: string, title = ''): boolean {
  const text = html
    .replace(/<[^>]+>/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
  if (!text) {
    return false
  }
  const normalizedTitle = title.replace(/\s+/g, ' ').trim()
  if (normalizedTitle && text === normalizedTitle) {
    return false
  }
  return text.length > Math.max(48, normalizedTitle.length + 8)
}

export function looksLikeHtml(value: string): boolean {

  return /<\/?(?:p|div|span|h[1-6]|ul|ol|li|pre|code|table|thead|tbody|tr|td|th|br|hr|a|img|strong|em|b|i|blockquote|section|article|figure|figcaption|header|footer|main|nav)\b/i.test(
    value,
  )
}

export function studyBodyToHtml(value: string): string {
  const text = repairMarkdownFences(value.trim())
  if (!text) {
    return ''
  }

  const solePre = text.match(
    /^\s*<pre\b[^>]*>\s*<code\b[^>]*>([\s\S]*?)<\/code>\s*<\/pre>\s*$/i,
  )
  if (solePre) {
    const inner = htmlBlockToPlain(solePre[1]).trim()
    if (shouldUnwrapProseFence('text', inner) || looksLikeMarkdown(inner)) {
      return sanitizeStudyHtml(markdownToStudyHtml(inner))
    }
  }

  const htmlish = looksLikeHtml(text)
  const mdish = looksLikeMarkdown(text)

  if (htmlish && (!mdish || /^\s*</.test(text))) {
    return sanitizeStudyHtml(text)
  }
  if (mdish) {
    return sanitizeStudyHtml(markdownToStudyHtml(text))
  }
  if (htmlish) {
    return sanitizeStudyHtml(text)
  }
  return sanitizeStudyHtml(plainToStudyHtml(text))
}

export function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
}

export function asciiTableToHtml(block: string): string | null {
  const lines = block
    .split('\n')
    .map((line) => line.replace(/\u00a0/g, ' ').replace(/\s+$/g, ''))
    .filter((line) => line.trim().length > 0)
  if (lines.length < 2) {
    return null
  }
  const splitRow = (line: string): string[] => {
    const normalized = line.replace(/\u00a0/g, ' ')
    if (normalized.includes('\t')) {
      return normalized.split('\t').map((cell) => cell.trim()).filter(Boolean)
    }
    if (/\s{2,}/.test(normalized)) {
      return normalized.split(/\s{2,}/).map((cell) => cell.trim()).filter(Boolean)
    }
    return []
  }
  const rows = lines.map(splitRow)
  if (rows.some((row) => row.length < 2)) {
    return null
  }
  const width = rows[0].length
  if (width < 2 || rows.some((row) => row.length !== width)) {
    return null
  }
  const [header, ...body] = rows
  const th = header.map((cell) => `<th>${escapeHtml(cell)}</th>`).join('')
  const tr = body
    .map((row) => `<tr>${row.map((cell) => `<td>${escapeHtml(cell)}</td>`).join('')}</tr>`)
    .join('')
  return `<div class="table-wrap"><table><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></div>`
}

function isListBlock(block: string): boolean {
  const lines = block.split('\n').map((line) => line.trim()).filter(Boolean)
  if (lines.length < 2) {
    return false
  }
  return lines.every((line) => /^(?:[-*•]|\d+[.)])\s+\S/.test(line))
}

function splitPlainChunks(text: string): string[] {
  const blocks = text.split(/\n\s*\n+/).map((part) => part.trim()).filter(Boolean)
  const chunks: string[] = []
  for (const block of blocks) {
    if (markdownPipeTableBlockToHtml(block) || asciiTableToHtml(block) || isListBlock(block)) {
      chunks.push(block)
      continue
    }
    const lines = block.split('\n').map((line) => line.replace(/\s+$/g, '')).filter((line) => line.trim())
    const tabularLines = lines.filter((line) => /\t|\s{2,}/.test(line))
    if (lines.length >= 2 && tabularLines.length === lines.length) {
      chunks.push(block)
      continue
    }
    if (lines.length > 1) {
      chunks.push(...lines.map((line) => line.trim()).filter(Boolean))
      continue
    }
    chunks.push(block)
  }
  return chunks
}

export function looksLikeMarkdown(value: string): boolean {
  const text = value.trim()
  if (!text) {
    return false
  }
  if (/^#{1,6}\s+\S/m.test(text)) {
    return true
  }

  if (/```[\s\S]*?```/.test(text) || /^`{2,}\w*\s*$/m.test(text)) {
    return true
  }

  if (/^\|.+\|\s*$/m.test(text) && /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/m.test(text)) {
    return true
  }
  if (/!\[[^\]]*]\(\s*https?:\/\/[^)]+\)/.test(text)) {
    return true
  }
  if (/\[[^\]]+]\(\s*https?:\/\/[^)]+\)/.test(text)) {
    return true
  }
  if (/^\s*>\s+\S/m.test(text)) {
    return true
  }
  return false
}

export function repairMarkdownFences(markdown: string): string {
  if (!markdown || !markdown.includes('`')) {
    return markdown
  }
  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  let open = false
  const out: string[] = []
  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i]
    const match = line.match(/^\s*(`{2,})([A-Za-z][\w+-]*)?\s*$/)
    if (!match) {
      out.push(line)
      continue
    }
    if (!open) {
      const lang = match[2] || ''
      if (!lang) {
        let peek = i + 1
        while (peek < lines.length && !lines[peek].trim()) {
          peek += 1
        }
        if (peek >= lines.length || !lineLooksLikePythonCode(lines[peek], false)) {
          continue
        }
      }
      open = true
      out.push(lang ? `\`\`\`${lang}` : '```')
      continue
    }
    // LLM часто «закрывает» блок как ```text / ```bash — это закрытие, не новый язык.
    open = false
    out.push('```')
  }
  if (open) {
    out.push('```')
  }
  return healOrphanedPythonFences(out.join('\n'))
}

const PYTHON_START =
  /^(?:(?:async\s+)?def\s+\w+|class\s+\w+|from\s+\S+\s+import\b|import\s+\S+|@\w+)/
const PYTHON_CONTINUE =
  /^(?:[ \t]+\S|#|(?:else|elif|except|finally|try|with|for|while|if|return|raise|pass|yield|await)\b|[)\]}])/
const PROSE_LINE = /^(?:#{1,6}\s+\S|[-*+]\s+\S|\d+\.\s+\S|>\s+\S)/

function lineLooksLikePythonCode(line: string, prevWasCode: boolean): boolean {
  const stripped = line.replace(/\s+$/, '')
  if (!stripped) {
    return false
  }
  if (stripped.startsWith('```')) {
    return false
  }
  if (PROSE_LINE.test(stripped)) {
    return false
  }
  const letters = stripped.match(/[A-Za-zА-Яа-яЁё]/g) || []
  const cyr = letters.filter((ch) => /[А-Яа-яЁё]/.test(ch)).length
  if (
    letters.length
    && cyr / letters.length >= 0.45
    && !stripped.includes('def ')
    && !stripped.includes('class ')
    && !/^[ \t]/.test(stripped)
  ) {
    return false
  }
  if (PYTHON_START.test(stripped)) {
    return true
  }
  if (prevWasCode && PYTHON_CONTINUE.test(stripped)) {
    return true
  }
  if (/^def\s+(?:__)?\w+\s*\(/.test(stripped) || /^class\s+\w+/.test(stripped)) {
    return true
  }
  return false
}

/** LLM closes ``` early; leftover Python becomes Markdown and `__set__` → bold "set". */
export function healOrphanedPythonFences(markdown: string): string {
  if (!markdown) {
    return markdown
  }
  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  const out: string[] = []
  let index = 0
  const fenceLine = /^\s*(`{2,})([A-Za-z][\w+-]*)?\s*$/

  const absorbLeaked = (body: string[]) => {
    while (index < lines.length) {
      const current = lines[index]
      if (fenceLine.test(current)) {
        let peek = index + 1
        while (peek < lines.length && !lines[peek].trim()) {
          peek += 1
        }
        if (peek < lines.length && lineLooksLikePythonCode(lines[peek], true)) {
          index += 1
          continue
        }
        break
      }
      if (lineLooksLikePythonCode(current, body.length > 0)) {
        body.push(current)
        index += 1
        continue
      }
      if (!current.trim()) {
        let peek = index + 1
        while (peek < lines.length && !lines[peek].trim()) {
          peek += 1
        }
        if (peek < lines.length && lineLooksLikePythonCode(lines[peek], true)) {
          body.push(current)
          index += 1
          continue
        }
      }
      break
    }
  }

  while (index < lines.length) {
    const line = lines[index]
    const fence = line.match(fenceLine)
    if (fence) {
      let lang = fence[2] || ''
      const body: string[] = []
      index += 1
      while (index < lines.length && !fenceLine.test(lines[index])) {
        body.push(lines[index])
        index += 1
      }
      if (index < lines.length) {
        index += 1
      }
      absorbLeaked(body)
      while (body.length && !body[body.length - 1].trim()) {
        body.pop()
      }
      const joined = body.join('\n')
      if (!lang || /^(?:text|plain|plaintext)$/i.test(lang)) {
        if (/\b(?:def|class|import)\b/.test(joined)) {
          lang = 'python'
        }
      }
      out.push(lang ? `\`\`\`${lang}` : '```', ...body, '```')
      continue
    }
    if (lineLooksLikePythonCode(line, false)) {
      const body: string[] = []
      absorbLeaked(body)
      while (body.length && !body[body.length - 1].trim()) {
        body.pop()
      }
      if (body.length) {
        out.push('```python', ...body, '```')
      }
      continue
    }
    out.push(line)
    index += 1
  }
  return out.join('\n')
}

function inlineMarkdown(text: string): string {
  let out = escapeHtml(repairMojibake(text))
  out = out.replace(/!\[([^\]]*)]\((https?:[^)\s]+)(?:\s+"[^"]*")?\)/g, (_m, alt: string, src: string) => {
    return `<img src="${src}" alt="${alt}" loading="lazy" />`
  })
  out = out.replace(/\[([^\]]+)]\((https?:[^)\s]+)(?:\s+"[^"]*")?\)/g, (_m, label: string, href: string) => {
    return `<a href="${href}" target="_blank" rel="noopener noreferrer">${label}</a>`
  })
  out = out.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
  out = out.replace(/__([^_]+)__/g, '<strong>$1</strong>')
  out = out.replace(/(?<!\*)\*([^*\n]+)\*(?!\*)/g, '<em>$1</em>')
  out = out.replace(/`([^`]+)`/g, '<code>$1</code>')
  return out
}

function dedentFenceBody(raw: string): string {
  const lines = raw.replace(/\r\n/g, '\n').split('\n')
  let minIndent = Number.POSITIVE_INFINITY
  for (const line of lines) {
    if (!line.trim()) {
      continue
    }
    const match = line.match(/^[ \t]*/)?.[0] ?? ''
    minIndent = Math.min(minIndent, match.length)
  }
  if (!Number.isFinite(minIndent) || minIndent <= 0) {
    return raw.trimEnd()
  }
  return lines
    .map((line) => (line.trim() ? line.slice(minIndent) : line))
    .join('\n')
    .replace(/^\n+/, '')
    .replace(/\n+$/, '')
}

function isMarkdownPipeSeparator(line: string): boolean {
  const trimmed = line.trim()
  if (!trimmed.includes('-') || !trimmed.includes('|')) {
    return false
  }

  return /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/.test(trimmed)
}

function splitMarkdownPipeRow(line: string): string[] {
  let trimmed = line.trim()
  if (trimmed.startsWith('|')) {
    trimmed = trimmed.slice(1)
  }
  if (trimmed.endsWith('|')) {
    trimmed = trimmed.slice(0, -1)
  }
  return trimmed.split('|').map((cell) => cell.trim())
}

export function consumeMarkdownPipeTable(
  lines: string[],
  start: number,
): { html: string; next: number } | null {
  if (start + 1 >= lines.length) {
    return null
  }
  const headerLine = lines[start]
  const sepLine = lines[start + 1]
  if (!headerLine.includes('|') || !isMarkdownPipeSeparator(sepLine)) {
    return null
  }
  const header = splitMarkdownPipeRow(headerLine)
  if (header.length < 2 || header.every((cell) => !cell)) {
    return null
  }
  const body: string[][] = []
  let i = start + 2
  while (i < lines.length) {
    const rowLine = lines[i]
    if (!rowLine.trim()) {
      break
    }
    if (!rowLine.includes('|') || isMarkdownPipeSeparator(rowLine)) {
      break
    }
    const cells = splitMarkdownPipeRow(rowLine)
    if (cells.length < 2) {
      break
    }

    const normalized = header.map((_, index) => cells[index] ?? '')
    body.push(normalized)
    i += 1
  }
  if (!body.length) {
    return null
  }
  const th = header.map((cell) => `<th>${inlineMarkdown(cell)}</th>`).join('')
  const tr = body
    .map((row) => `<tr>${row.map((cell) => `<td>${inlineMarkdown(cell)}</td>`).join('')}</tr>`)
    .join('')
  return {
    html: `<div class="table-wrap"><table><thead><tr>${th}</tr></thead><tbody>${tr}</tbody></table></div>`,
    next: i,
  }
}

export function markdownPipeTableBlockToHtml(block: string): string | null {
  const lines = block.replace(/\r\n/g, '\n').split('\n')
  let start = 0
  while (start < lines.length && !lines[start].trim()) {
    start += 1
  }
  const parsed = consumeMarkdownPipeTable(lines, start)
  if (!parsed) {
    return null
  }
  if (lines.slice(parsed.next).some((line) => line.trim())) {
    return null
  }
  return parsed.html
}

function promoteBareMermaidFences(markdown: string): string {
  const lines = markdown.replace(/\r\n/g, '\n').split('\n')
  const out: string[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    const openFence = line.match(/^\s*```([\w+-]*)?\s*$/)
    if (openFence) {
      out.push(line)
      i += 1
      while (i < lines.length && !/^\s*```[\w+-]*\s*$/.test(lines[i])) {
        out.push(lines[i])
        i += 1
      }
      if (i < lines.length) {
        out.push('```')
        i += 1
      }
      continue
    }
    if (/^\s*(?:graph|flowchart|sequenceDiagram|classDiagram|stateDiagram(?:-v2)?|erDiagram)\b/i.test(line)) {
      const start = i
      const body: string[] = []
      while (i < lines.length) {
        const cur = lines[i]
        if (!cur.trim()) {
          break
        }
        if (/^#{1,6}\s+\S/.test(cur) || /^\s*```/.test(cur)) {
          break
        }
        body.push(cur)
        i += 1
      }
      if (isMermaidBlock(body.join('\n'))) {
        out.push('```mermaid', ...body, '```')
        continue
      }
      i = start
    }
    out.push(line)
    i += 1
  }
  return out.join('\n')
}

function shouldUnwrapProseFence(lang: string, body: string): boolean {
  const hint = (lang || '').trim()
  if (hint && !/^(?:text|plain|txt|md|markdown)?$/i.test(hint)) {
    return false
  }
  const trimmed = body.trim()
  if (!trimmed || trimmed.length < 40) {
    return false
  }
  // Pure diagram fences stay code/mermaid — only unwrap when prose/markdown leaked in.
  const hasHeading = /^#{1,6}\s+\S/m.test(trimmed)
  const hasPipeTable = /^\|.+\|\s*$/m.test(trimmed)
    && /^\|?\s*:?-{3,}:?\s*(\|\s*:?-{3,}:?\s*)+\|?\s*$/m.test(trimmed)
  const hasCallout = /^\s*>\s+\S/m.test(trimmed)
  const hasBoldLine = /^\*\*[^*\n]{3,120}\*\*\.?$/m.test(trimmed)
  if (hasHeading || hasPipeTable || hasCallout || hasBoldLine) {
    return true
  }
  const hasMermaid = isMermaidBlock(trimmed, hint)
  const numberedSection = /^[0-9]+\.\s+\S.+/m.test(trimmed)
  if (hasMermaid && numberedSection && trimmed.length > 220) {
    return true
  }
  return false
}

export function markdownToStudyHtml(markdown: string): string {
  const cleaned = promoteBareMermaidFences(
    repairMarkdownFences(markdown.replace(/\r\n/g, '\n').trim()),
  )
  if (!cleaned) {
    return ''
  }

  const parts: string[] = []
  const lines = cleaned.split('\n')
  let i = 0
  let paragraph: string[] = []

  const flushParagraph = () => {
    if (!paragraph.length) {
      return
    }
    const text = paragraph.join('\n').trim()
    paragraph = []
    if (!text) {
      return
    }
    parts.push(`<p>${inlineMarkdown(text).replace(/\n/g, '<br />')}</p>`)
  }

  while (i < lines.length) {
    const line = lines[i]

    const fence = line.match(/^\s*```([\w+-]*)?\s*$/)
    if (fence) {
      flushParagraph()
      const lang = fence[1] || ''
      const body: string[] = []
      i += 1
      while (i < lines.length && !/^\s*```[\w+-]*\s*$/.test(lines[i])) {
        body.push(lines[i])
        i += 1
      }
      const raw = body.join('\n')

      let codeBody = dedentFenceBody(raw)
      if (shouldUnwrapProseFence(lang, codeBody)) {
        // LLM often wraps a whole theory slide in ```text … ``` — re-parse as markdown.
        const nested = markdownToStudyHtml(codeBody)
        if (nested.trim()) {
          parts.push(nested)
          i += 1
          continue
        }
      }
      if (/^mermaid$/i.test(lang) || isMermaidBlock(codeBody, lang)) {
        codeBody = repairMermaidSource(codeBody)
      }
      const code = escapeHtml(codeBody)
      const asMermaid = /^mermaid$/i.test(lang) || isMermaidBlock(codeBody, lang)
      const langAttr = asMermaid
        ? ` class="language-${escapeHtml(lang && lang !== 'text' ? lang : 'mermaid')}"`
        : lang
          ? ` class="language-${escapeHtml(lang)}"`
          : ''
      parts.push(`<pre><code${langAttr}>${code}</code></pre>`)
      i += 1
      continue
    }

    const heading = line.match(/^(#{1,6})\s+(.+)$/)
    if (heading) {
      flushParagraph()
      const level = Math.min(heading[1].length, 4)
      const tag = level <= 2 ? 'h2' : 'h3'
      parts.push(`<${tag} class="study-section-title">${inlineMarkdown(heading[2].trim())}</${tag}>`)
      i += 1
      continue
    }

    const pipeTable = consumeMarkdownPipeTable(lines, i)
    if (pipeTable) {
      flushParagraph()
      parts.push(pipeTable.html)
      i = pipeTable.next
      continue
    }

    if (/^\s*([-*_] ?)\1{2,}\s*$/.test(line)) {
      flushParagraph()
      parts.push('<hr />')
      i += 1
      continue
    }

    if (/^\s*>\s?/.test(line)) {
      flushParagraph()
      const quote: string[] = []
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
        quote.push(lines[i].replace(/^\s*>\s?/, ''))
        i += 1
      }
      const joined = quote.join('\n').trim()
      const label = joined.match(
        /^\*\*(Важно|Ловушка|Gap(?:\s+fill)?|Note|Tip|Warning|Caution):?\*\*:?\s*/i,
      )
      if (label) {
        const kindRaw = label[1].toLowerCase()
        const kind =
          /ловушка|warning|caution/.test(kindRaw)
            ? 'trap'
            : /gap/.test(kindRaw)
              ? 'gap'
              : /tip|note/.test(kindRaw)
                ? 'tip'
                : 'note'
        const rest = joined.slice(label[0].length)
        parts.push(
          `<aside class="study-callout study-callout-${kind}" data-callout="${kind}">`
            + `<div class="study-callout-label">${escapeHtml(label[1])}</div>`
            + `<div class="study-callout-body">${inlineMarkdown(rest).replace(/\n/g, '<br />')}</div>`
            + `</aside>`,
        )
      } else {
        parts.push(
          `<blockquote>${inlineMarkdown(joined).replace(/\n/g, '<br />')}</blockquote>`,
        )
      }
      continue
    }

    if (/^\s*(?:[-*•]|\d+[.)])\s+\S/.test(line)) {
      flushParagraph()
      const items: { ordered: boolean; text: string }[] = []
      while (i < lines.length && /^\s*(?:[-*•]|\d+[.)])\s+\S/.test(lines[i])) {
        const match = lines[i].trim().match(/^(?:[-*•]|(\d+)[.)])\s+(.+)$/)
        if (match) {
          items.push({ ordered: Boolean(match[1]), text: match[2] })
        }
        i += 1
      }
      if (items.length) {
        const ordered = items.every((item) => item.ordered)
        const tag = ordered ? 'ol' : 'ul'
        parts.push(
          `<${tag}>${items.map((item) => `<li>${inlineMarkdown(item.text)}</li>`).join('')}</${tag}>`,
        )
      }
      continue
    }

    if (!line.trim()) {
      flushParagraph()
      i += 1
      continue
    }

    if (/^\s*!\[[^\]]*]\(\s*https?:\/\/[^)]+\)\s*$/.test(line)) {
      flushParagraph()
      parts.push(`<p class="study-figure">${inlineMarkdown(line.trim())}</p>`)
      i += 1
      continue
    }

    paragraph.push(line)
    i += 1
  }
  flushParagraph()
  return parts.join('')
}

export function plainToStudyHtml(text: string): string {
  const cleaned = text.replace(/\r\n/g, '\n').trim()
  if (!cleaned) {
    return ''
  }

  const asWholeTable = markdownPipeTableBlockToHtml(cleaned) || asciiTableToHtml(cleaned)
  if (asWholeTable) {
    return asWholeTable
  }

  const chunks = splitPlainChunks(cleaned)

  const htmlParts: string[] = []
  for (const chunk of chunks) {
    const asTable = markdownPipeTableBlockToHtml(chunk) || asciiTableToHtml(chunk)
    if (asTable) {
      htmlParts.push(asTable)
      continue
    }

    const headingMatch = chunk.match(/^\*\*(.+?)\*\*\.?$/)
      || chunk.match(/^([^*\n]{3,100})\n[-=]{3,}$/)
    if (headingMatch?.[1] && !/[.!?…]$/.test(headingMatch[1].trim())) {
      htmlParts.push(`<h3 class="study-section-title">${escapeHtml(headingMatch[1].trim())}</h3>`)
      continue
    }

    if (
      chunk.length <= 110
      && !chunk.includes('\n')
      && !/[.!?…:]$/.test(chunk)
      && /^[A-ZА-ЯЁ0-9「『«"]/.test(chunk)
      && !/\s{2,}/.test(chunk)
    ) {
      const words = chunk.split(/\s+/).length
      if (words >= 2 && words <= 14) {
        htmlParts.push(`<h3 class="study-section-title">${escapeHtml(chunk)}</h3>`)
        continue
      }
    }

    let paragraphs = [chunk]
    if (chunk.includes('\n') && !/\s{2,}/.test(chunk)) {
      paragraphs = chunk.split('\n').map((part) => part.trim()).filter(Boolean)
    } else if (chunk.length > 220 && !chunk.includes('\n')) {
      const sentences = chunk.split(/(?<=[.!?…])\s+/).map((part) => part.trim()).filter(Boolean)
      const grouped: string[] = []
      let buf: string[] = []
      for (const sentence of sentences) {
        buf.push(sentence)
        if (buf.length >= 2 || buf.join(' ').length >= 220) {
          grouped.push(buf.join(' '))
          buf = []
        }
      }
      if (buf.length) {
        grouped.push(buf.join(' '))
      }
      paragraphs = grouped.length ? grouped : paragraphs
    }

    if (isListBlock(chunk)) {
      const listItems = chunk
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean)
        .map((line) => {
          const match = line.match(/^(?:[-*•]|(\d+)[.)])\s+(.+)$/)
          return match ? { ordered: Boolean(match[1]), text: match[2] } : null
        })
        .filter((item): item is { ordered: boolean; text: string } => item !== null)
      if (listItems.length >= 2) {
        const ordered = listItems.every((item) => item.ordered)
        const tag = ordered ? 'ol' : 'ul'
        const items = listItems
          .map((item) => `<li>${escapeHtml(item.text).replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')}</li>`)
          .join('')
        htmlParts.push(`<${tag}>${items}</${tag}>`)
        continue
      }
    }

    for (const paragraph of paragraphs) {
      const withInline = escapeHtml(repairMojibake(paragraph))
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
      htmlParts.push(`<p>${withInline}</p>`)
    }
  }

  return htmlParts.join('')
}

export function youtubeEmbedSrc(url: string): string | null {
  try {
    const parsed = new URL(url)
    const host = parsed.hostname.replace(/^www\./, '')
    if (host === 'youtu.be') {
      const id = parsed.pathname.replace(/^\//, '')
      return id ? `https://www.youtube.com/embed/${id}?rel=0&modestbranding=1` : null
    }
    if (host === 'youtube.com' || host === 'm.youtube.com' || host === 'youtube-nocookie.com') {
      if (parsed.pathname.startsWith('/embed/')) {
        return `https://www.youtube.com${parsed.pathname}?rel=0&modestbranding=1`
      }
      const id = parsed.searchParams.get('v')
      return id ? `https://www.youtube.com/embed/${id}?rel=0&modestbranding=1` : null
    }
  } catch {
    return null
  }
  return null
}
