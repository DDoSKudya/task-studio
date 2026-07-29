import { describe, expect, it } from 'vitest'

import { tutorMessageHtml } from './chatHtml'

describe('tutorMessageHtml', () => {
  it('renders bold and inline code', () => {
    const html = tutorMessageHtml('Use **SELECT** with `*`')
    expect(html).toContain('<strong>SELECT</strong>')
    expect(html).toContain('<code>*</code>')
    expect(html).not.toContain('**')
  })

  it('renders fenced sql as a code card', () => {
    const html = tutorMessageHtml('Example:\n\n```sql\nSELECT * FROM cadets;\n```')
    expect(html).toContain('session-tutor-code')
    expect(html).toContain('SELECT')
    expect(html).not.toContain('```')
  })

  it('renders bullet lists', () => {
    const html = tutorMessageHtml('- one\n- two')
    expect(html).toContain('<ul>')
    expect(html).toContain('<li>')
  })
})
