<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { normalizeForSearch } from '@/utils/normalize'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useRowMenu } from '@/composables/useRowMenu'

const { openMenu, menuPos, toggleMenu, closeMenus } = useRowMenu()

const data = ref(null)
const loading = ref(false)
const saving = ref(false)

const showModal = ref(false)
const methodName = ref('')
const search = ref('')
const deleteTarget = ref(null)

const filteredMethods = computed(() => {
  const list = data.value?.methods || []
  const q = normalizeForSearch(search.value.trim())
  if (!q) return list
  return list.filter((m) => normalizeForSearch(m.name).includes(q))
})

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

function removeMethod(method) {
  deleteTarget.value = method
}

async function confirmRemove() {
  const method = deleteTarget.value
  deleteTarget.value = null
  if (!method) return
  try {
    data.value = await api.del(`/payments/${method.id}`)
    ElMessage.success('Forma de pagamento excluída.')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

onMounted(() => {
  load()
})
</script>

<template>
  <AppShell>
    <div class="dashboard payments-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">Formas de pagamento</h1>
          <p class="page-subtitle">Gerencie as formas aceitas no PDV.</p>
        </div>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="products-toolbar">
          <div class="search-box products-search-box">
            <i class="fas fa-search"></i>
            <input
              v-model="search"
              type="text"
              placeholder="Buscar forma de pagamento..."
              aria-label="Buscar formas de pagamento"
            />
            <button
              v-if="search"
              type="button"
              class="search-clear"
              aria-label="Limpar busca"
              @click="search = ''"
            >
              <i class="fas fa-times"></i>
            </button>
          </div>
          <button type="button" class="btn-brand" @click="showModal = true">
            <i class="fas fa-plus"></i> Nova forma
          </button>
        </div>

        <div class="table-card">
          <div class="table-container">
            <table class="data-table payments-table">
              <thead>
                <tr>
                  <th>Forma de pagamento</th>
                  <th class="col-status">Status</th>
                  <th class="th-actions"><span class="sr-only">Ações</span></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="method in filteredMethods" :key="method.id" :class="{ 'is-inactive': !method.active }">
                  <td>
                    <span class="cell-title" :title="method.name">{{ method.name }}</span>
                    <span v-if="!method.active" class="cell-sub">não aparece no PDV</span>
                  </td>
                  <td class="col-status">
                    <span class="status-badge" :class="method.active ? 'is-ok' : 'is-off'">
                      {{ method.active ? 'Ativa' : 'Inativa' }}
                    </span>
                  </td>
                  <td class="cell-actions">
                    <div class="dropdown">
                      <button
                        type="button"
                        class="icon-btn row-menu-btn"
                        aria-haspopup="true"
                        :aria-expanded="openMenu === method.id ? 'true' : 'false'"
                        aria-label="Ações da forma de pagamento"
                        :data-menu="method.id"
                        @click.stop="toggleMenu(method.id)"
                      >
                        <i class="fas fa-ellipsis-h"></i>
                      </button>
                      <div
                        class="dropdown-panel"
                        v-show="openMenu === method.id"
                        :style="{ top: menuPos.top + 'px', left: menuPos.left + 'px' }"
                      >
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
                <tr v-if="!filteredMethods.length" class="empty-row">
                  <td colspan="3" class="empty-state">
                    <i class="fas fa-credit-card"></i>
                    <h3>{{ search ? 'Nenhuma forma encontrada' : 'Nenhuma forma de pagamento' }}</h3>
                    <p>{{ search ? 'Tente outro termo de busca.' : 'Adicione as formas aceitas no seu comércio.' }}</p>
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
    <ConfirmDialog
      v-if="deleteTarget"
      title="Excluir forma de pagamento"
      :message="`Excluir a forma de pagamento \u201C${deleteTarget.name}\u201D?`"
      confirm-label="Excluir"
      danger
      @confirm="confirmRemove"
      @cancel="deleteTarget = null"
    />
  </AppShell>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}

/* Tabela com layout fixo: Nome flexível, demais compactas */
.payments-table {
  table-layout: fixed;
}
.payments-table .col-status {
  width: 130px;
}
.payments-table tbody td {
  min-width: 0;
  padding: 10px 16px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.payments-table .cell-title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.payments-table .cell-actions {
  padding-left: 8px;
  padding-right: 8px;
  overflow: visible;
}
.payments-table tbody tr:hover td {
  background: var(--surface-hover);
}
</style>