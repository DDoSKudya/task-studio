import type { AdapterInfo } from '~/composables/useSearch'
import { extractErrorMessage } from '~/utils/api'
import {
  CURSOR_DEFAULT_MODEL,
  CURSOR_PROXY_URL,
  EDITOR_RUNTIMES,
  OPENAI_DEFAULT_MODEL,
  OPENAI_PROVIDER_URL,
  authTypeLabel as authTypeLabelCopy,
  clonePlain,
  credentialValuePresent,
  defaultLanguageMap,
  fieldHint as fieldHintCopy,
  fieldLabel as fieldLabelCopy,
  fieldPlaceholder as fieldPlaceholderCopy,
  fieldsFor as fieldsForCopy,
  findCatalogEntry,
  inferProviderMode,
  integrationDraftDirty,
  integrationDraftFromStored,
  isModelInList,
  isOptionalField as isOptionalFieldCopy,
  isSecretCredentialField,
  languagesMapDirty,
  normalizePlatformCredentials,
  parseEditorSettings,
  platformCapabilities as platformCapabilitiesCopy,
  platformHelp as platformHelpCopy,
  requiredFieldsFilled,
  requiredFieldsFor as requiredFieldsForCopy,
  selectProjectModels,
  settingsFormDirty,
  tutorFormDirty,
  buildProviderProfilesPayload,
  emptyProviderDraft,
  emptyProviderProfiles,
  providerProfilesFromSettings,
  snapshotActiveProvider,
  type TutorProviderMode,
  type TutorProviderProfilesState,
} from '~/utils/settings'

type TutorSettingsForm = {
  providerUrl: string
  apiKey: string
  dailyLimit: number
  model: string
}

