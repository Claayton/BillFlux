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
const editing = ref(null)
const form = ref({})

const COLORS = [
  { value: '', label: 'Sem cor' },
  { value: '#6366F1', label: 'Índigo' },
  { value: '#10B981', label: 'Verde' },
  { value: '#F59E0B', label: 'Âmbar' },
  { value: '#EF4444', label: 'Vermelho' },
  { value: '#3B82F6', label: 'Azul' },
  { value: '#8B5CF6', label: 'Roxo' },
]

function toggleMenu(id) {
  openMenu.value = openMenu.value === id ? null : id
}

function closeMenus() {
  openMenu.value = null
}

function parentOptions(currentType) {
  const sections = data.value?.sections || []
  const currentSection = sections.find((s) => s.type === currentType)
  return currentSection?.groups || []
}

function openNew() {
  editing.value = null
  form.value = { name: '', type: 'despesa', parent_id: '', color: '' }
  showModal.value = true
}

function openEdit(account) {
  editing.value = account
  form.value = {
    name: account.name,
    type: account.type,
    parent_id: account.parent_id ? String(account.parent_id) : '',
    color: account.color || '',
  }
  showModal.value = true
}

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/accounts')
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.value.name) {
    ElMessage.warning('Informe o nome da categoria.')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: form.value.name,
      type: form.value.type,
      parent_id: form.value.parent_id || null,
      color: form.value.color || null,
    }
    if (editing.value) {
      data.value = await api.put(`/accounts/${editing.value.id}`, payload)
    } else {
      data.value = await api.post('/accounts', payload)
    }
    showModal.value = false
    ElMessage.success(editing.value ? 'Categoria atualizada!' : 'Categoria criada!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function removeAccount(account) {
  if (!window.confirm(`Excluir a categoria "${account.name}"?`)) return
  try {
    data.value = await api.del(`/accounts/${account.id}`)
    ElMessage.success('Categoria excluída.')
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
          <h1 class="page-title">Plano de contas</h1>
          <p class="page-subtitle">Organize receitas e despesas em categorias para enxergar seu resultado.</p>
        </div>
        <button type="button" class="btn btn-primary" @click="openNew">
          <i class="fas fa-plus"></i> Nova categoria
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <section v-for="section in data.sections" :key="section.type" class="account-section">
          <div class="account-section-head">
            <span class="account-type-dot" :class="section.type === 'receita' ? 'is-receita' : 'is-despesa'"></span>
            <h2>{{ section.label }}</h2>
          </div>

          <div v-if="section.groups.length" class="account-card">
            <template v-for="group in section.groups" :key="group.account.id">
              <div class="account-item">
                <div class="account-item-main">
                  <span class="account-dot" :style="group.account.color ? { background: group.account.color } : {}"></span>
                  <span class="account-name">{{ group.account.name }}</span>
                </div>
                <div class="dropdown">
                  <button type="button" class="icon-btn" aria-haspopup="true" aria-expanded="false" aria-label="Ações da categoria" @click.stop="toggleMenu(group.account.id)">
                    <i class="fas fa-ellipsis-h"></i>
                  </button>
                  <div class="dropdown-panel" v-show="openMenu === group.account.id">
                    <button type="button" class="dropdown-item" @click="openEdit(group.account)">
                      <i class="fas fa-pen"></i> Editar
                    </button>
                    <button type="button" class="dropdown-item is-danger" @click="removeAccount(group.account)">
                      <i class="fas fa-trash"></i> Excluir
                    </button>
                  </div>
                </div>
              </div>

              <div v-for="child in group.children" :key="child.id" class="account-item is-child">
                <div class="account-item-main">
                  <span class="account-dot" :style="child.color ? { background: child.color } : {}"></span>
                  <span class="account-name">{{ child.name }}</span>
                  <span class="account-tag">{{ child.type === 'receita' ? 'Receita' : 'Despesa' }}</span>
                </div>
                <div class="dropdown">
                  <button type="button" class="icon-btn" aria-haspopup="true" aria-expanded="false" aria-label="Ações da categoria" @click.stop="toggleMenu(child.id)">
                    <i class="fas fa-ellipsis-h"></i>
                  </button>
                  <div class="dropdown-panel" v-show="openMenu === child.id">
                    <button type="button" class="dropdown-item" @click="openEdit(child)">
                      <i class="fas fa-pen"></i> Editar
                    </button>
                    <button type="button" class="dropdown-item is-danger" @click="removeAccount(child)">
                      <i class="fas fa-trash"></i> Excluir
                    </button>
                  </div>
                </div>
              </div>
            </template>
          </div>
          <div v-else class="account-card account-empty">
            <i class="fas fa-folder-open"></i>
            <span>Nenhuma categoria de {{ section.label.toLowerCase() }} criada ainda.</span>
          </div>
        </section>

        <p class="account-hint">
          <i class="fas fa-info-circle"></i>
          Categorias em uso (com contas vinculadas) não podem ser excluídas.
        </p>
      </template>
    </div>

    <div class="modal" :class="{ 'is-open': showModal }">
      <div class="modal-content modal-content-sm">
        <div class="modal-header">
          <h2>{{ editing ? 'Editar categoria' : 'Nova categoria' }}</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="showModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="submit">
          <div class="form-field">
            <label for="account_name">Nome da categoria</label>
            <input id="account_name" v-model="form.name" type="text" placeholder="Ex: Energia de agosto" required />
          </div>

          <div class="form-grid">
            <div class="form-field">
              <label for="account_type">Tipo</label>
              <select id="account_type" v-model="form.type" required>
                <option value="receita">Receita</option>
                <option value="despesa">Despesa</option>
              </select>
            </div>
            <div class="form-field">
              <label for="account_color">Cor (opcional)</label>
              <select id="account_color" v-model="form.color">
                <option v-for="c in COLORS" :key="c.value" :value="c.value">{{ c.label }}</option>
              </select>
            </div>
          </div>

          <div class="form-field">
            <label for="account_parent">Subcategoria de (opcional)</label>
            <select id="account_parent" v-model="form.parent_id">
              <option value="">— Categoria principal —</option>
              <optgroup :label="section.label" v-for="section in data?.sections || []" :key="section.type">
                <option v-for="group in section.groups" :key="group.account.id" :value="String(group.account.id)">
                  {{ group.account.name }}
                </option>
              </optgroup>
            </select>
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
  </AppShell>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}
</style>