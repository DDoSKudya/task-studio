export type PackIntegrityStatus = 'ok' | 'broken'

export type PackSummary = {
  id: string
  slug: string
  title: string
  source: string | null
  external_id: string | null
  version: string
  version_id: string
  installed_at: string
  integrity: PackIntegrityStatus
  integrity_issues: string[]
  has_theory: boolean
  has_video: boolean
  has_quiz: boolean
  has_practice: boolean
}

export type PackVersionInfo = {
  id: string
  version: string
  created_at: string
  active: boolean
}

export type PackDetail = {
  id: string
  slug: string
  title: string
  source: string
  external_id: string | null
  schema_version: number
  active_version: PackVersionInfo
  versions: PackVersionInfo[]
  manifest: Record<string, unknown>
  integrity: PackIntegrityStatus
  integrity_issues: string[]
}

export type PackUploadResponse = {
  pack_id: string
  version_id: string
  slug: string
  title: string
  version: string
}