export function useSettingsPage() {
  const { t } = useI18n()
  const route = useRoute()
  const { settings, fetchMe, patchSettings } = useAuth()
  const { listIntegrations } = useSearch()
  const { getLlmStatus, testLlm } = useTutor()

  const pending = ref(true)
  const saving = ref(false)
  const adapters = ref<AdapterInfo[]>([])
  const toasts = useToasts()
  const openSection = ref<string | null>(null)
  const selectedPlatform = ref<string | null>(null)

  const autocomplete = ref(true)
  const mode = ref<'full' | 'syntax_only'>('full')
  const languageEnabled = ref<Record<string, boolean>>(defaultLanguageMap())
  const tutor = ref<TutorSettingsForm>({
    providerUrl: '',
    apiKey: '',
    dailyLimit: 0,
    model: '',
  })
  const tutorProviderMode = ref<TutorProviderMode>('ollama')
  const providerProfiles = ref<TutorProviderProfilesState>(emptyProviderProfiles())
  const hasStoredApiKey = ref(false)
  const llmStatus = ref<Awaited<ReturnType<typeof getLlmStatus>> | null>(null)
  const llmStatusPending = ref(false)
  const modelsLoadPending = ref(false)
  const integrationDrafts = ref<Record<string, Record<string, string>>>({})

  const baseline = ref({
    autocomplete: true,
    mode: 'full' as 'full' | 'syntax_only',
    languages: defaultLanguageMap(),
    tutor: {
      providerUrl: '',
      providerMode: 'ollama' as TutorProviderMode,
      dailyLimit: 0,
      model: '',
    },
    integrations: {} as Record<string, Record<string, string>>,
  })

  const integrationSettings = computed(() => {
    const blob = settings.value.integrations
    if (!blob || typeof blob !== 'object' || Array.isArray(blob)) {
      return {} as Record<string, Record<string, string>>
    }
    const normalized: Record<string, Record<string, string>> = {}
    for (const [platformId, values] of Object.entries(blob as Record<string, unknown>)) {
      normalized[platformId] = normalizePlatformCredentials(values)
    }
    return normalized
  })

  const authAdapters = computed(() =>
    adapters.value.filter((adapter) => adapter.capabilities.requires_auth),
  )

  const publicAdapters = computed(() =>
    adapters.value.filter((adapter) => !adapter.capabilities.requires_auth),
  )

  const connectedAuthCount = computed(() =>
    authAdapters.value.filter((adapter) => isConnected(adapter.id)).length,
  )

  const editorSummary = computed(() =>
    mode.value === 'full' ? t('settings.modeFull') : t('settings.modeSyntaxOnly'),
  )

  const tutorSummary = computed(() =>
    t(`settings.tutor.providers.${tutorProviderMode.value}`),
  )

  const activeProviderLabel = computed(() => {
    if (tutorProviderMode.value === 'ollama') {
      return t('settings.tutor.providers.ollamaEndpoint')
    }
    if (tutorProviderMode.value === 'cursor') {
      return t('settings.tutor.providers.cursorEndpoint')
    }
    return (tutor.value.providerUrl ?? '').trim() || t('settings.tutor.providers.notSet')
  })

  function sectionIdForIntegration(platformId: string) {
    return `integration:${platformId}`
  }

  function isSectionOpen(sectionId: string) {
    return openSection.value === sectionId
  }

  function toggleSection(sectionId: string) {
    if (openSection.value === sectionId) {
      openSection.value = null
      if (sectionId.startsWith('integration:')) {
        selectedPlatform.value = null
      }
      return
    }
    openSection.value = sectionId
    if (sectionId.startsWith('integration:')) {
      selectedPlatform.value = sectionId.slice('integration:'.length)
    } else {
      selectedPlatform.value = null
    }
    if (sectionId === 'tutor') {
      void loadAvailableModels({ quiet: true })
    }
  }

  function platformStatus(adapter: AdapterInfo): 'ok' | 'idle' | 'pending' {
    if (adapter.capabilities.import_without_auth) {
      if (hasUnsavedCredentials(adapter.id)) {
        return 'pending'
      }
      return 'ok'
    }
    if (!adapter.capabilities.requires_auth) {
      return 'ok'
    }
    if (isConnected(adapter.id)) {
      return 'ok'
    }
    if (hasUnsavedCredentials(adapter.id)) {
      return 'pending'
    }
    return 'idle'
  }

  function platformStatusClasses(adapter: AdapterInfo) {
    const status = platformStatus(adapter)
    return {
      status,
      icon: {
        'settings-service-icon-ok': status === 'ok',
        'settings-service-icon-idle': status === 'idle',
        'settings-service-icon-pending': status === 'pending',
      },
      badge: {
        'settings-service-badge-ok': status === 'ok',
        'settings-service-badge-idle': status === 'idle',
        'settings-service-badge-pending': status === 'pending',
      },
    }
  }

  function selectPlatform(adapter: AdapterInfo) {
    selectedPlatform.value = adapter.id
    openSection.value = sectionIdForIntegration(adapter.id)
  }

  function loadProviderDraft(mode: TutorProviderMode) {
    const draft = providerProfiles.value[mode] ?? emptyProviderDraft(mode)

    tutor.value.providerUrl = mode === 'cursor' ? CURSOR_PROXY_URL : (draft.providerUrl ?? '')
    tutor.value.model = draft.model ?? ''

    tutor.value.apiKey = draft.apiKey ?? ''
    hasStoredApiKey.value = draft.hasStoredApiKey || Boolean(tutor.value.apiKey.trim())
  }

  function persistActiveProviderDraft() {
    const typedKey = (tutor.value.apiKey ?? '').trim()
    const providerUrl =
      tutorProviderMode.value === 'cursor'
        ? CURSOR_PROXY_URL
        : (tutor.value.providerUrl ?? '')
    providerProfiles.value = snapshotActiveProvider(
      providerProfiles.value,
      tutorProviderMode.value,
      {
        providerUrl,
        model: tutor.value.model ?? '',
        apiKey: tutor.value.apiKey ?? '',
      },
      hasStoredApiKey.value || Boolean(typedKey),
    )
  }

  watch(tutorProviderMode, (next, prev) => {
    if (next === prev) {
      return
    }

    persistActiveProviderDraft()

    llmStatus.value = null
    loadProviderDraft(next)

    if (next === 'ollama') {
      tutor.value.providerUrl = ''
      void loadAvailableModels({ quiet: true })
      return
    }

    if (next === 'cursor') {
      tutor.value.providerUrl = CURSOR_PROXY_URL
      void loadAvailableModels({ quiet: true })
      return
    }

    if (
      !(tutor.value.providerUrl ?? '').trim()
      || tutor.value.providerUrl === CURSOR_PROXY_URL
    ) {
      tutor.value.providerUrl = OPENAI_PROVIDER_URL
    }
    void loadAvailableModels({ quiet: true })
  })

  const projectModelSelection = computed(() => {
    return selectProjectModels(rawLlmModels())
  })

  const availableLlmModels = computed(() => {
    const preferred = projectModelSelection.value.models
    const current = (tutor.value.model ?? '').trim()
    if (!current || isModelInList(current, preferred)) {
      return preferred
    }

    if (isModelInList(current, rawLlmModels())) {
      return [...preferred, current]
    }
    return preferred
  })

  const modelsFilteredToPreferred = computed(
    () => projectModelSelection.value.filteredToPreferred,
  )

  const selectedModelDescription = computed(() => {
    const entry = findCatalogEntry(tutor.value.model)
    if (!entry) {
      return ''
    }
    return t(`settings.tutor.modelCatalog.${entry.descKey}`)
  })

  function rawLlmModels(): string[] {
    const rows = llmStatus.value?.models
    if (!Array.isArray(rows)) {
      return []
    }
    return rows.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
  }

  function applyLoadedModels(status: Awaited<ReturnType<typeof getLlmStatus>>) {
    llmStatus.value = status
    const raw = Array.isArray(status.models)
      ? status.models.filter((item): item is string => typeof item === 'string' && item.trim().length > 0)
      : []
    if (!raw.length) {
      tutor.value.model = ''
      return
    }

    if ((tutor.value.model ?? '').trim() && !isModelInList(tutor.value.model ?? '', raw)) {
      tutor.value.model = ''
    }
  }

  async function loadAvailableModels(options?: { quiet?: boolean }) {
    const quiet = options?.quiet === true
    if (tutorProviderMode.value === 'external' && !(tutor.value.providerUrl ?? '').trim()) {
      if (!quiet) {
        toasts.error(t('settings.tutor.modelsNeedUrl'))
      }
      return false
    }

    modelsLoadPending.value = true
    try {
      if (tutorProviderMode.value === 'ollama') {
        applyLoadedModels(await getLlmStatus())
      } else {
        const providerUrl =
          tutorProviderMode.value === 'cursor'
            ? CURSOR_PROXY_URL
            : (tutor.value.providerUrl ?? '').trim() || null
        if (tutorProviderMode.value === 'cursor') {
          tutor.value.providerUrl = CURSOR_PROXY_URL
        }
        applyLoadedModels(
          await testLlm({
            provider: 'external',
            provider_url: providerUrl,
            api_key: (tutor.value.apiKey ?? '').trim() || null,
            model: (tutor.value.model ?? '').trim() || null,
          }),
        )
      }
      if (!quiet) {
        if (llmStatus.value?.ok) {
          toasts.success(
            t('settings.tutor.modelsLoaded', { count: availableLlmModels.value.length }),
          )
        } else {
          toasts.error(llmStatus.value?.detail || t('settings.tutor.statusUnavailable'))
        }
      }
      return Boolean(llmStatus.value?.ok)
    } catch {
      llmStatus.value = {
        ok: false,
        provider: tutorProviderMode.value === 'ollama' ? 'ollama' : 'external',
        detail: t('settings.tutor.statusUnavailable'),
        models: [],
        default_model: null,
      }
      if (!quiet) {
        toasts.error(t('settings.tutor.statusUnavailable'))
      }
      return false
    } finally {
      modelsLoadPending.value = false
    }
  }

  async function verifyTutorBeforeSave(): Promise<boolean> {
    if (tutorProviderMode.value === 'external' && !(tutor.value.providerUrl ?? '').trim()) {
      toasts.error(t('settings.tutor.modelsNeedUrl'))
      return false
    }

    const selectedModel = (tutor.value.model ?? '').trim()
    if (!selectedModel) {
      toasts.error(t('settings.tutor.modelRequired'))
      return false
    }

    llmStatusPending.value = true
    try {
      const ok = await loadAvailableModels({ quiet: true })
      if (!ok) {
        toasts.error(llmStatus.value?.detail || t('settings.tutor.statusUnavailable'))
        return false
      }
      const raw = rawLlmModels()
      if (!raw.length) {
        toasts.error(t('settings.tutor.modelRequired'))
        return false
      }
      if (!isModelInList(selectedModel, raw)) {
        toasts.error(t('settings.tutor.modelRequired'))
        return false
      }

      tutor.value.model = selectedModel
      return true
    } finally {
      llmStatusPending.value = false
    }
  }

  function fieldsFor(adapter: AdapterInfo) {
    return fieldsForCopy(adapter)
  }

  function requiredFieldsFor(adapter: AdapterInfo) {
    return requiredFieldsForCopy(adapter)
  }

  function isOptionalField(adapter: AdapterInfo, field: string) {
    return isOptionalFieldCopy(adapter, field)
  }

  function fieldHint(adapter: AdapterInfo, field: string) {
    if (isSecretCredentialField(field)) {
      const stored = integrationSettings.value[adapter.id]
      const draftValue = integrationDrafts.value[adapter.id]?.[field]
      if (credentialValuePresent(stored, field) && !draftValue?.trim()) {
        return t('settings.integrations.secretStored')
      }
    }
    return fieldHintCopy(t, adapter, field)
  }

  function fieldPlaceholder(adapter: AdapterInfo, field: string) {
    return fieldPlaceholderCopy(t, adapter, field)
  }

  function platformHelp(adapter: AdapterInfo) {
    return platformHelpCopy(t, adapter)
  }

  function authTypeLabel(adapter: AdapterInfo) {
    return authTypeLabelCopy(t, adapter)
  }

  function isConnected(platformId: string) {
    const adapter = adapters.value.find((item) => item.id === platformId)
    if (!adapter?.capabilities.requires_auth) {
      return true
    }
    return requiredFieldsFilled(requiredFieldsFor(adapter), integrationSettings.value[platformId])
  }

  function hasUnsavedCredentials(platformId: string) {
    if (!integrationDirty(platformId)) {
      return false
    }
    const adapter = adapters.value.find((item) => item.id === platformId)
    if (!adapter?.capabilities.requires_auth) {
      return false
    }
    return requiredFieldsFilled(requiredFieldsFor(adapter), integrationDrafts.value[platformId])
  }

  function platformStatusLabel(adapter: AdapterInfo) {
    if (!adapter.capabilities.requires_auth) {
      return t('settings.integrations.publicAccess')
    }
    if (isConnected(adapter.id)) {
      return t('settings.integrations.connected')
    }

    if (adapter.capabilities.import_without_auth) {
      return t('settings.integrations.importReady')
    }
    if (hasUnsavedCredentials(adapter.id)) {
      return t('settings.integrations.unsaved')
    }
    return t('settings.integrations.notConnected')
  }

  function integrationDirty(platformId: string) {
    return integrationDraftDirty(
      integrationDrafts.value[platformId],
      baseline.value.integrations[platformId],
    )
  }

  function draftFor(platformId: string) {
    if (!integrationDrafts.value[platformId]) {
      integrationDrafts.value[platformId] = {}
    }
    return integrationDrafts.value[platformId]
  }

  function fieldLabel(field: string) {
    return fieldLabelCopy(t, field)
  }

  function platformCapabilities(adapter: AdapterInfo) {
    return platformCapabilitiesCopy(t, adapter)
  }

  function runtimeLabel(runtime: string) {
    return t(`settings.editorRuntimes.${runtime}`, runtime)
  }

  function syncLanguageState(editorLanguages: Record<string, { enabled: boolean }>) {
    for (const runtime of EDITOR_RUNTIMES) {
      languageEnabled.value[runtime] = editorLanguages[runtime]?.enabled ?? true
    }
  }

  function languagesDirty() {
    return languagesMapDirty(languageEnabled.value, baseline.value.languages)
  }

  function tutorDirty() {
    return tutorFormDirty(tutor.value, tutorProviderMode.value, baseline.value.tutor)
  }

  const dirty = computed(() =>
    settingsFormDirty({
      tutorDirty: tutorDirty(),
      autocomplete: autocomplete.value,
      baselineAutocomplete: baseline.value.autocomplete,
      mode: mode.value,
      baselineMode: baseline.value.mode,
      languagesDirty: languagesDirty(),
      integrationDrafts: integrationDrafts.value,
      baselineIntegrations: baseline.value.integrations,
    }),
  )

  function syncFromSettings() {
    const editor = parseEditorSettings(settings.value)
    autocomplete.value = editor.autocomplete
    mode.value = editor.mode
    syncLanguageState(editor.languages)

    const tutorBlob = settings.value.tutor
    if (tutorBlob && typeof tutorBlob === 'object' && !Array.isArray(tutorBlob)) {
      const record = tutorBlob as Record<string, unknown>
      const providerUrl = typeof record.provider_url === 'string' ? record.provider_url : ''
      const dailyLimit = typeof record.daily_limit === 'number' && Number.isFinite(record.daily_limit)
        ? record.daily_limit
        : 0
      const activeProvider =
        record.active_provider === 'external'
        || record.active_provider === 'cursor'
        || record.active_provider === 'ollama'
          ? record.active_provider
          : inferProviderMode(providerUrl)
      tutorProviderMode.value = activeProvider
      providerProfiles.value = providerProfilesFromSettings(record, activeProvider)
      const activeDraft = providerProfiles.value[activeProvider]
      tutor.value = {
        providerUrl: activeDraft.providerUrl || providerUrl,
        apiKey: '',
        dailyLimit,
        model: activeDraft.model || (typeof record.model === 'string' ? record.model : ''),
      }
      hasStoredApiKey.value = activeDraft.hasStoredApiKey || Boolean(record.api_key_encrypted)
    } else {
      providerProfiles.value = emptyProviderProfiles()
      hasStoredApiKey.value = false
      tutorProviderMode.value = 'ollama'
      tutor.value = {
        providerUrl: '',
        apiKey: '',
        dailyLimit: 0,
        model: '',
      }
    }

    const integrations: Record<string, Record<string, string>> = {}
    for (const adapter of authAdapters.value) {
      const stored = normalizePlatformCredentials(integrationSettings.value[adapter.id])
      integrations[adapter.id] = integrationDraftFromStored(stored, fieldsFor(adapter))
    }
    integrationDrafts.value = integrations
    baseline.value = {
      autocomplete: autocomplete.value,
      mode: mode.value,
      languages: Object.fromEntries(
        EDITOR_RUNTIMES.map((runtime) => [runtime, languageEnabled.value[runtime]]),
      ),
      tutor: {
        providerUrl: tutor.value.providerUrl,
        providerMode: tutorProviderMode.value,
        dailyLimit: tutor.value.dailyLimit,
        model: tutor.value.model,
      },
      integrations: clonePlain(integrations),
    }
  }

  onMounted(async () => {
    try {
      await fetchMe()
    } catch {
      toasts.error(t('settings.errors.loadFailed'))
      pending.value = false
      return
    }

    try {
      adapters.value = await listIntegrations()
    } catch {
      adapters.value = []

      toasts.notice(t('settings.integrations.empty'))
    }

    try {
      syncFromSettings()
    } catch (error) {
      console.error('settings sync failed', error)

      toasts.error(t('settings.errors.loadFailed'))
      baseline.value = {
        autocomplete: autocomplete.value,
        mode: mode.value,
        languages: Object.fromEntries(
          EDITOR_RUNTIMES.map((runtime) => [runtime, languageEnabled.value[runtime]]),
        ),
        tutor: {
          providerUrl: tutor.value.providerUrl,
          providerMode: tutorProviderMode.value,
          dailyLimit: tutor.value.dailyLimit,
          model: tutor.value.model,
        },
        integrations: clonePlain(integrationDrafts.value),
      }
    } finally {
      pending.value = false
      const section = typeof route.query.section === 'string' ? route.query.section : ''
      if (section) {
        openSection.value = section
        if (section.startsWith('integration:')) {
          selectedPlatform.value = section.slice('integration:'.length)
        }
      }
      if (openSection.value === 'tutor' || tutorProviderMode.value === 'ollama') {
        void loadAvailableModels({ quiet: true })
      }
    }
  })

  function discardChanges() {
    syncFromSettings()
  }

  async function submit() {
    saving.value = true
    try {
      persistActiveProviderDraft()
      if (tutorDirty()) {
        const connectionOk = await verifyTutorBeforeSave()
        if (!connectionOk) {
          return
        }
      }

      const profilesPayload = buildProviderProfilesPayload(
        providerProfiles.value,
        tutorProviderMode.value,
        tutor.value.apiKey ?? '',
      )
      const activeProviderUrl =
        tutorProviderMode.value === 'ollama'
          ? null
          : tutorProviderMode.value === 'cursor'
            ? CURSOR_PROXY_URL
            : (tutor.value.providerUrl ?? '').trim() || null
      const tutorPayload: Record<string, unknown> = {
        enabled: true,
        active_provider: tutorProviderMode.value,
        provider_profiles: profilesPayload,
        provider_url: activeProviderUrl,
        daily_limit: Number.isFinite(tutor.value.dailyLimit) ? tutor.value.dailyLimit : 0,
        model: (tutor.value.model ?? '').trim() || null,
      }
      if ((tutor.value.apiKey ?? '').trim()) {
        tutorPayload.api_key = (tutor.value.apiKey ?? '').trim()
      }

      const integrationsPayload = clonePlain(integrationDrafts.value)
      for (const [platformId, values] of Object.entries(integrationsPayload)) {
        const cleaned: Record<string, string> = {}
        for (const [key, value] of Object.entries(values)) {
          if (typeof value === 'string' && value.trim()) {
            cleaned[key] = value.trim()
          }
        }
        integrationsPayload[platformId] = cleaned
      }

      const languagesPayload = Object.fromEntries(
        EDITOR_RUNTIMES.map((runtime) => [
          runtime,
          { enabled: languageEnabled.value[runtime] },
        ]),
      )

      await patchSettings({
        settings: {
          editor: {
            autocomplete: autocomplete.value,
            mode: mode.value,
            languages: languagesPayload,
          },
          tutor: tutorPayload,
          integrations: integrationsPayload,
        },
      })
      tutor.value.apiKey = ''

      try {
        syncFromSettings()
      } catch (syncError) {
        console.error('settings sync after save failed', syncError)
      }
      toasts.success(t('settings.saved'))
    } catch (error) {
      const detail = extractErrorMessage(error)
      toasts.error(detail || t('settings.errors.saveFailed'))
    } finally {
      saving.value = false
    }
  }

  const serviceRows = computed(() =>
    adapters.value.map((adapter) => {
      const classes = platformStatusClasses(adapter)
      return {
        adapter,
        iconClass: classes.icon,
        badgeClass: classes.badge,
        statusLabel: platformStatusLabel(adapter),
      }
    }),
  )

  return {
    EDITOR_RUNTIMES,
    OPENAI_PROVIDER_URL,
    OPENAI_DEFAULT_MODEL,
    CURSOR_PROXY_URL,
    CURSOR_DEFAULT_MODEL,
    t,
    pending,
    saving,
    adapters,
    serviceRows,
    openSection,
    selectedPlatform,
    autocomplete,
    mode,
    languageEnabled,
    tutor,
    tutorProviderMode,
    hasStoredApiKey,
    llmStatus,
    llmStatusPending,
    modelsLoadPending,
    baseline,
    authAdapters,
    publicAdapters,
    connectedAuthCount,
    editorSummary,
    tutorSummary,
    activeProviderLabel,
    sectionIdForIntegration,
    isSectionOpen,
    toggleSection,
    platformStatus,
    platformStatusClasses,
    selectPlatform,
    availableLlmModels,
    modelsFilteredToPreferred,
    selectedModelDescription,
    isModelInList,
    loadAvailableModels,
    fieldsFor,
    requiredFieldsFor,
    isOptionalField,
    fieldHint,
    fieldPlaceholder,
    platformHelp,
    authTypeLabel,
    isConnected,
    hasUnsavedCredentials,
    platformStatusLabel,
    integrationDirty,
    draftFor,
    fieldLabel,
    platformCapabilities,
    runtimeLabel,
    languagesDirty,
    tutorDirty,
    dirty,
    discardChanges,
    submit,
  }
}
