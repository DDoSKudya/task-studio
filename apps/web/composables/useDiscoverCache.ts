import type { DiscoverResponse } from '~/composables/useSearch'

type DiscoverCacheEntry = {
  query: string
  payload: DiscoverResponse
  fetchedAt: number
}

const TTL_MS = 3 * 60_000

export function useDiscoverCache() {
  const entry = useState<DiscoverCacheEntry | null>('discover-catalog-cache', () => null)

  function read(query: string): DiscoverResponse | null {
    const current = entry.value
    if (!current) {
      return null
    }
    if (current.query !== query.trim()) {
      return null
    }
    if (Date.now() - current.fetchedAt > TTL_MS) {
      return null
    }
    return current.payload
  }

  function write(query: string, payload: DiscoverResponse) {

    if (!payload.courses?.length && !(payload.platforms ?? []).some((item) => item.status === 'ready')) {
      entry.value = null
      return
    }
    entry.value = {
      query: query.trim(),
      payload,
      fetchedAt: Date.now(),
    }
  }

  function clear() {
    entry.value = null
  }

  return { read, write, clear, entry }
}
