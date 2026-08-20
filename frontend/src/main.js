import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import ptBr from 'element-plus/es/locale/lang/pt-br'
import App from './App.vue'
import router from './router'
import './assets/css/style-base.css'
import './assets/css/style-home.css'
import './assets/css/sales.css'
import './assets/css/pdv.css'
import './assets/css/bills.css'
import './assets/css/products.css'
import './assets/css/accounts.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(ElementPlus, { locale: ptBr })
app.mount('#app')