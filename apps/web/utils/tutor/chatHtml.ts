import {
  detectCodeLanguage,
  highlightStudyCode,
  markdownToStudyHtml,
  sanitizeStudyHtml,
} from '../study'

function decodeBasicEntities(text: string): string {
  return text
    .replace(/<[^>]+>/g, '')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/&amp;/g, '&')
}


export function tutorMessageHtml(content: string): string {
  const text = content.trim()
  if (!text) {
    return ''
  }
  let html = sanitizeStudyHtml(markdownToStudyHtml(text))
  html = html.replace(
    /<pre(?:\s[^>]*)?><code(?:\s+class="language-([^"]*)")?>([\s\S]*?)<\/code><\/pre>/gi,
    (_match, langAttr: string | undefined, inner: string) => {
      const code = decodeBasicEntities(inner)
      const lang = detectCodeLanguage(code, langAttr || '')
      const highlighted = highlightStudyCode(code, lang)
      return (
        `<div class="study-code session-tutor-code">`
        + `<div class="study-code-bar"><span>${lang}</span></div>`
        + `<pre><code class="language-${lang}">${highlighted}</code></pre>`
        + `</div>`
      )
    },
  )
  return html
}
