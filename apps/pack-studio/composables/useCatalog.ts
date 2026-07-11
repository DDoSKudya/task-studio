export type PackUploadResponse = {
  pack_id: string
  version_id: string
  slug: string
  title: string
  version: string
}

export function useCatalog() {
  const { request } = useApi()

  async function uploadPack(file: File) {
    const form = new FormData()
    form.append('pack', file)
    return request<PackUploadResponse>('/v1/catalog/packs/upload', {
      method: 'POST',
      body: form,
    })
  }

  return { uploadPack }
}
