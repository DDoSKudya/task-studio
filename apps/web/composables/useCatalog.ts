export type PackSummary = {
  id: string
  slug: string
  title: string
  source: string
  version: string
  version_id: string
  installed_at: string
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
  schema_version: number
  active_version: PackVersionInfo
  versions: PackVersionInfo[]
  manifest: Record<string, unknown>
}

export type PackUploadResponse = {
  pack_id: string
  version_id: string
  slug: string
  title: string
  version: string
}

export function useCatalog() {
  const { request } = useApi()

  async function listPacks() {
    return request<PackSummary[]>('/v1/catalog/packs')
  }

  async function getPack(packId: string) {
    return request<PackDetail>(`/v1/catalog/packs/${packId}`)
  }

  async function uploadPack(file: File) {
    const form = new FormData()
    form.append('pack', file)
    return request<PackUploadResponse>('/v1/catalog/packs/upload', {
      method: 'POST',
      body: form,
    })
  }

  return {
    listPacks,
    getPack,
    uploadPack,
  }
}
