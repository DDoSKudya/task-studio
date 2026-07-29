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
    import_without_auth?: boolean
    content_types: string[]
  }
  auth: {
    type: string | null
    settings_fields: string[]
    optional_settings_fields?: string[]
  } | null
}

export type ExternalCourseSummary = {
  platform: string
  external_id: string
  title: string
  description: string
  author?: string
  language?: string
  tags?: string[]
}

export type PlatformCatalogStatus =
  | 'ready'
  | 'needs_auth'
  | 'error'
  | 'empty'
  | 'upload_only'
  | 'unavailable'

export type PlatformCatalogBlock = {
  platform_id: string
  display_name: string
  requires_auth: boolean
  supports_catalog: boolean
  status: PlatformCatalogStatus
  message: string | null
  course_count: number
  courses: ExternalCourseSummary[]
}

export type DiscoverResponse = {
  platforms: PlatformCatalogBlock[]
  courses: ExternalCourseSummary[]
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
