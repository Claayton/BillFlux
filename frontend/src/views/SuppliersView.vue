<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { normalizeForSearch } from '@/utils/normalize'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const data = ref(null)
const loading = ref(false)
const saving = ref(false)
const search = ref('')

const showModal = ref(false)
const editing = ref(null)
const form = ref(emptyForm())

const deleteTarget = ref(null)

function emptyForm() {
  return {
    name: '',
    cnpj: '',
    phone: '',
    email: '',
    contact: '',
    address: '',
    neighborhood: '',
    city: '',
    state: '',
    obs: '',
  }
}

const filtered = computed(() => {
  if (!data.value) return []
  const q = normalizeForSearch(search.value)
  if (!q) return data.value.suppliers
  return data.value.suppliers.filter((s) =>
    normalizeForSearch(s.name).includes(q) ||
    normalizeForSearch(s.cnpj || '').includes(q) ||
    normalizeForSearch(s.phone || '').includes(q)
  )
})

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/suppliers')
  } finally {
    loading.value = false
  }
}

function openNew() {
  editing.value = null
  form.value = emptyForm()
  showModal.value = true
}

function openEdit(supplier) {
  editing.value = supplier
  form.value = {
    name: supplier.name,
    cnpj: supplier.cnpj,
    phone: supplier.phone,
    email: supplier.email,
    contact: supplier.contact,
    address: supplier.address,
    neighborhood: supplier.neighborhood,
    city: supplier.city,
    state: supplier.state,
    obs: supplier.obs,
  }
  showModal.value = true
}

