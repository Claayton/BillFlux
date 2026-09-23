<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PublicHeader from '@/components/PublicHeader.vue'
import { useAuthStore } from '@/stores/auth'
import logoUrl from '@/assets/logo.png'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const sessionExpired = ref(false)

onMounted(() => {
  sessionExpired.value = route.query.expired === '1'
})
const username = ref('')
const password = ref('')
const loading = ref(false)
const showPassword = ref(false)
const userEmpty = ref(false)
const passEmpty = ref(false)

function forgotPassword() {
  ElMessage.info('Fale com o administrador do sistema para redefinir sua senha.')
}

async function submit() {
  userEmpty.value = !username.value
  passEmpty.value = !password.value
  if (!username.value || !password.value) {
    ElMessage.warning('Informe usuário e senha.')
    return
  }
  loading.value = true
  try {
    await auth.login(username.value, password.value)
    ElMessage.success(`Bem-vindo, ${username.value}!`)
    router.push(String(route.query.redirect || '/sales'))
  } catch (error) {
    ElMessage.error(error.message || 'Usuário ou senha inválidos.')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div>
    <PublicHeader />
    <section class="auth-page">
      <div class="auth-card">
        <div class="auth-header">
          <img class="logo-mark" :src="logoUrl" alt="BeeFlux" />
          <h2>Entrar</h2>
          <p>Acesse sua conta BeeFlux.</p>
          <p v-if="sessionExpired" class="auth-notice" role="alert">
            Sua sessão expirou. Entre novamente para continuar.
          </p>
        </div>

        <form class="auth-form" @submit.prevent="submit" novalidate>
          <div class="form-field" :class="{ 'has-error': userEmpty }">
            <label for="login-username">Usuário</label>
            <input
              id="login-username"
              v-model.trim="username"
              type="text"
              autocomplete="username"
              required
              placeholder="Seu usuário"
              @input="userEmpty = false"
            />
          </div>
          <div class="form-field" :class="{ 'has-error': passEmpty }">
            <label for="login-password">Senha</label>
            <div class="password-wrap">
              <input
                id="login-password"
                v-model="password"
                :type="showPassword ? 'text' : 'password'"
                autocomplete="current-password"
                required
                placeholder="Sua senha"
                @input="passEmpty = false"
              />
              <button
                type="button"
                class="password-toggle"
                :aria-label="showPassword ? 'Ocultar senha' : 'Mostrar senha'"
                :title="showPassword ? 'Ocultar senha' : 'Mostrar senha'"
                @click="showPassword = !showPassword"
              >
                <svg
                  v-if="!showPassword"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7-10-7-10-7z" />
                  <circle cx="12" cy="12" r="3" />
                </svg>
                <svg
                  v-else
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.8"
                  stroke-linecap="round"
                  stroke-linejoin="round"
                >
                  <path d="M17.94 17.94A10.6 10.6 0 0 1 12 19c-6.5 0-10-7-10-7a17.6 17.6 0 0 1 4.06-4.94" />
                  <path d="M9.9 4.24A10.6 10.6 0 0 1 12 5c6.5 0 10 7 10 7a17.7 17.7 0 0 1-2.16 3.19" />
                  <path d="m2 2 20 20" />
                  <path d="M9.88 9.88a3 3 0 1 0 4.24 4.24" />
                </svg>
              </button>
            </div>
          </div>
          <div class="forgot-row">
            <button type="button" class="forgot-link" @click="forgotPassword">
              Esqueci minha senha
            </button>
          </div>
          <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
            <span v-if="loading" class="btn-spinner" aria-hidden="true"></span>
            {{ loading ? 'Entrando…' : 'Entrar' }}
          </button>
        </form>

        <p v-if="auth.allowSignup" class="auth-footer">
          Ainda não tem conta?
          <router-link to="/signin">Criar conta</router-link>
        </p>
      </div>
    </section>
  </div>
</template>