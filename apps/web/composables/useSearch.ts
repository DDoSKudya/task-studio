export type SearchHit = {
  id: string
  kind: 'installed' | 'uploaded' | 'external'
  title: string
  description: string
  source: string
  platform: string | null
  external_id: string | null
  pack_id: string | null
  pack_version_id: string | null
  score: number
}

export type SearchResponse = {
  query: string
  hits: SearchHit[]
  total: number
}

export type AdapterInfo = {
  id: string
  version: string
  display_name: string
  capabilities: {
    import_course: boolean
    search_catalog: boolean
    requires_auth: boolean
    content_types: string[]
  }
}

export type ExternalCourseSummary = {
  platform: string
  external_id: string
  title: string
  description: string
}

export type ImportJobResponse = {
  id: string
  platform_id: string
  external_course_id: string
  status: string
  pack_version_id: string | null
  error: string | null
  created_at: string
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

  async function startImport(platform: string, courseId: string) {
    return request<ImportJobResponse>(`/v1/integrations/${platform}/import`, {
      method: 'POST',
      body: { course_id: courseId },
    })
  }

  async function importFromSearch(platform: string, externalId: string) {
    return request<ImportJobResponse>('/v1/search/import', {
      method: 'POST',
      body: { platform, external_id: externalId },
    })
  }

  async function getImportJob(jobId: string) {
    return request<ImportJobResponse>(`/v1/integrations/jobs/${jobId}`)
  }

  return {
    search,
    listIntegrations,
    listPlatformCatalog,
    startImport,
    importFromSearch,
    getImportJob,
  }
}
