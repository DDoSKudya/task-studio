<script setup lang="ts">
function isAuthShell(path: string, layout: unknown) {
  return layout === 'auth' || path === '/login' || path === '/register' || path === '/auth'
}

const route = useRoute()
const suppressPageTransition = useState('suppress-page-transition', () => false)

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

  suppressPageTransition.value = false
})

const layoutTransition = {
  name: 'shell-swap',
  mode: 'out-in' as const,
}

const pageTransition = computed(() => {
  if (suppressPageTransition.value) {
    return false
  }
  if (isAuthShell(route.path, route.meta.layout)) {
    return {
      name: 'auth-page',
      mode: 'out-in' as const,
    }
  }
  return {
    name: 'page-cyber',
    mode: 'out-in' as const,
  }
})
</script>

<template>
  <div class="app-root">
    <OpBackdrop />
    <NuxtLayout :transition="layoutTransition">
      <NuxtPage :transition="pageTransition" />
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
