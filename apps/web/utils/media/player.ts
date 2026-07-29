export function mediaProgressPercent(current: number, duration: number): number {
  return duration > 0 ? (current / duration) * 100 : 0
}

export function formatMediaTime(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) {
    return '0:00'
  }
  const total = Math.floor(seconds)
  const h = Math.floor(total / 3600)
  const m = Math.floor((total % 3600) / 60)
  const s = total % 60
  if (h > 0) {
    return `${h}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`
  }
  return `${m}:${String(s).padStart(2, '0')}`
}

export function resolvePlaybackSrc(src: string, baseHref: string | null): string {
  if (!baseHref || !src) {
    return src
  }
  try {
    return new URL(src, baseHref).href
  } catch {
    return src
  }
}

export function seekRatioFromClientX(
  clientX: number,
  left: number,
  width: number,
): number {
  if (width <= 0) {
    return 0
  }
  return Math.min(1, Math.max(0, (clientX - left) / width))
}
