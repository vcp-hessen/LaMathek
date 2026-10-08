import { VueQueryPlugin } from '@tanstack/vue-query'
import { createPinia } from 'pinia'
import { configure } from 'vee-validate'
import { createApp } from 'vue'
import App from './App.vue'
import { i18n } from './i18n'
import { router } from './router'
import './style.css'

configure({
  validateOnInput: true,
})

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.use(i18n)
app.use(VueQueryPlugin)
app.mount('#app')
