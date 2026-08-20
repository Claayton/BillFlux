<script setup>
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <router-view v-if="!auth.loading" />
  <div v-else class="app-boot">
    <div class="app-boot-mark">BF</div>
    <p>Carregando BillFlux…</p>
  </div>
</template>

<style scoped>
.app-boot {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--text-muted);
  font-size: 14px;
}
.app-boot-mark {
  width: 48px;
  height: 48px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  background: var(--primary);
  color: #fff;
  font-weight: 800;
}
</style>