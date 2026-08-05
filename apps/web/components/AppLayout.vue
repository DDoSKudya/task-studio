<script setup lang="ts">
import {
  AcademicCapIcon,
  ArrowRightEndOnRectangleIcon,
  ArrowRightOnRectangleIcon,
  ChartBarIcon,
  Cog6ToothIcon,
} from '@heroicons/vue/24/outline'

const route = useRoute()
const { t } = useI18n()
const { user, logout } = useAuth()
const { confirm } = useConfirm()
const { version, shortVersion, build } = useAppVersion()

const sidebarExpanded = ref(false)

const versionTitle = computed(() =>
  build > 0
    ? t('app.versionFull', { version, build })
    : t('app.versionLabel', { version }),
)

const navItems = [
  { to: '/catalog', labelKey: 'nav.catalog', icon: AcademicCapIcon, match: (path: string) => path.startsWith('/catalog') || path.startsWith('/sessions/') || path.startsWith('/search') || path === '/' },
  { to: '/analytics', labelKey: 'nav.analytics', icon: ChartBarIcon, match: (path: string) => path.startsWith('/analytics') },
  { to: '/settings', labelKey: 'nav.settings', icon: Cog6ToothIcon, match: (path: string) => path.startsWith('/settings') },
] as const

function isActive(match: (path: string) => boolean) {
  return match(route.path)
}

function expandSidebar() {
  sidebarExpanded.value = true
}

function collapseSidebar() {
  sidebarExpanded.value = false
}

function onNavFocusIn() {
  sidebarExpanded.value = true
}

function onSidebarFocusOut(event: FocusEvent) {
  const sidebar = event.currentTarget as HTMLElement | null
  const next = event.relatedTarget
  if (sidebar && next instanceof Node && sidebar.contains(next)) {
    return
  }
  sidebarExpanded.value = false
}

async function requestLogout() {
  const ok = await confirm({
    title: t('auth.logoutConfirmTitle'),
    message: t('auth.logoutConfirmMessage'),
    confirmLabel: t('auth.logout'),
    cancelLabel: t('dialog.cancel'),
    danger: true,
  })
  if (!ok) {
    return
  }
  await logout()
}

const userInitials = computed(() => {
  const email = user.value?.email ?? ''
  const local = email.split('@')[0] ?? '?'
  return local.slice(0, 2).toUpperCase()
})
</script>

<template>
  <div class="app-shell">
    <aside
      class="sidebar"
      :class="{ 'sidebar-expanded': sidebarExpanded }"
      @mouseleave="collapseSidebar"
      @focusout="onSidebarFocusOut"
    >
      <div class="sidebar-brand">
        <div class="sidebar-brand-row">
          <span class="sidebar-mark" aria-hidden="true">
            <AppIcon icon-class="sidebar-mark-icon" />
          </span>
          <div class="sidebar-brand-copy">
            <div class="sidebar-title">{{ t('app.title') }}</div>
          </div>
        </div>
        <div
          class="sidebar-version"
          :title="versionTitle"
          :aria-label="versionTitle"
        >
          <span class="sidebar-version-short">{{ shortVersion }}</span>
          <span class="sidebar-version-full">{{ version }}</span>
          <span v-if="build > 0" class="sidebar-version-build">
            {{ t('app.buildLabel', { build }) }}
          </span>
        </div>
      </div>

      <nav
        class="sidebar-nav"
        :aria-label="t('nav.main')"
        @mouseenter="expandSidebar"
        @focusin="onNavFocusIn"
      >
        <NuxtLink
          v-for="item in navItems"
          :key="item.to"
          :to="item.to"
          class="nav-link"
          :class="{ 'nav-link-active': isActive(item.match) }"
          :title="t(item.labelKey)"
        >
          <component :is="item.icon" class="nav-link-icon" />
          <span class="nav-link-label">{{ t(item.labelKey) }}</span>
        </NuxtLink>
      </nav>

      <div class="sidebar-footer">
        <div v-if="user" class="sidebar-card">
          <button
            type="button"
            class="user-card user-card-action"
            :title="t('auth.logout')"
            :aria-label="t('auth.logout')"
            @click="requestLogout"
          >
            <span class="user-avatar">{{ userInitials }}</span>
            <div class="user-card-copy">
              <div class="user-card-name">{{ user.email }}</div>
              <div class="user-card-meta">{{ t('auth.signedIn') }}</div>
            </div>
          </button>
          <button
            type="button"
            class="btn-ghost btn-sm btn-block sidebar-logout-btn"
            @click="requestLogout"
          >
            <ArrowRightOnRectangleIcon class="icon-sm" />
            {{ t('auth.logout') }}
          </button>
          <div class="sidebar-language">
            <LanguageSwitcher />
          </div>
        </div>
        <div v-else class="sidebar-card">
          <NuxtLink class="btn-primary btn-sm btn-block" to="/login">
            <ArrowRightEndOnRectangleIcon class="icon-sm" />
            {{ t('auth.login') }}
          </NuxtLink>
          <div class="sidebar-language">
            <LanguageSwitcher />
          </div>
        </div>
      </div>
    </aside>

    <div class="main-area">
      <main class="page">
        <slot />
      </main>
    </div>
  </div>
</template>
