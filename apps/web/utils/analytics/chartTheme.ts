

export const ANALYTICS_VIOLET = '#b366ff'

export const ANALYTICS_SUCCESS = '#b366ff'
export const ANALYTICS_MUTED = 'rgba(160, 160, 168, 0.85)'
export const ANALYTICS_GRID = 'rgba(255, 255, 255, 0.08)'
export const ANALYTICS_AXIS = 'rgba(160, 160, 168, 0.55)'
export const ANALYTICS_LINE = 'rgba(242, 242, 247, 0.88)'

export function analyticsTooltipBase() {
  return {
    backgroundColor: 'rgba(10, 10, 16, 0.94)',
    borderColor: 'rgba(255, 255, 255, 0.22)',
    borderWidth: 1,
    textStyle: {
      color: '#f2f2f7',
      fontFamily: 'JetBrains Mono Variable, JetBrains Mono, monospace',
      fontSize: 11,
    },
    extraCssText: 'border-radius:0;box-shadow:none;letter-spacing:0.06em;text-transform:uppercase;',
  }
}

export function analyticsAxisLabel() {
  return {
    color: ANALYTICS_AXIS,
    fontFamily: 'JetBrains Mono Variable, JetBrains Mono, monospace',
    fontSize: 10,
    letterSpacing: 1,
  }
}

export function analyticsLegend() {
  return {
    top: 0,
    right: 0,
    textStyle: {
      color: ANALYTICS_MUTED,
      fontFamily: 'JetBrains Mono Variable, JetBrains Mono, monospace',
      fontSize: 10,
      letterSpacing: 1,
    },
    itemWidth: 10,
    itemHeight: 6,
    icon: 'rect',
  }
}
