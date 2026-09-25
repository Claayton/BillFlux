import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import ptBr from 'element-plus/es/locale/lang/pt-br'
import App from './App.vue'
import router from './router'
import { setUnauthorizedHandler } from './api/client'
import { clearHadSession, hadPreviousSession, useAuthStore } from './stores/auth'
import './assets/css/brand.css'
import './assets/css/style-base.css'
import './assets/css/style-home.css'
import './assets/css/sales.css'
import './assets/css/pdv.css'
import './assets/css/bills.css'
import './assets/css/products.css'
import './assets/css/accounts.css'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: ptBr })

// Sessão expirada em qualquer chamada da API: limpa o estado e manda
// pra tela inicial (que hospeda o login) preservando a rota (sem toast
// aqui — a view que originou a chamada já exibe a mensagem amigável).
// Importante: só trata como "expirou" se houve sessão antes (usuário
// logado ou flag de login nesta aba). Boot em anônimo (401 sem nunca
// ter logado) cai aqui também e segue silenciosamente.
setUnauthorizedHandler(() => {
  const auth = useAuthStore()
  const expired = Boolean(auth.user) || hadPreviousSession()
  auth.user = null
  clearHadSession()
  if (!expired) return
  const current = router.currentRoute.value
  if (['landing', 'login', 'signin'].includes(current.name)) return
  router
    .push({ name: 'landing', query: { redirect: current.fullPath, expired: '1' } })
    .catch(() => {})
})

app.mount('#app')