<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'

const data = ref(null)
const loading = ref(false)
const saving = ref(false)
const openMenu = ref(null)

const showModal = ref(false)
const methodName = ref('')

function toggleMenu(id) {
  openMenu.value = openMenu.value === id ? null : id
}

function closeMenus() {
  openMenu.value = null
}

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/payments')
  } finally {
    loading.value = false
  }
}

async function createMethod() {
  if (!methodName.value.trim()) {
    ElMessage.warning('Informe o nome da forma de pagamento.')
    return
  }
  saving.value = true
  try {
    data.value = await api.post('/payments', { name: methodName.value })
    showModal.value = false
    methodName.value = ''
    ElMessage.success('Forma de pagamento cadastrada!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function toggleMethod(method) {
  try {
    data.value = await api.post(`/payments/${method.id}/toggle`)
    ElMessage.success(method.active ? 'Forma desativada.' : 'Forma ativada!')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function removeMethod(method) {
  if (!window.confirm(`Excluir a forma de pagamento "${method.name}"?`)) return
  try {
    data.value = await api.del(`/payments/${method.id}`)
    ElMessage.success('Forma de pagamento excluída.')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

onMounted(() => {
  load()
  document.addEventListener('click', closeMenus)
})
</script>

<template>
  <AppShell>
    <div class="dashboard">
      <div class="page-header">
        <div>
          <h1 class="page-title">Formas de pagamento</h1>
          <p class="page-subtitle">Gerencie as formas aceitas no PDV.</p>
        </div>
        <button type="button" class="btn btn-primary" @click="showModal = true">
          <i class="fas fa-plus"></i> Nova forma
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="table-card">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Forma de pagamento</th>
                  <th>Status</th>
                  <th class="th-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="method in data.methods" :key="method.id" :class="{ 'is-inactive': !method.active }">
                  <td>
                    <span class="cell-title">{{ method.name }}</span>
                    <span v-if="!method.active" class="cell-sub">não aparece no PDV</span>
                  </td>
                  <td>
                    <span class="status-badge" :class="method.active ? 'is-active' : 'is-inactive'">
                      {{ method.active ? 'Ativa' : 'Inativa' }}
                    </span>
                  </td>
                  <td class="cell-actions">
                    <div class="dropdown">
                      <button
                        type="button"
                        class="icon-btn row-menu-btn"
                        aria-haspopup="true"
                        aria-expanded="false"
                        aria-label="Ações da forma de pagamento"
                        @click.stop="toggleMenu(method.id)"
                      >
                        <i class="fas fa-ellipsis-h"></i>
                      </button>
                      <div class="dropdown-panel" v-show="openMenu === method.id">
                        <button type="button" class="dropdown-item" @click="toggleMethod(method)">
                          <i class="fas fa-power-off"></i> {{ method.active ? 'Desativar' : 'Ativar' }}
                        </button>
                        <button type="button" class="dropdown-item is-danger" @click="removeMethod(method)">
                          <i class="fas fa-trash"></i> Excluir
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr v-if="!data.methods.length" class="empty-row">
                  <td colspan="3" class="empty-state">
                    <i class="fas fa-credit-card"></i>
                    <h3>Nenhuma forma de pagamento</h3>
                    <p>Adicione as formas aceitas no seu comércio.</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <p class="account-hint">
          <i class="fas fa-info-circle"></i>
          Formas já usadas em vendas não podem ser excluídas — apenas desativadas.
        </p>
      </template>
    </div>

    <div class="modal" :class="{ 'is-open': showModal }">
      <div class="modal-content modal-content-sm">
        <div class="modal-header">
          <h2>Nova forma de pagamento</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="showModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="createMethod">
          <div class="form-field">
            <label for="method_name">Nome</label>
            <input
              id="method_name"
              v-model="methodName"
              type="text"
              placeholder="Ex: Boleto, Vale-refeição..."
              required
            />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-ghost modal-cancel" @click="showModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Salvar forma' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </AppShell>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}
</style>