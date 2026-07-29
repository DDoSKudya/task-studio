import { describe, expect, it } from 'vitest'

import { detectCodeLanguage, highlightStudyCode } from './highlightCode'

describe('detectCodeLanguage', () => {
  it('detects sql select', () => {
    expect(detectCodeLanguage('SELECT id FROM users')).toBe('sql')
  })

  it('detects sql CTE without mistaking python with-as', () => {
    expect(detectCodeLanguage('WITH paid AS (\n  SELECT 1\n)\nSELECT * FROM paid')).toBe('sql')
  })

  it('detects python with Session as context manager (not sql)', () => {
    const sample = `with Session(engine) as session:
    # Открыли Unit of Work
    order = Order(user_id=1, total=500)
    session.add(order)
    session.commit()`
    expect(detectCodeLanguage(sample)).toBe('python')
    expect(detectCodeLanguage(sample, 'sql')).toBe('python')
  })

  it('detects short sqlalchemy flush snippet as python', () => {
    const sample = `order = Order(user_id=1, total=100)
session.add(order)
session.flush()
# SQL INSERT ушел, но транзакция не закрыта`
    expect(detectCodeLanguage(sample)).toBe('python')
    expect(detectCodeLanguage(sample, 'text')).toBe('python')
  })

  it('respects python fence hint', () => {
    expect(detectCodeLanguage('x = 1', 'python')).toBe('python')
  })
})

describe('highlightStudyCode', () => {
  it('detects sql and wraps keywords', () => {
    expect(detectCodeLanguage('SELECT id FROM users')).toBe('sql')
    const html = highlightStudyCode('SELECT id FROM users', 'sql')
    expect(html).toContain('class="tok-kw"')
    expect(html).toContain('SELECT')
  })

  it('escapes markup in code', () => {
    const html = highlightStudyCode('print("<b>")', 'python')
    expect(html).toContain('&lt;b&gt;')
    expect(html).not.toContain('<b>')
    expect(html).toContain('<span class="tok-str">')
  })

  it('does not nest string spans inside keyword class attributes', () => {
    const html = highlightStudyCode(
      'def create_order(data):\n    with Session(engine) as session:\n        try:\n            return {"id": 1}\n        except IntegrityError:\n            raise',
      'python',
    )
    expect(html).not.toContain('tok-str">"tok-kw"')
    expect(html).not.toContain('class=<span')
    expect(html).toContain('<span class="tok-kw">def</span>')
    expect(html).toContain('<span class="tok-kw">with</span>')
    expect(html).toContain('<span class="tok-kw">as</span>')
    expect(html).toContain('<span class="tok-kw">try</span>')
    expect(html).toContain('<span class="tok-kw">return</span>')
    expect(html).toContain('<span class="tok-kw">except</span>')
    expect(html).toContain('<span class="tok-kw">raise</span>')
    expect(html).toContain('<span class="tok-str">')
  })

  it('does not highlight keywords inside strings', () => {
    const html = highlightStudyCode('msg = "def not a keyword"', 'python')
    expect(html).toContain('<span class="tok-str">"def not a keyword"</span>')
    expect(html).not.toMatch(/tok-str">.*tok-kw/)
  })
})
