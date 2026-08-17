import type { PackDetail, PackSummary, PackUploadResponse } from '~/utils/catalog'

export type {
  PackDetail,
  PackIntegrityStatus,
  PackSummary,
  PackUploadResponse,
  PackVersionInfo,
} from '~/utils/catalog'

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

  async function deletePack(packId: string) {
    await request(`/v1/catalog/packs/${packId}`, {
      method: 'DELETE',
    })
  }

  return {
    listPacks,
    getPack,
    uploadPack,
    deletePack,
  }
}
