<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import PublicHeader from '@/components/PublicHeader.vue'
import { useAuthStore } from '@/stores/auth'
import { api } from '@/api/client'

const auth = useAuthStore()
const router = useRouter()
const username = ref('')
const email = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value || !password.value) {
    ElMessage.warning('Preencha usuário e senha.')
    return
  }
  loading.value = true
  try {
    await api.post('/auth/signin', {
      username: username.value,
      email: email.value,
      password: password.value,
    })
    ElMessage.success('Conta criada! Faça login para continuar.')
    router.push('/login')
  } catch (error) {
    ElMessage.error(error.message || 'Não foi possível criar a conta.')
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
          <h2>Criar conta</h2>
          <p>Comece a usar o BillFlux.</p>
        </div>

        <form class="auth-form" @submit.prevent="submit">
          <div class="form-field">
            <label for="signin-username">Usuário</label>
            <input
              id="signin-username"
              v-model="username"
              type="text"
              autocomplete="username"
              required
              placeholder="Mínimo de 3 caracteres"
            />
          </div>
          <div class="form-field">
            <label for="signin-email">E-mail (opcional)</label>
            <input id="signin-email" v-model="email" type="email" autocomplete="email" />
          </div>
          <div class="form-field">
            <label for="signin-password">Senha</label>
            <input
              id="signin-password"
              v-model="password"
              type="password"
              autocomplete="new-password"
              required
              placeholder="Mínimo de 4 caracteres"
            />
          </div>
          <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
            {{ loading ? 'Criando…' : 'Criar conta' }}
          </button>
        </form>

        <p class="auth-footer">
          Já tem conta?
          <router-link to="/login">Entrar</router-link>
        </p>
      </div>
    </section>
  </div>
</template>