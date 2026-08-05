import type { MaybeRefOrGetter } from 'vue'
import { toValue } from 'vue'

export function useAppPageTitle(title: MaybeRefOrGetter<string | undefined | null>) {
  const { t } = useI18n()

  useHead({
    title: computed(() => {
      const raw = toValue(title)?.trim()
      return raw || t('app.title')
    }),
  })
}
