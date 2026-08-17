import { describe, expect, it } from 'vitest'
import {
  localizeCourseError,
  localizeCourseProgressMessage,
  localizeCourseWarning,
} from './localizeProgress'

const ru: Record<string, string> = {
  'courseBuild.messages.analyzePreparing': 'Готовим модель для сборки курса',
  'courseBuild.messages.analyzeCompiling': 'Собираем программу из источников',
  'courseBuild.messages.analyzeRunning': 'Собираем единую прогрессивную программу из всех источников',
  'courseBuild.messages.topicBundleRunning': 'Собираем тему: {title}',
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
  'courseBuild.warningsMap.theoryOutlineThinCorpus':
    'Корпус слишком тонкий для {wanted} слайдов теории; оставили {got}',
  'courseBuild.warningsMap.theoryOutlineShortAfterExpand':
    'После расширения outline: {got} из {wanted} слайдов теории',
  'courseBuild.warningsMap.bookPolishSkipped': 'Редактуру пропустили: {reason}',
  'courseBuild.warningsMap.bookPolishSkippedCapacity': 'Редактуру главы «{id}» пропустили: лимит модели (попробуйте позже)',
  'courseBuild.warningsMap.bookPolishSkippedFor': 'Редактуру главы «{id}» пропустили: {reason}',
  'courseBuild.errors.noProvider': 'Не настроен ИИ-провайдер помощника',
  'courseBuild.errors.localTheoryFailed':
    'Не удалось написать теорию главы: модель не покрыла источник. Попробуйте снова.',
  'courseBuild.errors.localPracticeFailed':
    'Не удалось составить практику по главе «{title}». Попробуйте снова.',
  'courseBuild.errors.noTeachableSyllabus':
    'В источниках нет глав с текстом, который можно преподавать. Добавьте более содержательные статьи.',
  'courseBuild.warningsMap.localUniqueTopics':
    'По источникам получилось {got} плотных глав (запрашивали {wanted}) — не раздували оглавление',
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
    expect(
      localizeCourseProgressMessage({ message_key: 'analyzePreparing' }, t),
    ).toBe('Готовим модель для сборки курса')
    expect(
      localizeCourseProgressMessage(
        { message_key: 'topicBundleRunning', message_params: { title: 'Routers' } },
        t,
      ),
    ).toBe('Собираем тему: Routers')
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
    expect(
      localizeCourseWarning('corpus too thin for 8 theory slides; kept 5', t),
    ).toBe('Корпус слишком тонкий для 8 слайдов теории; оставили 5')
    expect(
      localizeCourseWarning('outline short after expand: 5 of 8 theory slides', t),
    ).toBe('После расширения outline: 5 из 8 слайдов теории')
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

  it('translates local compiler unique-topic notice', () => {
    expect(
      localizeCourseWarning('local compiler: 5 unique topics from sources (requested 8)', t),
    ).toBe('По источникам получилось 5 плотных глав (запрашивали 8) — не раздували оглавление')
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

  it('translates local ollama course failures', () => {
    expect(
      localizeCourseError('local theory failed for «Routers»: window 1/2 LLM error', t),
    ).toMatch(/теорию главы/i)
    expect(
      localizeCourseError('local syllabus has no teachable chapter excerpts', t),
    ).toMatch(/преподавать/i)
    expect(
      localizeCourseError(
        'local practice failed for «Почему FastAPI»: no usable tasks after retries',
        t,
      ),
    ).toMatch(/практику по главе «Почему FastAPI»/i)
  })
})
