<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl } from '@/utils/format'
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

const historyTarget = ref(null)
const historyData = ref(null)
const historyLoading = ref(false)

function emptyForm() {
  return {
    name: '',
    cpf_cnpj: '',
    phone: '',
    email: '',
    address: '',
    number: '',
    neighborhood: '',
    city: '',
    state: '',
    complement: '',
    zip_code: '',
    obs: '',
  }
}

const filtered = computed(() => {
  if (!data.value) return []
  const q = search.value.toLowerCase()
  if (!q) return data.value.customers
  return data.value.customers.filter((c) =>
    c.name.toLowerCase().includes(q) ||
    c.cpf_cnpj.includes(q) ||
    c.phone.includes(q) ||
    c.email.toLowerCase().includes(q)
  )
})

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/customers')
  } finally {
    loading.value = false
  }
}

function openNew() {
  editing.value = null
  form.value = emptyForm()
  showModal.value = true
}

function openEdit(customer) {
  editing.value = customer
  form.value = {
    name: customer.name,
    cpf_cnpj: customer.cpf_cnpj,
    phone: customer.phone,
    email: customer.email,
    address: customer.address,
    number: customer.number,
    neighborhood: customer.neighborhood,
    city: customer.city,
    state: customer.state,
    complement: customer.complement,
    zip_code: customer.zip_code,
    obs: customer.obs,
  }
  showModal.value = true
}

