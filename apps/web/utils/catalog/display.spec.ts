import { describe, expect, it } from 'vitest'
import {
  cardInitial,
  catalogQueryForTab,
  catalogTabFromQuery,
  chapterTitleFromOutline,
  courseCardMeta,
  courseKey,
  inferDisplayTags,
  inferTagsFromText,
  libraryCardSubtitleText,
  packPrimaryHref,
  packContentTags,
  platformHintText,
  settingsLinkForPlatform,
  uniqueTags,
} from './display'

describe('catalog/display', () => {
  it('builds course keys', () => {
    expect(courseKey('stepik', '42')).toBe('stepik:42')
  })

  it('maps discover query tabs', () => {
    expect(catalogTabFromQuery('discover')).toBe('external')
    expect(catalogTabFromQuery('download')).toBe('external')
    expect(catalogTabFromQuery('library')).toBe('library')
    expect(catalogTabFromQuery(undefined)).toBe('library')
  })

  it('dedupes tags and drops language echo', () => {
    expect(uniqueTags(['Python', 'python', 'Docker', ''], 'python')).toEqual(['Docker'])
  })

  it('infers tags from title/description', () => {
    expect(inferTagsFromText('Learn python and Docker')).toEqual(['Python', 'Docker'])
  })

  it('merges course tags with inferred ones', () => {
    expect(
      inferDisplayTags({
        platform: 'stepik',
        external_id: '1',
        title: 'Intro to python',
        description: '',
        language: 'en',
        tags: ['Beginner'],
      }),
    ).toEqual(['Beginner', 'Python'])
  })

  it('formats card meta and initials', () => {
    expect(
      courseCardMeta({
        author: 'Ada',
        tags: ['Python', 'Docker'],
        description: 'long',
        platform: 'stepik',
        externalId: '9',
      }),
    ).toBe('Ada · Python · Docker')
    expect(cardInitial('c++ primer')).toBe('C++')
    expect(cardInitial('')).toBe('?')
  })

  it('builds settings deep link', () => {
    expect(settingsLinkForPlatform('stepik')).toBe('/settings?section=integration:stepik')
  })

  it('builds tab query and library card copy', () => {
    expect(catalogQueryForTab({ q: 'x', tab: 'discover' }, 'library')).toEqual({ q: 'x' })
    expect(catalogQueryForTab({ q: 'x' }, 'external')).toEqual({ q: 'x', tab: 'discover' })
    expect(
      chapterTitleFromOutline([{ topic_id: 't1', title: ' Intro ' }], 't1', 'empty'),
    ).toBe('Intro')
    expect(packPrimaryHref('p1', { sessionId: 's1', status: 'active' })).toBe('/sessions/s1')
    expect(
      libraryCardSubtitleText({
        title: 'Course',
        slug: 'course',
        version: 2,
        chapter: 'Lesson 1',
        progress: 10,
        emptyLabel: 'none',
      }),
    ).toBe('Lesson 1')
    expect(platformHintText(null, 'fallback')).toBe('fallback')
  })

  it('builds pack content tags from manifest flags', () => {
    expect(
      packContentTags({ has_theory: true, has_video: true, has_quiz: false, has_practice: true }),
    ).toEqual(['theory', 'video', 'practice'])
    expect(packContentTags({ has_video: true })).toEqual(['video'])
    expect(packContentTags({})).toEqual([])
  })
})
