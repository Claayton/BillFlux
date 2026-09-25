<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useAuthStore } from '@/stores/auth'
import logoUrl from '@/assets/logo.png'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)
const sessionExpired = ref(false)
const showPassword = ref(false)
const userEmpty = ref(false)
const passEmpty = ref(false)

onMounted(() => {
  sessionExpired.value = route.query.expired === '1'
})

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
  <div class="landing-split">
    <section class="split-left">
      <span class="orb orb-a" aria-hidden="true"></span>
      <span class="orb orb-b" aria-hidden="true"></span>

      <div class="float-card float-sale rise rise-4" aria-hidden="true">
        <div class="float-label">Venda aprovada</div>
        <div class="float-value">R$ 128,50</div>
        <span class="float-ok"><span class="dot"></span>PDV • agora</span>
      </div>

      <div class="float-card float-chart rise rise-5" aria-hidden="true">
        <div class="float-label">Faturamento • +18%</div>
        <div class="mini-bars">
          <i style="height: 35%; animation-delay: 0.5s"></i>
          <i style="height: 55%; animation-delay: 0.58s"></i>
          <i style="height: 42%; animation-delay: 0.66s"></i>
          <i style="height: 70%; animation-delay: 0.74s"></i>
          <i style="height: 58%; animation-delay: 0.82s"></i>
          <i style="height: 85%; animation-delay: 0.9s"></i>
          <i style="height: 100%; animation-delay: 0.98s"></i>
        </div>
      </div>

      <div class="split-left-inner">
        <div class="hero-brand rise rise-1">
          <img :src="logoUrl" alt="B" />
          <span>eeFlux</span>
        </div>
        <div class="hero-badge rise rise-2">Vendas, PDV e contas em um só lugar</div>
        <h1 class="rise rise-2">Seu comércio sob controle, sem dor de cabeça.</h1>
        <p class="split-subtitle rise rise-3">
          Feche vendas no PDV, acompanhe o faturamento e organize as contas a pagar —
          simples, direto e sem enrolação.
        </p>
        <div class="split-features rise rise-4">
          <div class="feature">
            <span class="feature-glyph">
              <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M13 2 4.5 13.5H11L10 22l8.5-11.5H12L13 2z" />
              </svg>
            </span>
            <span>PDV rápido<small>Venda em segundos, com recibo na hora</small></span>
          </div>
          <div class="feature">
            <span class="feature-glyph">
              <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <path d="M3 3v16a2 2 0 0 0 2 2h16" />
                <path d="M7 14l4-4 3 3 5-6" />
                <circle cx="19" cy="7" r="1.4" fill="#fff" stroke="none" />
              </svg>
            </span>
            <span>Relatórios de vendas<small>Faturamento e margem sempre à vista</small></span>
          </div>
          <div class="feature">
            <span class="feature-glyph">
              <svg viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="5" width="18" height="16" rx="3" />
                <path d="M3 10h18M8 3v4M16 3v4" />
                <path d="m10.5 15 2 2 3.5-4" />
              </svg>
            </span>
            <span>Controle de vencimentos<small>Contas a pagar sem atraso</small></span>
          </div>
        </div>
      </div>
    </section>

    <section class="split-right">
      <div class="split-card">
        <h2>Entrar</h2>
        <p class="split-card-sub">Acesse sua conta BeeFlux.</p>
        <p v-if="sessionExpired" class="auth-notice" role="alert">
          Sua sessão expirou. Entre novamente para continuar.
        </p>

        <form class="auth-form" @submit.prevent="submit" novalidate>
          <div class="form-field" :class="{ 'has-error': userEmpty }">
            <label for="landing-username">Usuário</label>
            <input
              id="landing-username"
              v-model.trim="username"
              type="text"
              autocomplete="username"
              required
              placeholder="Seu usuário"
              @input="userEmpty = false"
            />
          </div>
          <div class="form-field" :class="{ 'has-error': passEmpty }">
            <label for="landing-password">Senha</label>
            <div class="password-wrap">
              <input
                id="landing-password"
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
