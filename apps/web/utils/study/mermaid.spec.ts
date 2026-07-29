import { describe, expect, it } from 'vitest'
import { isMermaidBlock, repairMermaidSource } from './mermaid'

describe('isMermaidBlock', () => {
  it('trusts mermaid fence language', () => {
    expect(isMermaidBlock('not a diagram', 'mermaid')).toBe(true)
    expect(isMermaidBlock('x', 'language-mermaid')).toBe(true)
    expect(isMermaidBlock('x', 'mmd')).toBe(true)
  })

  it('detects flowchart bodies without a fence tag', () => {
    const code = [
      'graph TD',
      '    A[URL-маршруты] --> B[Вьюхи]',
      '    B --> C[Модели]',
      '    B --> D[Шаблоны]',
    ].join('\n')
    expect(isMermaidBlock(code)).toBe(true)
    expect(isMermaidBlock(code, 'text')).toBe(true)
  })

  it('ignores ordinary code', () => {
    expect(isMermaidBlock('def post_list(request):\n    return posts')).toBe(false)
    expect(isMermaidBlock('SELECT id FROM posts', 'sql')).toBe(false)
  })
})

describe('repairMermaidSource', () => {
  it('quotes node labels that contain parentheses (LLM Redis/Postgres diagrams)', () => {
    const raw = [
      'graph TD',
      '  A[Приложение] -->|пишет| B[Доска у входа(Redis)]',
      '  A -->|читает| B',
      '  A -->|пишет| C[Архив(PostgreSQL)]',
      '  B -->|временное состояние| A',
      '  C -->|долговечные данные| A',
      '  B -->|штампы| A',
    ].join('\n')
    const fixed = repairMermaidSource(raw)
    expect(fixed).toContain('A["Приложение"]')
    expect(fixed).toContain('B["Доска у входа(Redis)"]')
    expect(fixed).toContain('C["Архив(PostgreSQL)"]')
    expect(fixed).toContain(' -->|"пишет"| ')
    expect(fixed).toContain(' -->|"временное состояние"| ')
    expect(fixed).not.toContain('B[Доска у входа(Redis)]')
  })

  it('strips wrapping fences and keeps already-quoted labels', () => {
    const raw = '```mermaid\ngraph LR\n  X["ok (1)"] --> Y[plain]\n```'
    const fixed = repairMermaidSource(raw)
    expect(fixed.startsWith('graph LR')).toBe(true)
    expect(fixed).toContain('X["ok (1)"]')
    expect(fixed).toContain('Y[plain]')
    expect(fixed).not.toContain('```')
  })
})
