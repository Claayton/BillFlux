<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'
import logoUrl from '@/assets/logo.png'

const auth = useAuthStore()

// Mantém a sessão deslizante de 24h viva durante o turno e detecta
// sessão morta antes do usuário estar no meio de uma venda.
const HEARTBEAT_MS = 15 * 60 * 1000
let heartbeatTimer = null

async function keepAlive() {
  if (!auth.isAuthenticated) return
  // 401 aqui cai no handler global (redirect + aviso na tela de login).
  const data = await api.get('/auth/me').catch(() => null)
  if (!data) return
  auth.user = data.user
  if (typeof data.allow_signup === 'boolean') auth.allowSignup = data.allow_signup
}

function onVisibilityChange() {
  if (document.visibilityState === 'visible') keepAlive()
}

onMounted(() => {
  keepAlive()
  heartbeatTimer = setInterval(keepAlive, HEARTBEAT_MS)
  document.addEventListener('visibilitychange', onVisibilityChange)
})

onBeforeUnmount(() => {
  if (heartbeatTimer) clearInterval(heartbeatTimer)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<template>
  <router-view v-if="!auth.loading" />
  <div v-else class="app-boot">
    <img class="app-boot-mark" :src="logoUrl" alt="BeeFlux" />
    <p>Carregando BeeFlux…</p>
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
  width: 60px;
  height: 60px;
  border-radius: 14px;
  object-fit: contain;
}
</style>