async function saveSupplier() {
  if (!form.value.name.trim()) {
    ElMessage.warning('Informe o nome do fornecedor.')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      data.value = await api.put(`/suppliers/${editing.value.id}`, form.value)
      ElMessage.success('Fornecedor atualizado!')
    } else {
      data.value = await api.post('/suppliers', form.value)
      ElMessage.success('Fornecedor cadastrado!')
    }
    showModal.value = false
    form.value = emptyForm()
    editing.value = null
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function toggleActive(supplier) {
  try {
    data.value = await api.post(`/suppliers/${supplier.id}/toggle`)
    ElMessage.success(supplier.active ? 'Fornecedor desativado.' : 'Fornecedor ativado!')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  try {
    data.value = await api.del(`/suppliers/${deleteTarget.value.id}`)
    ElMessage.success('Fornecedor excluído.')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    deleteTarget.value = null
  }
}

function fmtCnpj(cnpj) {
  if (!cnpj) return '—'
  const d = cnpj.replace(/\D/g, '')
  if (d.length === 14) {
    return d.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5')
  }
  return cnpj
}

function fmtPhone(phone) {
  if (!phone) return '—'
  const d = phone.replace(/\D/g, '')
  if (d.length === 11) {
    return d.replace(/(\d{2})(\d{5})(\d{4})/, '($1) $2-$3')
  }
  if (d.length === 10) {
    return d.replace(/(\d{2})(\d{4})(\d{4})/, '($1) $2-$3')
  }
  return phone
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
          <h1 class="page-title">Fornecedores</h1>
          <p class="page-subtitle">Cadastro de fornecedores do seu comércio.</p>
        </div>
        <button type="button" class="btn btn-primary" @click="openNew">
          <i class="fas fa-plus"></i> Novo fornecedor
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="search-bar">
          <i class="fas fa-search"></i>
          <input
            v-model="search"
            type="text"
            placeholder="Buscar por nome, CNPJ ou telefone…"
          />
        </div>

        <div class="table-card">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>CNPJ</th>
                  <th>Telefone</th>
                  <th>Contato</th>
                  <th>Cidade</th>
                  <th>Status</th>
                  <th class="th-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="s in filtered"
                  :key="s.id"
                  :class="{ 'is-inactive': !s.active }"
                  @click="openEdit(s)"
                  style="cursor: pointer"
                >
                  <td>
                    <span class="cell-title">{{ s.name }}</span>
                    <span v-if="s.email" class="cell-sub">{{ s.email }}</span>
                  </td>
                  <td>{{ fmtCnpj(s.cnpj) }}</td>
                  <td>{{ fmtPhone(s.phone) }}</td>
                  <td>{{ s.contact || '—' }}</td>
                  <td>{{ s.city || '—' }}</td>
                  <td>
                    <span class="status-badge" :class="s.active ? 'is-active' : 'is-inactive'">
                      {{ s.active ? 'Ativo' : 'Inativo' }}
                    </span>
                  </td>
                  <td class="cell-actions" @click.stop>
                    <button
                      type="button"
                      class="icon-btn"
                      :title="s.active ? 'Desativar' : 'Ativar'"
                      @click="toggleActive(s)"
                    >
                      <i class="fas" :class="s.active ? 'fa-toggle-on' : 'fa-toggle-off'"></i>
                    </button>
                    <button
                      type="button"
                      class="icon-btn"
                      title="Excluir"
                      @click="deleteTarget = s"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </td>
                </tr>
                <tr v-if="!filtered.length" class="empty-row">
                  <td colspan="7" class="empty-state">
                    <i class="fas fa-truck"></i>
                    <h3>{{ search ? 'Nenhum fornecedor encontrado' : 'Nenhum fornecedor cadastrado' }}</h3>
                    <p>{{ search ? 'Tente outro termo de busca.' : 'Cadastre o primeiro fornecedor.' }}</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>

    <!-- Modal Novo/Editar -->
    <div class="modal" :class="{ 'is-open': showModal }">
      <div class="modal-content modal-content-md">
        <div class="modal-header">
          <h2>{{ editing ? 'Editar fornecedor' : 'Novo fornecedor' }}</h2>
          <button type="button" class="modal-close" @click="showModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="saveSupplier">
          <div class="form-row">
            <div class="form-field flex-2">
              <label>Nome *</label>
              <input v-model="form.name" type="text" placeholder="Razão social ou nome" required />
            </div>
            <div class="form-field flex-1">
              <label>CNPJ</label>
              <input v-model="form.cnpj" type="text" placeholder="00.000.000/0000-00" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-field flex-1">
              <label>Telefone</label>
              <input v-model="form.phone" type="text" placeholder="(00) 00000-0000" />
            </div>
            <div class="form-field flex-1">
              <label>Email</label>
              <input v-model="form.email" type="email" placeholder="email@exemplo.com" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-field flex-1">
              <label>Pessoa de contato</label>
              <input v-model="form.contact" type="text" placeholder="Nome do representante" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-field flex-2">
              <label>Endereço</label>
              <input v-model="form.address" type="text" placeholder="Rua, Avenida…" />
            </div>
            <div class="form-field flex-1">
              <label>Bairro</label>
              <input v-model="form.neighborhood" type="text" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-field flex-1">
              <label>Cidade</label>
              <input v-model="form.city" type="text" />
            </div>
            <div class="form-field flex-1">
              <label>UF</label>
              <input v-model="form.state" type="text" maxlength="2" placeholder="SP" style="text-transform:uppercase" />
            </div>
          </div>
          <div class="form-field">
            <label>Observações</label>
            <input v-model="form.obs" type="text" placeholder="Anotações sobre o fornecedor…" />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-ghost" @click="showModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Salvar' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog
      v-if="deleteTarget"
      :title="'Excluir fornecedor'"
      :message="'Tem certeza que deseja excluir ' + deleteTarget.name + '?'"
      confirm-text="Excluir"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </AppShell>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}
.search-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  background: var(--surface, #fff);
  border: 1px solid var(--border, #d1d5db);
  border-radius: 8px;
  padding: 8px 12px;
  margin-bottom: 16px;
}
.search-bar i {
  color: var(--text-muted, #999);
}
.search-bar input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 14px;
  background: transparent;
}
.cell-sub {
  display: block;
  font-size: 12px;
  color: var(--text-muted, #999);
  margin-top: 2px;
}
.form-row {
  display: flex;
  gap: 12px;
}
.form-field {
  margin-bottom: 4px;
}
.form-field label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary, #666);
  margin-bottom: 4px;
}
.form-field input {
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--border, #d1d5db);
  border-radius: 6px;
  font-size: 14px;
}
.form-field input:focus {
  outline: none;
  border-color: var(--primary, #2563eb);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}
.flex-1 { flex: 1; }
.flex-2 { flex: 2; }
</style>
