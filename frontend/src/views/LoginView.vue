<script setup>
import { ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PublicHeader from '@/components/PublicHeader.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()
const username = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
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
          <span class="logo-mark">BF</span>
          <h2>Entrar</h2>
          <p>Acesse sua conta BillFlux.</p>
        </div>

        <form class="auth-form" @submit.prevent="submit">
          <div class="form-field">
            <label for="login-username">Usuário</label>
            <input
              id="login-username"
              v-model="username"
              type="text"
              autocomplete="username"
              required
              placeholder="Seu usuário"
            />
          </div>
          <div class="form-field">
            <label for="login-password">Senha</label>
            <input
              id="login-password"
              v-model="password"
              type="password"
              autocomplete="current-password"
              required
              placeholder="Sua senha"
            />
          </div>
          <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
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