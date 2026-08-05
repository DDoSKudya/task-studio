import { describe, expect, it } from 'vitest'
import {
  localizeCourseError,
  localizeCourseProgressMessage,
  localizeCourseWarning,
} from './localizeProgress'

const ru: Record<string, string> = {
  'courseBuild.messages.analyzeRunning': 'Собираем единую прогрессивную программу из всех источников',
  'courseBuild.messages.analyzeOutlineReady': 'Каркас программы готов — уточняем главы',
  'courseBuild.messages.analyzeEnriching': 'Уточняем главу: {title}',
  'courseBuild.messages.theoryExpanding': 'Раскрываем главу: {title}',
  'courseBuild.messages.polishRunning': 'Сводим теорию к единому голосу книги',
  'courseBuild.messages.polishDone': 'Редакция применена к главам: {count}',
  'courseBuild.messages.polishPartial': 'Редакция частичная: готово {count}, пропущено {skipped}',
  'courseBuild.messages.generationCompletePartial': 'Курс собран, но редактура части глав не завершена',
  'courseBuild.messages.quizzesDesigning': 'Готовим {count} проверочных квизов',
  'courseBuild.warningsMap.continuedDespiteDeviations': 'Продолжили несмотря на расхождения между статьями',
  'courseBuild.warningsMap.theorySlidesShort':
    'По источникам получилось {got} из {wanted} запрошенных слайдов теории',
  'courseBuild.warningsMap.bookPolishSkipped': 'Редактуру пропустили: {reason}',
  'courseBuild.warningsMap.bookPolishSkippedCapacity': 'Редактуру главы «{id}» пропустили: лимит модели (попробуйте позже)',
  'courseBuild.warningsMap.bookPolishSkippedFor': 'Редактуру главы «{id}» пропустили: {reason}',
  'courseBuild.errors.noProvider': 'Не настроен ИИ-провайдер помощника',
  'courseBuild.errors.network':
    'Связь оборвалась на долгой генерации. Нажмите «Возобновить» — уже сделанное сохранится.',
}

function t(key: string, params?: Record<string, unknown>) {
  let out = ru[key] ?? key
  if (params) {
    for (const [name, value] of Object.entries(params)) {
      out = out.replace(`{${name}}`, String(value))
    }
  }
  return out
}

describe('localizeCourseProgressMessage', () => {
  it('translates by message_key', () => {
    expect(
      localizeCourseProgressMessage(
        { message: 'Synthesizing one progressive syllabus from all sources', message_key: 'analyzeRunning' },
        t,
      ),
    ).toBe('Собираем единую прогрессивную программу из всех источников')
  })

  it('translates analyze enrich progress', () => {
    expect(
      localizeCourseProgressMessage(
        {
          message: 'Enriching chapter: ORM',
          message_key: 'analyzeEnriching',
          message_params: { title: 'ORM', index: 2, total: 5 },
        },
        t,
      ),
    ).toBe('Уточняем главу: ORM')
    expect(
      localizeCourseProgressMessage(
        { message: 'Syllabus outline ready — enriching chapters' },
        t,
      ),
    ).toBe('Каркас программы готов — уточняем главы')
  })

  it('falls back to English message patterns', () => {
    expect(
      localizeCourseProgressMessage(
        { message: 'Synthesizing one progressive syllabus from all sources' },
        t,
      ),
    ).toBe('Собираем единую прогрессивную программу из всех источников')
  })

  it('interpolates params from message_key', () => {
    expect(
      localizeCourseProgressMessage(
        { message_key: 'theoryExpanding', message_params: { title: 'ORM' } },
        t,
      ),
    ).toBe('Раскрываем главу: ORM')
  })

  it('parses count from legacy quiz message', () => {
    expect(
      localizeCourseProgressMessage({ message: 'Designing 6 knowledge-check quizzes' }, t),
    ).toBe('Готовим 6 проверочных квизов')
  })

  it('translates polish messages', () => {
    expect(
      localizeCourseProgressMessage({ message_key: 'polishRunning' }, t),
    ).toBe('Сводим теорию к единому голосу книги')
    expect(
      localizeCourseProgressMessage(
        { message: 'Book polish applied to 2 chapter(s)', message_key: 'polishDone', message_params: { count: 2 } },
        t,
      ),
    ).toBe('Редакция применена к главам: 2')
  })

  it('translates partial polish legacy message before polishDone', () => {
    expect(
      localizeCourseProgressMessage(
        { message: 'Book polish applied to 1 chapter(s); skipped 2' },
        t,
      ),
    ).toBe('Редакция частичная: готово 1, пропущено 2')
  })
})

describe('localizeCourseWarning', () => {
  it('translates known warnings', () => {
    expect(localizeCourseWarning('continued despite article deviations', t)).toBe(
      'Продолжили несмотря на расхождения между статьями',
    )
  })

  it('translates theory shortfall warnings', () => {
    expect(
      localizeCourseWarning('sources supported 4 of 12 requested theory slides', t),
    ).toBe('По источникам получилось 4 из 12 запрошенных слайдов теории')
  })

  it('translates book polish skip warnings', () => {
    expect(localizeCourseWarning('book polish skipped: invalid JSON', t)).toBe(
      'Редактуру пропустили: invalid JSON',
    )
    expect(localizeCourseWarning('book polish skipped capacity: ch-1', t)).toBe(
      'Редактуру главы «ch-1» пропустили: лимит модели (попробуйте позже)',
    )
    expect(localizeCourseWarning('book polish skipped for ch-2: timeout', t)).toBe(
      'Редактуру главы «ch-2» пропустили: timeout',
    )
  })
})

describe('localizeCourseError', () => {
  it('translates known backend errors', () => {
    expect(localizeCourseError('no tutor provider configured', t)).toBe(
      'Не настроен ИИ-провайдер помощника',
    )
  })

  it('translates network drops during long builds', () => {
    expect(localizeCourseError('NETWORK ERROR', t)).toMatch(/Возобновить|связ/i)
    expect(localizeCourseError('Failed to fetch', t)).toMatch(/Возобновить|связ/i)
  })
})
