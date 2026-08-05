import DOMPurify from 'isomorphic-dompurify'

const STUDY_TAGS = [
  'a',
  'aside',
  'b',
  'blockquote',
  'br',
  'code',
  'div',
  'em',
  'figcaption',
  'figure',
  'h1',
  'h2',
  'h3',
  'h4',
  'hr',
  'i',
  'img',
  'li',
  'ol',
  'p',
  'pre',
  'span',
  'strong',
  'table',
  'tbody',
  'td',
  'th',
  'thead',
  'tr',
  'ul',
] as const

const STUDY_ATTR = [
  'alt',
  'class',
  'colspan',
  'data-callout',
  'href',
  'loading',
  'rel',
  'rowspan',
  'src',
  'target',
  'title',
] as const

export function purifyStudyHtml(dirty: string): string {
  if (!dirty) {
    return ''
  }
  return DOMPurify.sanitize(dirty, {
    ALLOWED_TAGS: [...STUDY_TAGS],
    ALLOWED_ATTR: [...STUDY_ATTR],
    ALLOW_DATA_ATTR: false,
    ADD_ATTR: ['target'],
  })
}
