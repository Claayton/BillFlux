<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { normalizeForSearch } from '@/utils/normalize'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const data = ref(null)
const loading = ref(false)
const saving = ref(false)
const search = ref('')
const statusFilter = ref('todos')
const openMenuId = ref(null)
const menuPos = ref({ top: 0, left: 0, up: false })

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
  let list = data.value.suppliers
  if (statusFilter.value !== 'todos') {
    const wantActive = statusFilter.value === 'ativos'
    list = list.filter((s) => Boolean(s.active) === wantActive)
  }
  const q = normalizeForSearch(search.value)
  if (!q) return list
  return list.filter((s) =>
    normalizeForSearch(s.name).includes(q) ||
    normalizeForSearch(s.cnpj || '').includes(q) ||
    normalizeForSearch(s.phone || '').includes(q)
  )
})

const menuSupplier = computed(() =>
  (data.value?.suppliers || []).find((s) => s.id === openMenuId.value) || null
)

/** Menu flutuante (teleport p/ body): escolhe abrir p/ baixo ou p/ cima
 *  conforme o espaço visível, sem ser cortado pelo card/tabela. */
function toggleMenu(supplier, event) {
  if (openMenuId.value === supplier.id) {
    closeMenu()
    return
  }
  const rect = event?.currentTarget?.getBoundingClientRect()
  let up = false
  let top = 0
  let left = 0
  if (rect) {
    const PANEL_W = 200
    const PANEL_H = 170
    up = window.innerHeight - rect.bottom < PANEL_H + 12 && rect.top > PANEL_H + 12
    top = up ? rect.top - PANEL_H - 6 : rect.bottom + 6
    left = Math.max(8, Math.min(rect.right - PANEL_W, window.innerWidth - PANEL_W - 8))
  }
  menuPos.value = { top, left, up }
  openMenuId.value = supplier.id
}

function closeMenu() {
  openMenuId.value = null
}

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

function onKeydown(event) {
  if (event.key === 'Escape') closeMenu()
}

