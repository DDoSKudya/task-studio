<script setup lang="ts">
function isAuthShell(path: string, layout: unknown) {
  return layout === 'auth' || path === '/login' || path === '/register' || path === '/auth'
}

const route = useRoute()
const suppressPageTransition = useState('suppress-page-transition', () => false)

const layoutTransition = {
  name: 'shell-swap',
  mode: 'out-in' as const,
}

const authPageTransition = {
  name: 'auth-page',
  mode: 'out-in' as const,
}

const defaultPageTransition = {
  name: 'page-cyber',
  mode: 'out-in' as const,
}

const silentPageTransition = {
  name: 'page-none',
  mode: 'out-in' as const,
}

const router = useRouter()
router.beforeEach((to, from) => {
  if (!from.matched.length) {
    suppressPageTransition.value = false
    return
  }

  suppressPageTransition.value =
    isAuthShell(from.path, from.meta.layout) !== isAuthShell(to.path, to.meta.layout)
})

router.afterEach(() => {
  nextTick(() => {
    suppressPageTransition.value = false
  })
})

const pageTransition = computed(() => {
  if (suppressPageTransition.value) {
    return silentPageTransition
  }
  if (isAuthShell(route.path, route.meta.layout)) {
    return authPageTransition
  }
  return defaultPageTransition
})

function pageKey(r: { path: string }) {
  return r.path
}
</script>

<template>
  <div class="app-root">
    <OpBackdrop />
    <NuxtLayout :transition="layoutTransition">
      <NuxtPage :transition="pageTransition" :page-key="pageKey" />
    </NuxtLayout>
    <AppToastStack />
  </div>
</template>

<style scoped>
.app-root {
  position: relative;
  min-height: 100vh;
  overflow-x: hidden;
}
</style>
