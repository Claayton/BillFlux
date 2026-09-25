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
const categoryName = ref('')
const search = ref('')

const confirmTarget = ref(null)

const filteredCategories = computed(() => {
  const list = data.value?.categories || []
  const q = normalizeForSearch(search.value.trim())
  if (!q) return list
  return list.filter((c) => normalizeForSearch(c.name).includes(q))
})

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
    <div class="dashboard categories-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">Categorias</h1>
          <p class="page-subtitle">Organize os produtos do seu comércio.</p>
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
              placeholder="Buscar categoria..."
              aria-label="Buscar categorias"
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
            <i class="fas fa-plus"></i> Nova categoria
          </button>
        </div>

        <div class="table-card">
          <div class="table-container">
            <table class="data-table categories-table">
              <thead>
                <tr>
                  <th>Categoria</th>
                  <th class="col-count">Produtos</th>
                  <th class="col-status">Status</th>
                  <th class="th-actions"><span class="sr-only">Ações</span></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="cat in filteredCategories"
                  :key="cat.id"
                  :class="{ 'is-inactive': !cat.active }"
                >
                  <td>
                    <span class="cell-title" :title="cat.name">{{ cat.name }}</span>
                    <span v-if="!cat.active" class="cell-sub">não aparece no PDV</span>
                  </td>
                  <td class="cell-number">{{ cat.product_count }}</td>
                  <td class="col-status">
                    <span class="status-badge" :class="cat.active ? 'is-ok' : 'is-off'">
                      {{ cat.active ? 'Ativa' : 'Inativa' }}
                    </span>
                  </td>
                  <td class="cell-actions">
                    <div class="dropdown">
                      <button
                        type="button"
                        class="icon-btn row-menu-btn"
                        aria-haspopup="true"
                        :aria-expanded="openMenu === cat.id ? 'true' : 'false'"
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
                <tr v-if="!filteredCategories.length" class="empty-row">
                  <td colspan="4" class="empty-state">
                    <i class="fas fa-tags"></i>
                    <h3>{{ search ? 'Nenhuma categoria encontrada' : 'Nenhuma categoria' }}</h3>
                    <p>{{ search ? 'Tente outro termo de busca.' : 'Crie categorias para organizar seus produtos.' }}</p>
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

/* Tabela com layout fixo: Categoria flexível, demais compactas */
.categories-table {
  table-layout: fixed;
}
.categories-table .col-count {
  width: 120px;
}
.categories-table .col-status {
  width: 130px;
}
.categories-table tbody td {
  min-width: 0;
  padding: 10px 16px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.categories-table .cell-title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.categories-table .cell-number {
  font-variant-numeric: tabular-nums;
}
.categories-table .cell-actions {
  padding-left: 8px;
  padding-right: 8px;
  overflow: visible;
}
.categories-table tbody tr:hover td {
  background: var(--surface-hover);
}
</style>
