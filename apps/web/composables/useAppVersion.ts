export type AppVersionInfo = {
  version: string
  build: number
  channel: string
  shortVersion: string
}

function shortFromSemver(version: string): string {
  const core = version.split('-')[0]?.trim() || version
  return core.startsWith('v') ? core.slice(1) : core
}

export function useAppVersion(): AppVersionInfo {
  const config = useRuntimeConfig()
  const version = String(config.public.appVersion || '0.0.0-develop')
  const buildRaw = Number(config.public.appBuild)
  const build = Number.isFinite(buildRaw) && buildRaw > 0 ? buildRaw : 0
  const channel = String(config.public.appChannel || 'develop')
  return {
    version,
    build,
    channel,
    shortVersion: shortFromSemver(version),
  }
}
