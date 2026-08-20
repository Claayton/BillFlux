<script setup>
import PublicHeader from '@/components/PublicHeader.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <div>
    <PublicHeader />
    <section class="hero">
      <div class="hero-card">
        <div class="hero-badge">Vendas, PDV e contas em um só lugar</div>
        <h1>Seu comércio sob controle, sem dor de cabeça.</h1>
        <p class="hero-subtitle">
          Feche vendas no PDV, acompanhe o faturamento e organize as contas a pagar —
          simples, direto e sem enrolação.
        </p>
        <div class="hero-actions">
          <router-link class="btn btn-primary btn-lg" to="/login">Entrar</router-link>
          <router-link v-if="auth.allowSignup" class="btn btn-outline btn-lg" to="/signin">
            Criar conta
          </router-link>
        </div>
        <div class="hero-features">
          <div class="feature">
            <span class="feature-icon">&#128176;</span>
            <span>PDV rápido</span>
          </div>
          <div class="feature">
            <span class="feature-icon">&#128202;</span>
            <span>Relatórios de vendas</span>
          </div>
          <div class="feature">
            <span class="feature-icon">&#128197;</span>
            <span>Controle de vencimentos</span>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>