<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import { useRowMenu } from '@/composables/useRowMenu'

const { openMenu, menuPos, toggleMenu, closeMenus } = useRowMenu()

const data = ref(null)
const loading = ref(false)
const saving = ref(false)

const showModal = ref(false)
const categoryName = ref('')

const confirmTarget = ref(null)

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/categories')
  } finally {
    loading.value = false
  }
}

async function createCategory() {
  if (!categoryName.value.trim()) {
    ElMessage.warning('Informe o nome da categoria.')
    return
  }
  saving.value = true
  try {
    data.value = await api.post('/categories', { name: categoryName.value })
    showModal.value = false
    categoryName.value = ''
    ElMessage.success('Categoria cadastrada!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function toggleCategory(category) {
  try {
    data.value = await api.post(`/categories/${category.id}/toggle`)
    ElMessage.success(category.active ? 'Categoria desativada.' : 'Categoria ativada!')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function confirmRemove() {
  const category = confirmTarget.value
  confirmTarget.value = null
  if (!category) return
  try {
    data.value = await api.del(`/categories/${category.id}`)
    ElMessage.success('Categoria excluída.')
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
    <div class="dashboard">
      <div class="page-header">
        <div>
          <h1 class="page-title">Categorias</h1>
          <p class="page-subtitle">Organize os produtos do seu comércio.</p>
        </div>
        <button type="button" class="btn btn-primary" @click="showModal = true">
          <i class="fas fa-plus"></i> Nova categoria
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="table-card">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Categoria</th>
                  <th>Produtos</th>
                  <th>Status</th>
                  <th class="th-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="cat in data.categories"
                  :key="cat.id"
                  :class="{ 'is-inactive': !cat.active }"
                >
                  <td>
                    <span class="cell-title">{{ cat.name }}</span>
                    <span v-if="!cat.active" class="cell-sub">não aparece no PDV</span>
                  </td>
                  <td>{{ cat.product_count }}</td>
                  <td>
                    <span class="status-badge" :class="cat.active ? 'is-active' : 'is-inactive'">
                      {{ cat.active ? 'Ativa' : 'Inativa' }}
                    </span>
                  </td>
                  <td class="cell-actions">
                    <div class="dropdown">
                      <button
                        type="button"
                        class="icon-btn row-menu-btn"
                        aria-haspopup="true"
                        aria-expanded="false"
                        aria-label="Ações da categoria"
                        :data-menu="cat.id"
                        @click.stop="toggleMenu(cat.id)"
                      >
                        <i class="fas fa-ellipsis-h"></i>
                      </button>
                      <div
                        class="dropdown-panel"
                        v-show="openMenu === cat.id"
                        :style="{ top: menuPos.top + 'px', left: menuPos.left + 'px' }"
                      >
                        <button type="button" class="dropdown-item" @click="toggleCategory(cat)">
                          <i class="fas fa-power-off"></i> {{ cat.active ? 'Desativar' : 'Ativar' }}
                        </button>
                        <button
                          type="button"
                          class="dropdown-item is-danger"
                          :disabled="cat.product_count > 0"
                          :title="cat.product_count > 0 ? 'Remova a categoria dos produtos antes de excluir' : ''"
                          @click="confirmTarget = cat"
                        >
                          <i class="fas fa-trash"></i> Excluir
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr v-if="!data.categories.length" class="empty-row">
                  <td colspan="4" class="empty-state">
                    <i class="fas fa-tags"></i>
                    <h3>Nenhuma categoria</h3>
                    <p>Crie categorias para organizar seus produtos.</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <p class="account-hint">
          <i class="fas fa-info-circle"></i>
          Categorias com produtos vinculados não podem ser excluídas — apenas desativadas.
        </p>
      </template>
    </div>

    <div class="modal" :class="{ 'is-open': showModal }">
      <div class="modal-content modal-content-sm">
        <div class="modal-header">
          <h2>Nova categoria</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="showModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="createCategory">
          <div class="form-field">
            <label for="category_name">Nome</label>
            <input
              id="category_name"
              v-model="categoryName"
              type="text"
              placeholder="Ex: Bebidas, Higiene..."
              required
            />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-ghost modal-cancel" @click="showModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Salvar categoria' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog
      v-if="confirmTarget"
      title="Excluir categoria"
      :message="`Excluir a categoria \u201C${confirmTarget.name}\u201D?`"
      confirm-label="Excluir"
      danger
      @confirm="confirmRemove"
      @cancel="confirmTarget = null"
    />
  </AppShell>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}
</style>
