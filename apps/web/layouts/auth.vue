<template>
  <div class="auth-layout">
    <div class="auth-layout-stage">
      <slot />
    </div>
    <AppConfirmDialog />
  </div>
</template>

<style scoped>
.auth-layout {
  position: relative;
  z-index: 1;
  height: 100dvh;
  min-height: 100vh;
  overflow: hidden;
  background: transparent;
}


.auth-layout-stage {
  position: relative;
  z-index: 1;
  height: 100%;
  width: 100%;
  overflow: hidden;
}
</style>