onMounted(() => {
  load()
  document.addEventListener('keydown', onKeydown)
  window.addEventListener('scroll', closeMenu, true)
  window.addEventListener('resize', closeMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  window.removeEventListener('scroll', closeMenu, true)
  window.removeEventListener('resize', closeMenu)
})
</script>

<template>
  <AppShell>
    <div class="dashboard suppliers-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">Fornecedores</h1>
          <p class="page-subtitle">Cadastro de fornecedores do seu comércio.</p>
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
              placeholder="Buscar por nome, CNPJ ou telefone..."
              aria-label="Buscar fornecedores"
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
          <select
            v-model="statusFilter"
            class="toolbar-select toolbar-select-status"
            aria-label="Filtrar por status"
          >
            <option value="todos">Todos os status</option>
            <option value="ativos">Ativos</option>
            <option value="inativos">Inativos</option>
          </select>
          <button type="button" class="btn-brand" @click="openNew">
            <i class="fas fa-plus"></i> Novo fornecedor
          </button>
        </div>
        <div
          v-if="openMenuId !== null"
          class="popover-overlay"
          @click="closeMenu()"
        ></div>

        <div class="table-card">
          <div class="table-container">
            <table class="data-table suppliers-table">
              <thead>
                <tr>
                  <th>Fornecedor</th>
                  <th class="col-cnpj">CNPJ</th>
                  <th class="col-tel">Telefone</th>
                  <th class="col-contato">Contato</th>
                  <th class="col-cidade">Cidade</th>
                  <th class="col-status">Status</th>
                  <th class="th-actions"><span class="sr-only">Ações</span></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="s in filtered"
                  :key="s.id"
                  :class="{ 'is-inactive': !s.active }"
                >
                  <td>
                    <span class="cell-title" :title="s.name">{{ s.name }}</span>
                    <span v-if="s.email" class="cell-sub">{{ s.email }}</span>
                  </td>
                  <td class="col-cnpj nowrap">{{ fmtCnpj(s.cnpj) }}</td>
                  <td class="col-tel nowrap">{{ fmtPhone(s.phone) }}</td>
                  <td class="col-contato"><span class="cell-ellipsis">{{ s.contact || '—' }}</span></td>
                  <td class="col-cidade"><span class="cell-ellipsis">{{ s.city || '—' }}</span></td>
                  <td class="col-status">
                    <span class="status-badge" :class="s.active ? 'is-ok' : 'is-off'">
                      {{ s.active ? 'Ativo' : 'Inativo' }}
                    </span>
                  </td>
                  <td class="cell-actions" @click.stop>
                    <div class="row-menu">
                      <button
                        type="button"
                        class="icon-btn"
                        title="Ações"
                        :aria-label="`Ações de ${s.name}`"
                        :aria-expanded="openMenuId === s.id ? 'true' : 'false'"
                        @click="toggleMenu(s, $event)"
                      >
                        <i class="fas fa-ellipsis-v"></i>
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="!filtered.length" class="empty-row">
                  <td colspan="7" class="empty-state">
                    <i class="fas fa-truck"></i>
                    <h3>{{ search || statusFilter !== 'todos' ? 'Nenhum fornecedor encontrado' : 'Nenhum fornecedor cadastrado' }}</h3>
                    <p>{{ search || statusFilter !== 'todos' ? 'Tente alterar os filtros ou buscar outro termo.' : 'Cadastre o primeiro fornecedor.' }}</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>

    <!-- Modal Novo/Editar -->
    <Teleport to="body">
      <div
        v-if="menuSupplier"
        class="row-menu-panel menu-float"
        role="menu"
        :style="{ top: menuPos.top + 'px', left: menuPos.left + 'px' }"
      >
        <button type="button" role="menuitem" @click="openEdit(menuSupplier); closeMenu()">
          <i class="fas fa-pen"></i> Editar
        </button>
        <button type="button" role="menuitem" @click="toggleActive(menuSupplier); closeMenu()">
          <i class="fas" :class="menuSupplier.active ? 'fa-toggle-off' : 'fa-toggle-on'"></i>
          {{ menuSupplier.active ? 'Desativar' : 'Ativar' }}
        </button>
        <button type="button" role="menuitem" class="is-danger" @click="deleteTarget = menuSupplier; closeMenu()">
          <i class="fas fa-trash"></i> Excluir
        </button>
      </div>
    </Teleport>

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
      confirm-label="Excluir"
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
.products-toolbar .toolbar-select-status {
  width: 180px;
}

/* Tabela com layout fixo: Fornecedor flexível, demais compactas */
.suppliers-table {
  table-layout: fixed;
}
.suppliers-table tbody td {
  padding: 10px 16px;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* Ações: respiro menor para o botão ⋮ (36px) caber sem ellipsis fantasma */
.suppliers-table .cell-actions {
  padding-left: 8px;
  padding-right: 8px;
}

/* Menu flutuante via Teleport: fixo na viewport, acima de tudo */
.menu-float {
  position: fixed;
  top: auto;
  right: auto;
  bottom: auto;
  z-index: 1200;
}
.suppliers-table .col-cnpj {
  width: 188px;
}
.suppliers-table .col-tel {
  width: 176px;
}
.suppliers-table .col-contato {
  width: 118px;
}
.suppliers-table .col-cidade {
  width: 110px;
}
.suppliers-table .col-status {
  width: 98px;
}
.suppliers-table tbody td {
  min-width: 0;
}
.suppliers-table .cell-title {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.cell-ellipsis {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.nowrap {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.suppliers-table tbody tr:hover td {
  background: var(--surface-hover);
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
  color: var(--text);
  margin-bottom: 6px;
}
.form-field input {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--brand-radius-sm);
  background: var(--surface);
  color: var(--text);
  font-size: 14px;
  transition: border-color 150ms ease, box-shadow 150ms ease;
}
.form-field input::placeholder {
  color: var(--text-muted);
}
.form-field input:hover {
  border-color: var(--border-strong);
}
.form-field input:focus {
  outline: none;
  border-color: var(--primary);
  box-shadow: var(--brand-input-ring);
}
.flex-1 { flex: 1; }
.flex-2 { flex: 2; }

@media (max-width: 900px) {
  .suppliers-table .col-cidade {
    display: none;
  }
}
@media (max-width: 640px) {
  .suppliers-table .col-contato {
    display: none;
  }
  .products-toolbar .toolbar-select-status {
    flex: 1 1 45%;
    width: auto;
    min-width: 0;
  }
}
</style>
