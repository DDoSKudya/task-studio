import type {
  AdapterInfo,
  DiscoverResponse,
  EnrollCourseResponse,
  ExternalCourseSummary,
  ImportJobResponse,
  PlatformCatalogBlock,
  SearchResponse,
} from '~/utils/search'

export type {
  AdapterInfo,
  DiscoverResponse,
  EnrollCourseResponse,
  ExternalCourseSummary,
  ImportJobResponse,
  PlatformCatalogBlock,
  PlatformCatalogStatus,
  SearchHit,
  SearchResponse,
} from '~/utils/search'

function normalizeDiscoverResponse(
  raw: DiscoverResponse | ExternalCourseSummary[] | null | undefined,
): DiscoverResponse {
  if (Array.isArray(raw)) {
    const courses = raw.filter(
      (item): item is ExternalCourseSummary =>
        Boolean(item && typeof item === 'object' && 'platform' in item && 'external_id' in item),
    )
    const byPlatform = new Map<string, ExternalCourseSummary[]>()
    for (const course of courses) {
      const bucket = byPlatform.get(course.platform) ?? []
      bucket.push(course)
      byPlatform.set(course.platform, bucket)
    }
    const platforms: PlatformCatalogBlock[] = Array.from(byPlatform.entries()).map(
      ([platformId, platformCourses]) => ({
        platform_id: platformId,
        display_name: platformId,
        requires_auth: false,
        supports_catalog: true,
        status: platformCourses.length ? 'ready' : 'empty',
        message: null,
        course_count: platformCourses.length,
        courses: platformCourses,
      }),
    )
    return { platforms, courses }
  }
  if (raw && typeof raw === 'object' && Array.isArray(raw.platforms) && Array.isArray(raw.courses)) {
    return raw
  }
  return { platforms: [], courses: [] }
}

export function useSearch() {
  const { request } = useApi()

  async function search(query: string, type?: 'course' | 'step') {
    const params = new URLSearchParams({ q: query })
    if (type) {
      params.set('type', type)
    }
    return request<SearchResponse>(`/v1/search?${params.toString()}`)
  }

  async function listIntegrations() {
    return request<AdapterInfo[]>('/v1/integrations')
  }

  async function listPlatformCatalog(platform: string) {
    return request<ExternalCourseSummary[]>(`/v1/integrations/${platform}/catalog`)
  }

  async function discoverCourses(query?: string) {
    const params = new URLSearchParams()
    if (query?.trim()) {
      params.set('q', query.trim())
    }
    const suffix = params.size ? `?${params.toString()}` : ''
    const raw = await request<DiscoverResponse | ExternalCourseSummary[]>(
      `/v1/integrations/discover${suffix}`,
    )
    return normalizeDiscoverResponse(raw)
  }

  async function startImport(platform: string, courseId: string, options: { force?: boolean } = {}) {
    return request<ImportJobResponse>(`/v1/integrations/${platform}/import`, {
      method: 'POST',
      body: { course_id: courseId, force: Boolean(options.force) },
    })
  }

  async function importFromSearch(
    platform: string,
    externalId: string,
    options: { force?: boolean } = {},
  ) {
    return request<ImportJobResponse>('/v1/search/import', {
      method: 'POST',
      body: {
        platform,
        external_id: externalId,
        force: Boolean(options.force),
      },
    })
  }

  async function enrollCourse(platform: string, courseId: string) {
    return request<EnrollCourseResponse>(`/v1/integrations/${platform}/enroll`, {
      method: 'POST',
      body: { course_id: courseId },
    })
  }

  async function getImportJob(jobId: string) {
    return request<ImportJobResponse>(`/v1/integrations/jobs/${jobId}`)
  }

  return {
    search,
    listIntegrations,
    listPlatformCatalog,
    discoverCourses,
    startImport,
    importFromSearch,
    enrollCourse,
    getImportJob,
  }
}
