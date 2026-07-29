import { describe, expect, it } from 'vitest'

import {
  asciiTableToHtml,
  looksLikeHtml,
  looksLikeMarkdown,
  markdownToStudyHtml,
  plainToStudyHtml,
  repairMojibake,
  sanitizeStudyHtml,
  studyBodyToHtml,
} from './sanitizeHtml'

describe('sanitizeStudyHtml', () => {
  it('promotes first table row to headers and wraps the table', () => {
    const html = sanitizeStudyHtml(
      '<table><tr><td>A</td><td>B</td></tr><tr><td>1</td><td>2</td></tr></table>',
    )
    expect(html).toContain('class="table-wrap"')
    expect(html).toContain('<thead>')
    expect(html).toContain('<th>A</th>')
    expect(html).toContain('<td>1</td>')
  })

  it('promotes bold-only paragraphs to section titles', () => {
    const html = sanitizeStudyHtml('<p><strong>Целостность данных</strong></p><p>Text.</p>')
    expect(html).toContain('study-section-title')
    expect(html).toContain('Целостность данных')
    expect(html).toContain('<p>Text.</p>')
  })

  it('decodes escaped HTML markup buried as entities', () => {
    const html = sanitizeStudyHtml('&lt;p&gt;&lt;strong&gt;Заголовок&lt;/strong&gt;&lt;/p&gt;')
    expect(html).toContain('Заголовок')
    expect(html).not.toContain('&lt;p&gt;')
    expect(html).toMatch(/<(?:p|h3)\b/)
  })

  it('hydrates preformatted spreadsheet dumps into real tables', () => {
    const html = sanitizeStudyHtml(
      '<p>Пример</p><pre>OrderID  OrderDate  Name\n1  2025-10-01  Anna\n2  2025-10-02  Bob</pre>',
    )
    expect(html).toContain('<table>')
    expect(html).toContain('<th>OrderID</th>')
    expect(html).toContain('<td>Anna</td>')
    expect(html).not.toContain('<pre>')
  })

  it('strips baked table presentation so skin CSS can control contrast', () => {
    const html = sanitizeStudyHtml(
      '<table bgcolor="#ffffff" style="color:#fff"><tr style="background:white"><td color="#fff" style="background:#fff;color:#fff">X</td></tr></table>',
    )
    expect(html).toContain('<table>')
    expect(html).toContain('<td>X</td>')
    expect(html).not.toMatch(/bgcolor=/i)
    expect(html).not.toMatch(/style=/i)
    expect(html).not.toMatch(/\scolor=/i)
  })
})

describe('repairMojibake', () => {
  it('restores Cyrillic from Latin-1 misdecode', () => {
    const broken = Buffer.from('Теория', 'utf8').toString('latin1')
    expect(repairMojibake(broken)).toBe('Теория')
  })
})

