<script setup>
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
</script>

<template>
  <header class="site-header">
    <div class="container header-inner">
      <div class="header-left">
        <a class="logo" href="/">
          <span class="logo-mark">BF</span>
          <span class="logo-text">BillFlux</span>
        </a>
        <nav class="main-nav" aria-label="Navegação principal">
          <ul>
            <li>
              <router-link to="/sales">Vendas</router-link>
            </li>
            <li>
              <router-link to="/home">Visão geral</router-link>
            </li>
          </ul>
        </nav>
      </div>
      <div class="header-actions">
        <router-link class="btn btn-ghost btn-sm" to="/login">Entrar</router-link>
        <router-link v-if="auth.allowSignup" class="btn btn-primary btn-sm" to="/signin">
          Criar conta
        </router-link>
      </div>
    </div>
  </header>
</template>