async function saveCustomer() {
  if (!form.value.name.trim()) {
    ElMessage.warning('Informe o nome do cliente.')
    return
  }
  saving.value = true
  try {
    if (editing.value) {
      data.value = await api.put(`/customers/${editing.value.id}`, form.value)
      ElMessage.success('Cliente atualizado!')
    } else {
      data.value = await api.post('/customers', form.value)
      ElMessage.success('Cliente cadastrado!')
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

async function toggleActive(customer) {
  try {
    data.value = await api.post(`/customers/${customer.id}/toggle`)
    ElMessage.success(customer.active ? 'Cliente desativado.' : 'Cliente ativado!')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  try {
    data.value = await api.del(`/customers/${deleteTarget.value.id}`)
    ElMessage.success('Cliente excluído.')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    deleteTarget.value = null
  }
}

function fmtDoc(cpf_cnpj) {
  if (!cpf_cnpj) return '—'
  const d = cpf_cnpj.replace(/\D/g, '')
  if (d.length === 11) {
    return d.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4')
  }
  if (d.length === 14) {
    return d.replace(/(\d{2})(\d{3})(\d{3})(\d{4})(\d{2})/, '$1.$2.$3/$4-$5')
  }
  return cpf_cnpj
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

function fmtDate(iso) {
  if (!iso) return '—'
  return iso.replace('T', ' ').slice(0, 16)
}

async function openHistory(customer) {
  historyTarget.value = customer
  historyData.value = null
  historyLoading.value = true
  try {
    historyData.value = await api.get(`/customers/${customer.id}/orders`)
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    historyLoading.value = false
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
          <h1 class="page-title">Clientes</h1>
          <p class="page-subtitle">Cadastro de clientes do seu comércio.</p>
        </div>
        <button type="button" class="btn btn-primary" @click="openNew">
          <i class="fas fa-plus"></i> Novo cliente
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="search-bar">
          <i class="fas fa-search"></i>
          <input
            v-model="search"
            type="text"
            placeholder="Buscar por nome, CPF/CNPJ, telefone ou email…"
          />
        </div>

        <div class="table-card">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Nome</th>
                  <th>CPF/CNPJ</th>
                  <th>Telefone</th>
                  <th>Cidade</th>
                  <th>Status</th>
                  <th class="th-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="c in filtered"
                  :key="c.id"
                  :class="{ 'is-inactive': !c.active }"
                  @click="openEdit(c)"
                  style="cursor: pointer"
                >
                  <td>
                    <span class="cell-title">{{ c.name }}</span>
                    <span v-if="c.email" class="cell-sub">{{ c.email }}</span>
                  </td>
                  <td>{{ fmtDoc(c.cpf_cnpj) }}</td>
                  <td>{{ fmtPhone(c.phone) }}</td>
                  <td>{{ c.city || '—' }}</td>
                  <td>
                    <span class="status-badge" :class="c.active ? 'is-active' : 'is-inactive'">
                      {{ c.active ? 'Ativo' : 'Inativo' }}
                    </span>
                  </td>
                  <td class="cell-actions" @click.stop>
                    <button
                      type="button"
                      class="icon-btn"
                      title="Histórico de compras"
                      @click="openHistory(c)"
                    >
                      <i class="fas fa-receipt"></i>
                    </button>
                    <button
                      type="button"
                      class="icon-btn"
                      :title="c.active ? 'Desativar' : 'Ativar'"
                      @click="toggleActive(c)"
                    >
                      <i class="fas" :class="c.active ? 'fa-toggle-on' : 'fa-toggle-off'"></i>
                    </button>
                    <button
                      type="button"
                      class="icon-btn"
                      title="Excluir"
                      @click="deleteTarget = c"
                    >
                      <i class="fas fa-trash"></i>
                    </button>
                  </td>
                </tr>
                <tr v-if="!filtered.length" class="empty-row">
                  <td colspan="6" class="empty-state">
                    <i class="fas fa-users"></i>
                    <h3>{{ search ? 'Nenhum cliente encontrado' : 'Nenhum cliente cadastrado' }}</h3>
                    <p>{{ search ? 'Tente outro termo de busca.' : 'Cadastre o primeiro cliente do seu comércio.' }}</p>
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
          <h2>{{ editing ? 'Editar cliente' : 'Novo cliente' }}</h2>
          <button type="button" class="modal-close" @click="showModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="saveCustomer">
          <div class="form-row">
            <div class="form-field flex-2">
              <label>Nome *</label>
              <input v-model="form.name" type="text" placeholder="Nome completo" required />
            </div>
            <div class="form-field flex-1">
              <label>CPF/CNPJ</label>
              <input v-model="form.cpf_cnpj" type="text" placeholder="000.000.000-00" />
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
            <div class="form-field flex-2">
              <label>Endereço</label>
              <input v-model="form.address" type="text" placeholder="Rua, Avenida…" />
            </div>
            <div class="form-field flex-1">
              <label>Número</label>
              <input v-model="form.number" type="text" placeholder="Nº" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-field flex-1">
              <label>Bairro</label>
              <input v-model="form.neighborhood" type="text" />
            </div>
            <div class="form-field flex-1">
              <label>Cidade</label>
              <input v-model="form.city" type="text" />
            </div>
            <div class="form-field flex-1">
              <label>UF</label>
              <input v-model="form.state" type="text" maxlength="2" placeholder="SP" style="text-transform:uppercase" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-field flex-1">
              <label>Complemento</label>
              <input v-model="form.complement" type="text" />
            </div>
            <div class="form-field flex-1">
              <label>CEP</label>
              <input v-model="form.zip_code" type="text" placeholder="00000-000" />
            </div>
          </div>
          <div class="form-field">
            <label>Observações</label>
            <input v-model="form.obs" type="text" placeholder="Anotações sobre o cliente…" />
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
      :title="'Excluir cliente'"
      :message="'Tem certeza que deseja excluir ' + deleteTarget.name + '?'"
      confirm-text="Excluir"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />

    <!-- Modal Histórico -->
    <div class="modal" :class="{ 'is-open': historyTarget }">
      <div class="modal-content modal-content-md">
        <div class="modal-header">
          <h2>Histórico — {{ historyTarget?.name }}</h2>
          <button type="button" class="modal-close" @click="historyTarget = null">&times;</button>
        </div>
        <div v-if="historyLoading" class="muted">Carregando…</div>
        <template v-else-if="historyData">
          <div class="history-stats">
            <div class="history-stat">
              <span class="label">Pedidos</span>
              <span class="value">{{ historyData.order_count }}</span>
            </div>
            <div class="history-stat">
              <span class="label">Total gasto</span>
              <span class="value">{{ brl(historyData.total_spent) }}</span>
            </div>
          </div>
          <div v-if="historyData.orders.length" class="table-container" style="max-height:300px;overflow-y:auto">
            <table class="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Data</th>
                  <th>Total</th>
                  <th>Pagamento</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="o in historyData.orders" :key="o.order_id" :class="{ 'is-inactive': o.cancelled }">
                  <td>{{ o.order_id }}</td>
                  <td>{{ fmtDate(o.date) }}</td>
                  <td class="cell-amount">{{ brl(o.total) }}</td>
                  <td>{{ o.payment_method }}</td>
                  <td>
                    <span v-if="o.cancelled" class="status-badge is-inactive">Cancelado</span>
                    <span v-else class="status-badge is-active">OK</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p v-else class="muted" style="padding:12px 0">Nenhum pedido registrado.</p>
        </template>
      </div>
    </div>
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
.history-stats {
  display: flex;
  gap: 24px;
  margin-bottom: 16px;
  padding: 12px 16px;
  background: var(--surface-hover, #f9fafb);
  border-radius: 8px;
}
.history-stat .label {
  display: block;
  font-size: 12px;
  color: var(--text-muted, #999);
  margin-bottom: 2px;
}
.history-stat .value {
  font-size: 18px;
  font-weight: 700;
}
.cell-amount {
  text-align: right;
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}
</style>