describe('markdownToStudyHtml', () => {
  it('renders headings, images, and fenced code', () => {
    const md = [
      '# Introduction',
      '',
      '## Example 1',
      '',
      '![Seven nests](https://assets.exercism.org/images/exercises/eliuds-eggs/example-1-coop.svg)',
      '',
      '```text',
      '|E| |E|E| | |E|',
      '```',
      '',
      'Count the eggs.',
    ].join('\n')
    const html = markdownToStudyHtml(md)
    expect(html).toContain('<h2')
    expect(html).toContain('Introduction')
    expect(html).toContain('<img src="https://assets.exercism.org/images/exercises/eliuds-eggs/example-1-coop.svg"')
    expect(html).toContain('<pre><code')
    expect(html).toContain('|E| |E|E| | |E|')
    expect(html).not.toContain('```')
    expect(html).not.toContain('![Seven')
  })

  it('detects markdown payloads', () => {
    expect(looksLikeMarkdown('## Example\n\nHello')).toBe(true)
    expect(looksLikeMarkdown('Just a sentence.')).toBe(false)
  })

  it('renders labeled callout blockquotes', () => {
    const html = markdownToStudyHtml('> **Ловушка:** add() ещё не INSERT\n\n> plain quote')
    expect(html).toContain('study-callout-trap')
    expect(html).toContain('Ловушка')
    expect(html).toContain('add() ещё не INSERT')
    expect(html).toContain('<blockquote>')
    expect(html).toContain('plain quote')
  })

  it('does not treat Python generics as HTML', () => {
    expect(looksLikeHtml('return user.<id>')).toBe(false)
    expect(looksLikeHtml('<p>Hello</p>')).toBe(true)
  })

  it('renders GFM pipe tables as HTML tables', () => {
    const md = [
      '## Когда использовать Redis?',
      '',
      '| Задача | Redis подходит? | Почему? |',
      '|-----------------------------------|------------------|----------------------------------|',
      '| Хранение сессий пользователей | Да | Быстрый доступ. |',
      '| Обработка заказов | Нет | Нужны транзакции. |',
      '',
      'Пример: кэширование.',
    ].join('\n')
    const html = markdownToStudyHtml(md)
    expect(html).toContain('<table>')
    expect(html).toContain('<th>Задача</th>')
    expect(html).toContain('<td>Да</td>')
    expect(html).toContain('Обработка заказов')
    expect(html).not.toContain('| Redis подходит?')
    expect(html).toContain('Пример: кэширование.')
  })

  it('parses indented fences from LLM theory blocks', () => {
    const md = [
      'Фундамент.',
      '',
      '   ```python',
      '   from django.db import models',
      '',
      '   class Article(models.Model):',
      '       title = models.CharField(max_length=200)',
      '   ```',
      '',
      'Здесь `Article` — модель.',
    ].join('\n')
    const html = markdownToStudyHtml(md)
    expect(html).toContain('<pre><code class="language-python">')
    expect(html).toContain('class Article(models.Model):')
    expect(html).not.toContain('```python')
    expect(html).toContain('<code>Article</code>')
  })

  it('repairs double-backtick fences from LLM corruption', () => {
    const md = [
      'Шаблон:',
      '',
      '``html',
      '<h1>Статьи</h1>',
      '{% for post in posts %}',
      '<li>{{ post.title }}</li>',
      '{% endfor %}',
      '``',
      '',
      'Готово.',
    ].join('\n')
    const html = markdownToStudyHtml(md)
    expect(html).toContain('<pre><code class="language-html">')
    expect(html).toContain('&lt;h1&gt;Статьи&lt;/h1&gt;')
    expect(html).toContain('Готово.')
    expect(html).not.toContain('``html')
  })

  it('keeps markdown with generics and fences out of HTML mode', () => {
    const md = [
      '# Частые ошибки',
      '',
      'После commit объект имеет `<id>`.',
      '',
      '```python',
      'print(user.id)  # <id> ready',
      '```',
    ].join('\n')
    expect(looksLikeHtml(md)).toBe(false)
    const html = studyBodyToHtml(md)
    expect(html).toContain('<h2')
    expect(html).toContain('<pre><code')
    expect(html).not.toContain('```')
    expect(html).not.toContain('# Частые')
  })
})

describe('plainToStudyHtml', () => {
  it('renders spaced pseudo-tables as HTML tables', () => {
    const html = plainToStudyHtml('OrderID  Name\n1  Anna\n2  Bob')
    expect(html).toContain('<table>')
    expect(html).toContain('<th>OrderID</th>')
    expect(html).toContain('<td>Anna</td>')
  })

  it('keeps readable paragraph breaks for long plain text', () => {
    const html = plainToStudyHtml('First sentence. Second sentence. Third sentence goes here as well.')
    expect(html).toContain('<p>')
  })

  it('turns bullet lines into lists', () => {
    const html = plainToStudyHtml('- one\n- two\n- three')
    expect(html).toContain('<ul>')
    expect(html).toContain('<li>one</li>')
    expect(html).toContain('<li>three</li>')
  })
})

describe('asciiTableToHtml', () => {
  it('rejects non-tabular blocks', () => {
    expect(asciiTableToHtml('Just a sentence with spaces.')).toBeNull()
  })
})
