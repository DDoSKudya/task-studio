<script setup lang="ts">
import {
  ArrowPathIcon,
  ArrowTopRightOnSquareIcon,
  ChevronDownIcon,
  CloudIcon,
  CodeBracketSquareIcon,
  CpuChipIcon,
  GlobeAltIcon,
  KeyIcon,
  SignalIcon,
  SparklesIcon,
} from '@heroicons/vue/24/outline'
import { useCredentialAutofill } from '~/composables/useCredentialAutofill'
import {
  credentialFieldKey,
  isSecretCredentialField,
} from '~/utils/settings'

const {
  EDITOR_RUNTIMES,
  OPENAI_PROVIDER_URL,
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
  selectPlatform,
  availableLlmModels,
  modelsFilteredToPreferred,
  selectedModelDescription,
  isModelInList,
  loadAvailableModels,
  fieldsFor,
  isOptionalField,
  fieldHint,
  fieldPlaceholder,
  platformHelp,
  authTypeLabel,
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
} = useSettingsPage()

const {
  unlockCredentialField,
  isCredentialFieldUnlocked,
} = useCredentialAutofill(() => openSection.value)
</script>

<template>
  <PageShell fill :title="t('settings.title')" :meta="t('settings.subtitle')">
    <template #actions>
      <Transition name="op-panel">
        <div v-if="dirty && !pending" class="board-toolbar-actions">
          <button type="button" class="btn-ghost" :disabled="saving" @click="discardChanges">
            {{ t('settings.cancel') }}
          </button>
          <button type="submit" form="settings-form" class="btn-primary" :disabled="saving">
            <ArrowPathIcon v-if="saving" class="icon-sm icon-spin" aria-hidden="true" />
            {{ saving ? t('settings.loading') : t('settings.save') }}
          </button>
        </div>
      </Transition>
    </template>

    <div v-if="pending" class="loading-state">
      <span class="loading-spinner" aria-hidden="true" />
      <p class="page-meta">{{ t('settings.loading') }}</p>
    </div>

    <form v-else id="settings-form" class="settings-form-shell" autocomplete="off" @submit.prevent="submit">
      <div class="settings-layout">
        <aside class="settings-panel settings-status-panel">
          <header class="settings-panel-header">
            <div class="settings-panel-head">
              <span class="settings-panel-icon">
                <SignalIcon class="icon-md" aria-hidden="true" />
              </span>
              <div>
                <p class="settings-eyebrow">{{ t('settings.integrations.eyebrow') }}</p>
                <h2 class="settings-panel-title">{{ t('settings.integrations.title') }}</h2>
              </div>
            </div>
          </header>

          <div class="settings-panel-body">
            <section class="settings-status-hero">
              <p class="settings-status-hero-label">{{ t('settings.integrations.summaryLabel') }}</p>
              <p class="settings-status-hero-value">
                {{
                  t('settings.integrations.summaryValue', {
                    connected: connectedAuthCount,
                    total: authAdapters.length,
                    public: publicAdapters.length,
                  })
                }}
              </p>
            </section>

            <div v-if="adapters.length === 0" class="panel-empty">
              <p class="empty-state-title">{{ t('settings.integrations.empty') }}</p>
            </div>

            <ul v-else class="settings-service-list">
              <li v-for="row in serviceRows" :key="row.adapter.id">
                <button
                  type="button"
                  class="settings-service-row"
                  :class="{
                    'settings-service-row-active': selectedPlatform === row.adapter.id,
                    'settings-service-row-auth': row.adapter.capabilities.requires_auth,
                  }"
                  @click="selectPlatform(row.adapter)"
                >
                  <span
                    class="settings-service-icon"
                    :class="row.iconClass"
                  >
                    <KeyIcon v-if="row.adapter.capabilities.requires_auth" class="icon-sm" aria-hidden="true" />
                    <CloudIcon v-else class="icon-sm" aria-hidden="true" />
                  </span>
                  <div class="settings-service-body">
                    <div class="settings-service-top">
                      <span class="settings-service-name">{{ row.adapter.display_name }}</span>
                      <span
                        class="settings-service-badge"
                        :class="row.badgeClass"
                      >
                        {{ row.statusLabel }}
                      </span>
                    </div>
                    <p class="settings-service-desc">{{ platformCapabilities(row.adapter) }}</p>
                    <div class="settings-service-actions">
                      <NuxtLink
                        class="btn-ghost btn-sm"
                        :to="`/catalog?platform=${row.adapter.id}`"
                        @click.stop
                      >
                        {{ t('settings.integrations.browseCatalog') }}
                        <ArrowTopRightOnSquareIcon class="icon-sm" />
                      </NuxtLink>
                    </div>
                  </div>
                </button>
              </li>
            </ul>
          </div>
        </aside>

        <section class="settings-panel settings-config-panel">
          <header class="settings-panel-header">
            <div class="settings-panel-head">
              <span class="settings-panel-icon">
                <CpuChipIcon class="icon-md" aria-hidden="true" />
              </span>
              <div>
                <p class="settings-eyebrow">{{ t('settings.configEyebrow') }}</p>
                <h2 class="settings-panel-title">{{ t('settings.configTitle') }}</h2>
              </div>
            </div>
          </header>

          <div class="settings-panel-body settings-config-body">
            <div class="settings-config-group">
              <div class="settings-config-group-header">
                <h3 class="settings-config-group-title">{{ t('settings.sourcesGroupTitle') }}</h3>
                <p class="settings-config-group-meta">{{ t('settings.sourcesGroupMeta') }}</p>
              </div>
              <div class="settings-accordion">
              <section
                v-for="adapter in authAdapters"
                :key="adapter.id"
                class="settings-accordion-item"
                :class="{ 'settings-accordion-item-open': isSectionOpen(sectionIdForIntegration(adapter.id)) }"
              >
                <button
                  type="button"
                  class="settings-accordion-trigger"
                  :aria-expanded="isSectionOpen(sectionIdForIntegration(adapter.id))"
                  @click="toggleSection(sectionIdForIntegration(adapter.id))"
                >
                  <span class="settings-accordion-icon">
                    <KeyIcon class="icon-sm" aria-hidden="true" />
                  </span>
                  <span class="settings-accordion-copy">
                    <span class="settings-accordion-title">{{ adapter.display_name }}</span>
                    <span class="settings-accordion-summary">
                      {{ authTypeLabel(adapter) }}
                      ·
                      {{ platformStatusLabel(adapter) }}
                    </span>
                  </span>
                  <span v-if="integrationDirty(adapter.id)" class="settings-accordion-dot" aria-hidden="true" />
                  <ChevronDownIcon class="settings-accordion-chevron icon-sm" aria-hidden="true" />
                </button>
                <Transition name="op-panel">
                  <div
                    v-if="isSectionOpen(sectionIdForIntegration(adapter.id))"
                    class="settings-accordion-body"
                  >
                  <p class="settings-group-meta">{{ platformHelp(adapter) }}</p>
                  <div class="settings-integration-meta">
                    <span class="settings-auth-badge">{{ authTypeLabel(adapter) }}</span>
                    <span class="settings-integration-caps">{{ platformCapabilities(adapter) }}</span>
                  </div>
                  <div class="settings-credentials-block">
                    <label
                      v-for="field in fieldsFor(adapter)"
                      :key="field"
                      class="settings-field-block"
                    >
                      <span class="settings-field-label">
                        {{ fieldLabel(field) }}
                        <span
                          v-if="isOptionalField(adapter, field)"
                          class="settings-field-optional"
                        >
                          {{ t('settings.integrations.optionalBadge') }}
                        </span>
                      </span>
                      <input
                        v-model="draftFor(adapter.id)[field]"
                        class="field field-input"
                        :name="`ts-int-${adapter.id}-${field}`"
                        :type="isSecretCredentialField(field) ? 'password' : field === 'base_url' ? 'url' : 'text'"
                        :autocomplete="isSecretCredentialField(field) ? 'new-password' : 'off'"
                        :readonly="!isCredentialFieldUnlocked(credentialFieldKey(adapter.id, field))"
                        data-lpignore="true"
                        data-1p-ignore="true"
                        data-bwignore="true"
                        data-form-type="other"
                        :placeholder="fieldPlaceholder(adapter, field)"
                        @focus="unlockCredentialField(credentialFieldKey(adapter.id, field))"
                      >
                      <span v-if="fieldHint(adapter, field)" class="settings-field-hint">
                        {{ fieldHint(adapter, field) }}
                      </span>
                    </label>
                  </div>
                  <div class="settings-integration-actions">
                    <NuxtLink class="btn-ghost btn-sm" :to="`/catalog?platform=${adapter.id}`">
                      {{ t('settings.integrations.browseCatalog') }}
                      <ArrowTopRightOnSquareIcon class="icon-sm" />
                    </NuxtLink>
                  </div>
                </div>
                </Transition>
              </section>

              <section
                v-for="adapter in publicAdapters"
                :key="adapter.id"
                class="settings-accordion-item"
                :class="{ 'settings-accordion-item-open': isSectionOpen(sectionIdForIntegration(adapter.id)) }"
              >
                <button
                  type="button"
                  class="settings-accordion-trigger"
                  :aria-expanded="isSectionOpen(sectionIdForIntegration(adapter.id))"
                  @click="toggleSection(sectionIdForIntegration(adapter.id))"
                >
                  <span class="settings-accordion-icon">
                    <CloudIcon class="icon-sm" aria-hidden="true" />
                  </span>
                  <span class="settings-accordion-copy">
                    <span class="settings-accordion-title">{{ adapter.display_name }}</span>
                    <span class="settings-accordion-summary">
                      {{ t('settings.integrations.publicAccess') }}
                    </span>
                  </span>
                  <ChevronDownIcon class="settings-accordion-chevron icon-sm" aria-hidden="true" />
                </button>
                <Transition name="op-panel">
                  <div
                    v-if="isSectionOpen(sectionIdForIntegration(adapter.id))"
                    class="settings-accordion-body"
                  >
                  <p class="settings-group-meta">{{ t('settings.integrations.publicMeta') }}</p>
                  <div class="settings-integration-meta">
                    <span class="settings-auth-badge settings-auth-badge-ok">
                      {{ t('settings.integrations.noAuthShort') }}
                    </span>
                    <span class="settings-integration-caps">{{ platformCapabilities(adapter) }}</span>
                  </div>
                  <div class="settings-integration-actions">
                    <NuxtLink class="btn-ghost btn-sm" :to="`/catalog?platform=${adapter.id}`">
                      {{ t('settings.integrations.browseCatalog') }}
                      <ArrowTopRightOnSquareIcon class="icon-sm" />
                    </NuxtLink>
                  </div>
                </div>
                </Transition>
              </section>
              </div>
            </div>

            <div class="settings-config-group">
              <div class="settings-config-group-header">
                <h3 class="settings-config-group-title">{{ t('settings.toolsGroupTitle') }}</h3>
              </div>
              <div class="settings-accordion">
              <section
                class="settings-accordion-item"
                :class="{ 'settings-accordion-item-open': isSectionOpen('tutor') }"
              >
                <button
                  type="button"
                  class="settings-accordion-trigger"
                  :aria-expanded="isSectionOpen('tutor')"
                  @click="toggleSection('tutor')"
                >
                  <span class="settings-accordion-icon">
                    <SparklesIcon class="icon-sm" aria-hidden="true" />
                  </span>
                  <span class="settings-accordion-copy">
                    <span class="settings-accordion-title">{{ t('settings.tutorTitle') }}</span>
                    <span class="settings-accordion-summary">{{ tutorSummary }}</span>
                  </span>
                  <span v-if="tutorDirty()" class="settings-accordion-dot" aria-hidden="true" />
                  <ChevronDownIcon class="settings-accordion-chevron icon-sm" aria-hidden="true" />
                </button>
                <Transition name="op-panel">
                  <div v-if="isSectionOpen('tutor')" class="settings-accordion-body">
                  <p class="settings-group-meta">{{ t('settings.tutorMeta') }}</p>

                  <p class="settings-field-label" style="margin-top: 0.25rem">
                    {{ t('settings.tutor.providerLabel') }}
                  </p>
                  <div
                    class="settings-choice-list"
                    role="radiogroup"
                    :aria-label="t('settings.tutor.providerLabel')"
                    @click.stop
                  >
                    <label
                      class="settings-choice-row"
                      :class="{ 'settings-choice-row-active': tutorProviderMode === 'ollama' }"
                    >
                      <input
                        v-model="tutorProviderMode"
                        class="sr-only"
                        type="radio"
                        name="tutor-provider"
                        value="ollama"
                      >
                      <span class="settings-choice-icon">
                        <CpuChipIcon class="icon-sm" aria-hidden="true" />
                      </span>
                      <span class="settings-choice-copy">
                        <span class="settings-choice-title">{{ t('settings.tutor.providers.ollama') }}</span>
                        <span class="settings-choice-desc">{{ t('settings.tutor.providers.ollamaMeta') }}</span>
                      </span>
                      <span class="settings-choice-mark" aria-hidden="true" />
                    </label>
                    <label
                      class="settings-choice-row"
                      :class="{ 'settings-choice-row-active': tutorProviderMode === 'external' }"
                    >
                      <input
                        v-model="tutorProviderMode"
                        class="sr-only"
                        type="radio"
                        name="tutor-provider"
                        value="external"
                      >
                      <span class="settings-choice-icon">
                        <CloudIcon class="icon-sm" aria-hidden="true" />
                      </span>
                      <span class="settings-choice-copy">
                        <span class="settings-choice-title">{{ t('settings.tutor.providers.external') }}</span>
                        <span class="settings-choice-desc">{{ t('settings.tutor.providers.externalMeta') }}</span>
                      </span>
                      <span class="settings-choice-mark" aria-hidden="true" />
                    </label>
                    <label
                      class="settings-choice-row"
                      :class="{ 'settings-choice-row-active': tutorProviderMode === 'cursor' }"
                    >
                      <input
                        v-model="tutorProviderMode"
                        class="sr-only"
                        type="radio"
                        name="tutor-provider"
                        value="cursor"
                      >
                      <span class="settings-choice-icon">
                        <SparklesIcon class="icon-sm" aria-hidden="true" />
                      </span>
                      <span class="settings-choice-copy">
                        <span class="settings-choice-title">{{ t('settings.tutor.providers.cursor') }}</span>
                        <span class="settings-choice-desc">{{ t('settings.tutor.providers.cursorMeta') }}</span>
                      </span>
                      <span class="settings-choice-mark" aria-hidden="true" />
                    </label>
                  </div>

                  <div
                    v-if="llmStatus"
                    class="settings-provider-summary"
                    :data-ok="llmStatus.ok || undefined"
                  >
                    <p class="settings-provider-summary-label">{{ t('settings.tutor.activeProvider') }}</p>
                    <p class="settings-provider-summary-value">
                      {{ activeProviderLabel }}
                    </p>
                    <p
                      class="settings-provider-status"
                      :class="llmStatus.ok ? 'settings-provider-status-ok' : 'settings-provider-status-bad'"
                    >
                      {{ llmStatus.detail }}
                    </p>
                  </div>
                  <div v-else class="settings-provider-summary">
                    <p class="settings-provider-summary-label">{{ t('settings.tutor.activeProvider') }}</p>
                    <p class="settings-provider-summary-value">
                      {{ activeProviderLabel }}
                    </p>
                  </div>

                  <div class="settings-credentials-block">
                    <template v-if="tutorProviderMode === 'external'">
                      <label class="settings-field-block">
                        <span class="settings-field-label">{{ t('settings.tutorProviderUrl') }}</span>
                        <input
                          v-model="tutor.providerUrl"
                          class="field field-input"
                          name="ts-tutor-provider-url"
                          type="url"
                          autocomplete="off"
                          data-lpignore="true"
                          data-1p-ignore="true"
                          data-form-type="other"
                          :placeholder="OPENAI_PROVIDER_URL"
                        >
                        <span class="settings-field-hint">{{ t('settings.tutorProviderUrlHint') }}</span>
                      </label>
                      <label class="settings-field-block">
                        <span class="settings-field-label">{{ t('settings.tutorApiKey') }}</span>
                        <input
                          v-model="tutor.apiKey"
                          class="field field-input"
                          name="ts-tutor-api-key"
                          type="password"
                          autocomplete="new-password"
                          :readonly="!isCredentialFieldUnlocked('tutor:api_key')"
                          data-lpignore="true"
                          data-1p-ignore="true"
                          data-bwignore="true"
                          data-form-type="other"
                          @focus="unlockCredentialField('tutor:api_key')"
                        >
                        <span class="settings-field-hint">
                          {{
                            hasStoredApiKey
                              ? t('settings.tutorApiKeyStored')
                              : t('settings.tutorApiKeyHint')
                          }}
                        </span>
                      </label>
                    </template>
                    <template v-else-if="tutorProviderMode === 'cursor'">
                      <label class="settings-field-block">
                        <span class="settings-field-label">{{ t('settings.tutorApiKey') }}</span>
                        <input
                          v-model="tutor.apiKey"
                          class="field field-input"
                          name="ts-tutor-cursor-key"
                          type="password"
                          autocomplete="new-password"
                          :readonly="!isCredentialFieldUnlocked('tutor:api_key')"
                          data-lpignore="true"
                          data-1p-ignore="true"
                          data-bwignore="true"
                          data-form-type="other"
                          @focus="unlockCredentialField('tutor:api_key')"
                        >
                        <span class="settings-field-hint">
                          {{
                            hasStoredApiKey
                              ? t('settings.tutorApiKeyStored')
                              : t('settings.tutor.providers.cursorKeyHint')
                          }}
                        </span>
                      </label>
                    </template>
                    <div class="settings-field-block">
                      <div class="settings-field-label-row">
                        <span class="settings-field-label">
                          {{ t('settings.tutorModel') }}
                          <span class="field-required" aria-hidden="true">*</span>
                        </span>
                        <button
                          type="button"
                          class="settings-icon-btn"
                          :disabled="modelsLoadPending || saving || llmStatusPending"
                          :title="t('settings.tutor.loadModels')"
                          :aria-label="t('settings.tutor.loadModels')"
                          @click="loadAvailableModels()"
                        >
                          <ArrowPathIcon
                            class="icon-sm"
                            :class="{ 'icon-spin': modelsLoadPending }"
                            aria-hidden="true"
                          />
                        </button>
                      </div>
                      <select
                        v-model="tutor.model"
                        class="field field-input"
                        required
                        :aria-required="true"
                      >
                        <option value="" disabled>
                          {{ t('settings.tutor.modelPlaceholder') }}
                        </option>
                        <option
                          v-if="tutor.model && (!availableLlmModels.length || !isModelInList(tutor.model, availableLlmModels))"
                          :value="tutor.model"
                        >
                          {{ tutor.model }}
                        </option>
                        <option
                          v-for="modelName in availableLlmModels"
                          :key="modelName"
                          :value="modelName"
                        >
                          {{ modelName }}
                        </option>
                      </select>
                      <span
                        v-if="selectedModelDescription"
                        class="settings-model-desc"
                      >{{ selectedModelDescription }}</span>
                      <span class="settings-field-hint">
                        {{
                          !availableLlmModels.length
                            ? t('settings.tutor.modelRequiredHint')
                            : modelsFilteredToPreferred
                              ? t('settings.tutor.modelsPreferredHint')
                              : tutorProviderMode === 'ollama'
                                ? t('settings.tutorModelHintOllama')
                                : t('settings.tutorModelHint')
                        }}
                      </span>
                    </div>
                    <label class="settings-field-block">
                      <span class="settings-field-label">{{ t('settings.tutorDailyLimit') }}</span>
                      <input v-model.number="tutor.dailyLimit" class="field field-input" type="number" min="0">
                    </label>
                  </div>
                </div>
                </Transition>
              </section>

              <section
                class="settings-accordion-item"
                :class="{ 'settings-accordion-item-open': isSectionOpen('editor') }"
              >
                <button
                  type="button"
                  class="settings-accordion-trigger"
                  :aria-expanded="isSectionOpen('editor')"
                  @click="toggleSection('editor')"
                >
                  <span class="settings-accordion-icon">
                    <CodeBracketSquareIcon class="icon-sm" aria-hidden="true" />
                  </span>
                  <span class="settings-accordion-copy">
                    <span class="settings-accordion-title">{{ t('settings.editorTitle') }}</span>
                    <span class="settings-accordion-summary">{{ editorSummary }}</span>
                  </span>
                  <span
                    v-if="autocomplete !== baseline.autocomplete || mode !== baseline.mode || languagesDirty()"
                    class="settings-accordion-dot"
                    aria-hidden="true"
                  />
                  <ChevronDownIcon class="settings-accordion-chevron icon-sm" aria-hidden="true" />
                </button>
                <Transition name="op-panel">
                  <div v-if="isSectionOpen('editor')" class="settings-accordion-body">
                  <p class="settings-group-meta">{{ t('settings.editorMeta') }}</p>

                  <div class="settings-choice-list" role="radiogroup" :aria-label="t('settings.editorTitle')">
                    <label
                      class="settings-choice-row"
                      :class="{ 'settings-choice-row-active': mode === 'full' }"
                    >
                      <input v-model="mode" class="sr-only" type="radio" value="full">
                      <span class="settings-choice-icon">
                        <CodeBracketSquareIcon class="icon-sm" aria-hidden="true" />
                      </span>
                      <span class="settings-choice-copy">
                        <span class="settings-choice-title">{{ t('settings.modeFull') }}</span>
                        <span class="settings-choice-desc">{{ t('settings.modeFullMeta') }}</span>
                      </span>
                      <span class="settings-choice-mark" aria-hidden="true" />
                    </label>
                    <label
                      class="settings-choice-row"
                      :class="{ 'settings-choice-row-active': mode === 'syntax_only' }"
                    >
                      <input v-model="mode" class="sr-only" type="radio" value="syntax_only">
                      <span class="settings-choice-icon">
                        <GlobeAltIcon class="icon-sm" aria-hidden="true" />
                      </span>
                      <span class="settings-choice-copy">
                        <span class="settings-choice-title">{{ t('settings.modeSyntaxOnly') }}</span>
                        <span class="settings-choice-desc">{{ t('settings.modeSyntaxOnlyMeta') }}</span>
                      </span>
                      <span class="settings-choice-mark" aria-hidden="true" />
                    </label>
                  </div>

                  <label class="settings-toggle-row">
                    <span class="settings-toggle-copy">
                      <span class="settings-toggle-title">{{ t('settings.autocomplete') }}</span>
                      <span class="settings-toggle-hint">{{ t('settings.autocompleteMeta') }}</span>
                    </span>
                    <span class="toggle-switch">
                      <input v-model="autocomplete" class="toggle-input" type="checkbox">
                      <span class="toggle-track" />
                      <span class="toggle-thumb" />
                    </span>
                  </label>

                  <p class="settings-field-label" style="margin-top: 0.75rem">{{ t('settings.languages') }}</p>
                  <label
                    v-for="runtime in EDITOR_RUNTIMES"
                    :key="runtime"
                    class="settings-toggle-row"
                  >
                    <span class="settings-toggle-copy">
                      <span class="settings-toggle-title">{{ runtimeLabel(runtime) }}</span>
                    </span>
                    <span class="toggle-switch">
                      <input v-model="languageEnabled[runtime]" class="toggle-input" type="checkbox">
                      <span class="toggle-track" />
                      <span class="toggle-thumb" />
                    </span>
                  </label>
                </div>
                </Transition>
              </section>
              </div>
            </div>
          </div>
        </section>
      </div>
    </form>
  </PageShell>
</template>
