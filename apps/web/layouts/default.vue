<template>
  <div class="layout-root">
    <AppLayout>
      <slot />
    </AppLayout>
    <AppConfirmDialog />
  </div>
</template>

<style scoped>
.layout-root {
  position: relative;
  z-index: 1;
  min-height: 100vh;
}
</style>
