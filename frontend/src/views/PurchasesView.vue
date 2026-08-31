<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const purchases = ref([])
const loading = ref(false)
const saving = ref(false)
const search = ref('')
const statusFilter = ref('')
const showModal = ref(false)
const editing = ref(null)
const form = ref(emptyForm())
const items = ref([])
const deleteTarget = ref(null)
const detailModal = ref(false)
const detailPurchase = ref(null)
const detailItems = ref([])
const nfModal = ref(false)
const nfXml = ref('')
const launchTarget = ref(null)
const launchItems = ref([])
const launchDate = ref('')
const launchCreateBill = ref(true)
const launchSearchIdx = ref(null)
const launchSearchQuery = ref('')
const launchSearchResults = ref([])
const launchSearching = ref(false)
const quickProductModal = ref(false)
const quickProductItemIdx = ref(null)
const quickProduct = ref({ name: '', price: '', cost: '', barcode: '', category_id: null })
const allProducts = ref([])
const suppliers = ref([])
const quickSupplierModal = ref(false)
const quickSupplier = ref({ name: '', cnpj: '', phone: '', email: '' })

function emptyForm() {
  return {
    nf_number: '', nf_serie: '', nf_chave: '', nf_modelo: '',
    supplier_id: null, freight: '', discount: '', due_date: '', obs: '',
  }
}

function emptyItem() {
  return { product_id: null, product_name: '', barcode: '', quantity: 1, unit_cost: '' }
}

const statusLabel = { rascunho: 'Rascunho', confirmada: 'Confirmada', cancelada: 'Cancelada' }
const statusClass = { rascunho: 'is-draft', confirmada: 'is-active', cancelada: 'is-inactive' }

const filtered = computed(() => {
  let list = purchases.value
  const q = search.value.toLowerCase()
  if (q) {
    list = list.filter(p =>
      (p.nf_number || '').toLowerCase().includes(q) ||
      (p.nf_chave || '').includes(q) ||
      (p.supplier_name || '').toLowerCase().includes(q) ||
      (p.obs || '').toLowerCase().includes(q)
    )
  }
  if (statusFilter.value) {
    list = list.filter(p => p.status === statusFilter.value)
  }
  return list
})

async function load() {
  loading.value = true
  try {
    const data = await api.get('/purchases')
    purchases.value = data.purchases
  } finally {
    loading.value = false
  }
}

async function loadProducts() {
  try {
    const data = await api.get('/products')
    allProducts.value = data.products || []
  } catch { /* ignore */ }
}

async function loadSuppliers() {
  try {
    const data = await api.get('/suppliers')
    suppliers.value = (data.suppliers || []).filter(s => s.active)
  } catch { /* ignore */ }
}

function openNew() {
  editing.value = null
  form.value = emptyForm()
  items.value = [emptyItem()]
  showModal.value = true
}

async function openEdit(purchase) {
  editing.value = purchase
  try {
    const data = await api.get(`/purchases/${purchase.id}`)
    form.value = {
      nf_number: data.purchase.nf_number || '',
      nf_serie: data.purchase.nf_serie || '',
      nf_chave: data.purchase.nf_chave || '',
      nf_modelo: data.purchase.nf_modelo || '',
      supplier_id: data.purchase.supplier_id || null,
      freight: data.purchase.freight || '',
      discount: data.purchase.discount || '',
      due_date: data.purchase.due_date || '',
      obs: data.purchase.obs || '',
    }
    items.value = (data.items || []).map(i => ({
      product_id: i.product_id,
      product_name: i.product_name || '',
      barcode: i.barcode || '',
      quantity: i.quantity,
      unit_cost: i.unit_cost,
    }))
    if (!items.value.length) items.value = [emptyItem()]
    showModal.value = true
  } catch (error) {
    ElMessage.error('Erro ao carregar compra: ' + error.message)
  }
}

async function openDetail(purchase) {
  detailPurchase.value = purchase
  const data = await api.get(`/purchases/${purchase.id}`)
  detailItems.value = data.items
  detailModal.value = true
}

async function savePurchase() {
  saving.value = true
  try {
    const payload = {
      ...form.value,
      items: items.value.filter(i => i.product_id || i.barcode || i.product_name),
    }
    if (editing.value) {
      await api.put(`/purchases/${editing.value.id}`, payload)
      ElMessage.success('Compra atualizada!')
    } else {
      await api.post('/purchases', payload)
      ElMessage.success('Compra criada!')
    }
    showModal.value = false
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

function addItem() {
  items.value.push(emptyItem())
}

function removeItem(index) {
  if (items.value.length > 1) items.value.splice(index, 1)
}

function calcItemTotal(item) {
  const qty = parseInt(item.quantity) || 0
  const cost = parseFloat(item.unit_cost) || 0
  return (qty * cost).toFixed(2)
}

function calcSubtotal() {
  return items.value.reduce((acc, i) => acc + parseFloat(calcItemTotal(i)) || 0, 0).toFixed(2)
}

function calcNetTotal() {
  const sub = parseFloat(calcSubtotal()) || 0
  const freight = parseFloat(form.value.freight) || 0
  const discount = parseFloat(form.value.discount) || 0
  return (sub + freight - discount).toFixed(2)
}

async function openNfModal() {
  nfXml.value = ''
  nfModal.value = true
}

async function importNfe() {
  if (!nfXml.value.trim()) {
    ElMessage.warning('Cole o XML da NF-e.')
    return
  }
  saving.value = true
  try {
    const res = await api.post('/purchases/nfe-import', { xml: nfXml.value.trim() })
    if (res.duplicate) {
      ElMessage.warning('NF-e já importada anteriormente.')
      nfModal.value = false
      return
    }
    ElMessage.success('NF-e importada com sucesso!')
    nfModal.value = false
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function openLaunchModal(purchase) {
  launchTarget.value = purchase
  launchDate.value = ''
  launchCreateBill.value = true
  const data = await api.get(`/purchases/${purchase.id}`)
  launchItems.value = data.items.map(item => ({
    ...item,
    product_id: item.product_id || null,
    matched: !!item.product_id,
    editing: false,
    units_per_case: 1,
  }))

  for (const li of launchItems.value) {
    if (!li.matched && li.barcode) {
      try {
        const res = await api.get(`/products/barcode/${li.barcode}`)
        if (res.product) {
          li.product_id = res.product.id
          li.product_name_existing = res.product.name
          li.existing_stock = res.product.stock_quantity
          li.existing_cost = res.product.cost
          li.matched = true
        }
      } catch { /* no match */ }
    } else if (li.matched && li.product_id) {
      try {
        const res = await api.get(`/products/${li.product_id}`)
        if (res.product) {
          li.product_name_existing = res.product.name
          li.existing_stock = res.product.stock_quantity
          li.existing_cost = res.product.cost
        }
      } catch { /* ignore */ }
    }
  }
  launchSearchIdx.value = null
}

function calcWeightedCost(item) {
  const currentQty = parseInt(item.existing_stock) || 0
  const currentCost = parseFloat(item.existing_cost) || 0
  const factor = parseInt(item.units_per_case) || 1
  const newQty = (parseInt(item.quantity) || 0) * factor
  const newCost = factor > 0 ? (parseFloat(item.unit_cost) || 0) / factor : 0
  if (currentQty > 0 && currentCost > 0 && newQty > 0 && newCost > 0) {
    return ((currentQty * currentCost) + (newQty * newCost)) / (currentQty + newQty)
  }
  return newCost
}

function openLaunchSearch(idx) {
  launchSearchIdx.value = idx
  launchSearchQuery.value = ''
  launchSearchResults.value = []
}

async function searchLaunchProduct() {
  const q = launchSearchQuery.value.trim()
  if (!q) { launchSearchResults.value = []; return }
  launchSearching.value = true
  try {
    const data = await api.get(`/products/search?q=${encodeURIComponent(q)}`)
    launchSearchResults.value = data.products || []
  } catch {
    launchSearchResults.value = []
  } finally {
    launchSearching.value = false
  }
}

function matchProduct(idx, product) {
  const li = launchItems.value[idx]
  li.product_id = product.id
  li.product_name_existing = product.name
  li.existing_stock = product.stock_quantity
  li.existing_cost = product.cost
  li.matched = true
  li.editing = false
  launchSearchIdx.value = null
}

function unmatchProduct(idx) {
  const li = launchItems.value[idx]
  li.product_id = null
  li.product_name_existing = null
  li.existing_stock = null
  li.existing_cost = null
  li.matched = false
  launchSearchIdx.value = null
}

function launchItemEdit(idx) {
  const li = launchItems.value[idx]
  li.editing = !li.editing
}

function openQuickProduct(idx) {
  quickProductItemIdx.value = idx
  const li = launchItems.value[idx]
  quickProduct.value = {
    name: li.product_name || '',
    price: '',
    cost: li.unit_cost || '',
    barcode: li.barcode || '',
    category_id: null,
  }
  quickProductModal.value = true
}

async function saveQuickSupplier() {
  const qs = quickSupplier.value
  if (!qs.name.trim()) {
    ElMessage.warning('Informe o nome do fornecedor.')
    return
  }
  saving.value = true
  try {
    const res = await api.post('/suppliers', qs)
    suppliers.value = (res.suppliers || []).filter(s => s.active)
    const newSup = suppliers.value.find(s => s.name === qs.name)
    if (newSup) form.value.supplier_id = newSup.id
    ElMessage.success('Fornecedor cadastrado!')
    quickSupplierModal.value = false
    quickSupplier.value = { name: '', cnpj: '', phone: '', email: '' }
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function saveQuickProduct() {
  const qp = quickProduct.value
  if (!qp.name.trim()) {
    ElMessage.warning('Informe o nome do produto.')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: qp.name,
      price: qp.price || '0',
      cost: qp.cost || '0',
      barcode: qp.barcode || null,
      stock_quantity: 0,
    }
    const res = await api.post('/products', payload)
    const newProduct = res.product
    if (newProduct) {
      const li = launchItems.value[quickProductItemIdx.value]
      li.product_id = newProduct.id
      li.product_name_existing = newProduct.name
      li.existing_stock = 0
      li.existing_cost = parseFloat(qp.cost) || 0
      li.matched = true
    }
    ElMessage.success('Produto cadastrado!')
    quickProductModal.value = false
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

function calcLaunchTotal() {
  return launchItems.value.reduce((acc, i) => {
    return acc + (parseInt(i.quantity) || 0) * (parseFloat(i.unit_cost) || 0)
  }, 0)
}

async function confirmLaunch() {
  if (!launchTarget.value) return
  const unmatched = launchItems.value.filter(i => !i.matched)
  if (unmatched.length > 0) {
    ElMessage.warning(`${unmatched.length} item(ns) sem produto vinculado. Vincule ou cadastre antes de lançar.`)
    return
  }
  saving.value = true
  try {
    await api.post(`/purchases/${launchTarget.value.id}/confirm`, {
      due_date: launchDate.value || null,
      create_bill: launchCreateBill.value,
    })
    ElMessage.success('Compra lançada! Estoque atualizado com custo médio ponderado.')
    launchTarget.value = null
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

async function cancelPurchase(purchase) {
  try {
    await api.post(`/purchases/${purchase.id}/cancel`)
    ElMessage.success('Compra cancelada.')
    await load()
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function confirmDelete() {
  if (!deleteTarget.value) return
  try {
    await api.del(`/purchases/${deleteTarget.value.id}`)
    purchases.value = purchases.value.filter(p => p.id !== deleteTarget.value.id)
    ElMessage.success('Compra excluída.')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    deleteTarget.value = null
  }
}

function fmtBrl(val) {
  const n = parseFloat(val) || 0
  return n.toLocaleString('pt-BR', { style: 'currency', currency: 'BRL' })
}

function fmtDate(dt) {
  if (!dt) return '—'
  return new Date(dt + (dt.includes('T') ? '' : 'T00:00:00')).toLocaleDateString('pt-BR')
}

function fmtChave(chave) {
  if (!chave) return '—'
  return chave.replace(/(\d{4})/g, '$1 ').trim()
}

onMounted(() => { load(); loadProducts(); loadSuppliers() })
</script>

<template>
  <AppShell>
    <div class="dashboard">
      <div class="page-header">
        <div>
          <h1 class="page-title">Compras</h1>
          <p class="page-subtitle">Entrada de mercadorias e importação de NF-e.</p>
        </div>
        <div class="header-actions">
          <button type="button" class="btn btn-ghost" @click="openNfModal">
            <i class="fas fa-file-import"></i> Importar NF-e
          </button>
          <button type="button" class="btn btn-primary" @click="openNew">
            <i class="fas fa-plus"></i> Nova compra
          </button>
        </div>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else>
        <div class="search-bar">
          <i class="fas fa-search"></i>
          <input v-model="search" type="text" placeholder="Buscar por NF, chave, fornecedor…" />
          <select v-model="statusFilter" class="filter-select">
            <option value="">Todos os status</option>
            <option value="rascunho">Rascunho</option>
            <option value="confirmada">Confirmada</option>
            <option value="cancelada">Cancelada</option>
          </select>
        </div>

        <div class="table-card">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Nº NF</th>
                  <th>Fornecedor</th>
                  <th>Chave</th>
                  <th>Total</th>
                  <th>Data</th>
                  <th>Status</th>
                  <th class="th-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in filtered" :key="p.id" style="cursor:pointer" @click="openDetail(p)">
                  <td>{{ p.nf_number || '—' }}</td>
                  <td>{{ p.supplier_name || '—' }}</td>
                  <td><span class="chave-text">{{ fmtChave(p.nf_chave) }}</span></td>
                  <td>{{ fmtBrl(p.net_total) }}</td>
                  <td>{{ fmtDate(p.created_at) }}</td>
                  <td>
                    <span class="status-badge" :class="statusClass[p.status]">
                      {{ statusLabel[p.status] || p.status }}
                    </span>
                  </td>
                  <td class="cell-actions" @click.stop>
                    <template v-if="p.status === 'rascunho'">
                      <button type="button" class="icon-btn btn-launch" title="Lançar"
                        @click="openLaunchModal(p)">
                        <i class="fas fa-rocket"></i>
                      </button>
                      <button type="button" class="icon-btn" title="Editar" @click="openEdit(p)">
                        <i class="fas fa-edit"></i>
                      </button>
                      <button type="button" class="icon-btn" title="Excluir" @click="deleteTarget = p">
                        <i class="fas fa-trash"></i>
                      </button>
                    </template>
                    <template v-else-if="p.status === 'confirmada'">
                      <button type="button" class="icon-btn" title="Cancelar" @click="cancelPurchase(p)">
                        <i class="fas fa-times"></i>
                      </button>
                    </template>
                  </td>
                </tr>
                <tr v-if="!filtered.length" class="empty-row">
                  <td colspan="7" class="empty-state">
                    <i class="fas fa-truck-loading"></i>
                    <h3>{{ search || statusFilter ? 'Nenhuma compra encontrada' : 'Nenhuma compra registrada' }}</h3>
                    <p>Crie uma nova compra ou importe uma NF-e.</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>

    <!-- Modal Nova/Editar Compra -->
    <div class="modal" :class="{ 'is-open': showModal }">
      <div class="modal-content modal-content-lg">
        <div class="modal-header">
          <h2>{{ editing ? 'Editar compra' : 'Nova compra' }}</h2>
          <button type="button" class="modal-close" @click="showModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="savePurchase">
          <div class="form-row">
            <div class="form-field flex-2">
              <label>Fornecedor</label>
              <div class="input-with-btn">
                <select v-model="form.supplier_id" class="flex-1">
                  <option :value="null">Selecione…</option>
                  <option v-for="s in suppliers" :key="s.id" :value="s.id">{{ s.name }}</option>
                </select>
                <button type="button" class="btn btn-ghost btn-xs" @click="quickSupplierModal = true" title="Cadastrar fornecedor">
                  <i class="fas fa-plus"></i>
                </button>
              </div>
            </div>
            <div class="form-field flex-1">
              <label>Nº Nota (opcional)</label>
              <input v-model="form.nf_number" type="text" placeholder="Ex: 12345" />
            </div>
          </div>
          <div class="form-row">
            <div class="form-field flex-1">
              <label>Frete</label>
              <input v-model="form.freight" type="text" placeholder="0,00" />
            </div>
            <div class="form-field flex-1">
              <label>Desconto</label>
              <input v-model="form.discount" type="text" placeholder="0,00" />
            </div>
          </div>

          <div class="items-section">
            <div class="items-header">
              <h3>Itens da compra</h3>
              <button type="button" class="btn btn-ghost btn-sm" @click="addItem">
                <i class="fas fa-plus"></i> Adicionar item
              </button>
            </div>
            <div v-for="(item, idx) in items" :key="idx" class="item-row">
              <div class="form-field flex-3">
                <label>Produto</label>
                <input v-model="item.product_name" type="text" placeholder="Descrição do produto" />
              </div>
              <div class="form-field flex-1">
                <label>Qtd</label>
                <input v-model.number="item.quantity" type="number" min="1" />
              </div>
              <div class="form-field flex-1">
                <label>Custo unit.</label>
                <input v-model="item.unit_cost" type="text" placeholder="0,00" />
              </div>
              <div class="form-field flex-1">
                <label>Total</label>
                <input :value="fmtBrl(calcItemTotal(item))" type="text" disabled />
              </div>
              <button type="button" class="icon-btn remove-item" @click="removeItem(idx)" v-if="items.length > 1">
                <i class="fas fa-times"></i>
              </button>
            </div>
          </div>

          <div class="totals-row">
            <span>Subtotal: <strong>{{ fmtBrl(calcSubtotal()) }}</strong></span>
            <span>Líquido: <strong>{{ fmtBrl(calcNetTotal()) }}</strong></span>
          </div>

          <div class="form-field">
            <label>Observações</label>
            <input v-model="form.obs" type="text" placeholder="Notas sobre a compra…" />
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

    <!-- Modal Detalhes -->
    <div class="modal" :class="{ 'is-open': detailModal }">
      <div class="modal-content modal-content-lg">
        <div class="modal-header">
          <h2>Compra #{{ detailPurchase?.id }}</h2>
          <button type="button" class="modal-close" @click="detailModal = false">&times;</button>
        </div>
        <div v-if="detailPurchase" class="detail-body">
          <div class="detail-row">
            <span>NF: {{ detailPurchase.nf_number || '—' }}</span>
            <span>Fornecedor: {{ detailPurchase.supplier_name || '—' }}</span>
            <span>Status: <span class="status-badge" :class="statusClass[detailPurchase.status]">{{ statusLabel[detailPurchase.status] }}</span></span>
          </div>
          <div class="detail-row">
            <span>Total: {{ fmtBrl(detailPurchase.total) }}</span>
            <span>Frete: {{ fmtBrl(detailPurchase.freight) }}</span>
            <span>Desconto: {{ fmtBrl(detailPurchase.discount) }}</span>
            <span>Líquido: {{ fmtBrl(detailPurchase.net_total) }}</span>
          </div>
          <div v-if="detailPurchase.nf_chave" class="detail-row">
            <span>Chave: {{ fmtChave(detailPurchase.nf_chave) }}</span>
          </div>
          <h3 style="margin-top:16px">Itens</h3>
          <table class="data-table" v-if="detailItems.length">
            <thead>
              <tr><th>Produto</th><th>Qtd</th><th>Custo unit.</th><th>Total</th></tr>
            </thead>
            <tbody>
              <tr v-for="item in detailItems" :key="item.id">
                <td>{{ item.product_name || '—' }}</td>
                <td>{{ item.quantity }}</td>
                <td>{{ fmtBrl(item.unit_cost) }}</td>
                <td>{{ fmtBrl(item.total) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div class="modal-footer">
          <button type="button" class="btn btn-ghost" @click="detailModal = false">Fechar</button>
        </div>
      </div>
    </div>

    <!-- Modal Importar NF-e -->
    <div class="modal" :class="{ 'is-open': nfModal }">
      <div class="modal-content modal-content-md">
        <div class="modal-header">
          <h2>Importar NF-e</h2>
          <button type="button" class="modal-close" @click="nfModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="importNfe">
          <div class="form-field">
            <label>XML da NF-e</label>
            <textarea v-model="nfXml" rows="10" placeholder="Cole o conteúdo XML aqui…" style="font-family:monospace;font-size:12px"></textarea>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-ghost" @click="nfModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-file-import"></i> {{ saving ? 'Importando…' : 'Importar' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal Lançar Compra -->
    <div class="modal" :class="{ 'is-open': !!launchTarget }">
      <div class="modal-content modal-content-lg">
        <div class="modal-header">
          <h2><i class="fas fa-rocket"></i> Lançar Compra #{{ launchTarget?.id }}</h2>
          <button type="button" class="modal-close" @click="launchTarget = null">&times;</button>
        </div>
        <div class="modal-form launch-body">
          <div class="launch-info">
            <span>NF: <strong>{{ launchTarget?.nf_number || '—' }}</strong></span>
            <span>Fornecedor: <strong>{{ launchTarget?.supplier_name || '—' }}</strong></span>
            <span>Total: <strong>{{ fmtBrl(launchTarget?.net_total) }}</strong></span>
          </div>

          <p class="launch-hint">
            Vincule cada item a um produto do sistema. Itens sem barcode podem ser buscados pelo nome.
          </p>

          <div class="launch-items">
            <div v-for="(li, idx) in launchItems" :key="idx" class="launch-item"
              :class="{ 'is-unmatched': !li.matched }">

              <div class="launch-item-header">
                <span class="launch-item-num">#{{ idx + 1 }}</span>
                <strong>{{ li.product_name || 'Sem nome' }}</strong>
                <span class="launch-item-barcode" v-if="li.barcode">EAN: {{ li.barcode }}</span>
                <span class="launch-item-unit" v-if="li.unit_com">
                  NF-e: {{ li.quantity }} {{ li.unit_com }}
                  <span v-if="li.unit_com !== 'UN' && li.unit_com !== 'PC' && li.unit_com !== 'PÇ'">
                    (= {{ (parseInt(li.quantity) || 0) * (parseInt(li.units_per_case) || 1) }} un.)
                  </span>
                </span>
                <span class="launch-item-qty">{{ li.quantity }}x {{ fmtBrl(li.unit_cost) }}</span>
              </div>

              <div class="launch-conversion" v-if="li.unit_com && li.unit_com !== 'UN' && li.unit_com !== 'PC' && li.unit_com !== 'PÇ'">
                <label>Qtd. unidades por {{ li.unit_com.toLowerCase() }}:</label>
                <input v-model.number="li.units_per_case" type="number" min="1" class="inline-input" />
                <span class="conversion-info" v-if="li.units_per_case > 1">
                  → {{ (parseInt(li.quantity) || 0) * (parseInt(li.units_per_case) || 1) }} un.
                  × {{ fmtBrl((parseFloat(li.unit_cost) || 0) / (parseInt(li.units_per_case) || 1)) }}/un.
                </span>
              </div>

              <div v-if="li.matched" class="launch-item-matched">
                <span class="match-badge is-matched">
                  <i class="fas fa-link"></i> {{ li.product_name_existing }}
                </span>
                <span class="match-info">Estoque: {{ li.existing_stock }} | Custo atual: {{ fmtBrl(li.existing_cost) }}</span>
                <span class="match-info">
                  Entrada: <strong>{{ li.units_per_case > 1 ? (parseInt(li.quantity) * parseInt(li.units_per_case)) : li.quantity }} un.</strong>
                  × {{ fmtBrl(calcWeightedCost(li)) }}/un.
                </span>
                <span class="match-info" v-if="li.existing_stock > 0">
                  Custo médio após entrada: <strong>{{ fmtBrl(calcWeightedCost(li)) }}</strong>
                </span>
                <div class="launch-item-actions">
                  <button type="button" class="btn btn-ghost btn-xs" @click="launchItemEdit(idx)">
                    <i class="fas fa-pen"></i> Editar
                  </button>
                  <button type="button" class="btn btn-ghost btn-xs" @click="unmatchProduct(idx)">
                    <i class="fas fa-unlink"></i> Desvincular
                  </button>
                </div>
              </div>

              <div v-else class="launch-item-unmatched">
                <div class="launch-search-row">
                  <button type="button" class="btn btn-ghost btn-xs"
                    @click="launchSearchIdx === idx ? (launchSearchIdx = null) : openLaunchSearch(idx)">
                    <i class="fas fa-search"></i> {{ launchSearchIdx === idx ? 'Fechar busca' : 'Buscar produto' }}
                  </button>
                  <button type="button" class="btn btn-ghost btn-xs" @click="openQuickProduct(idx)">
                    <i class="fas fa-plus"></i> Cadastro rápido
                  </button>
                </div>

                <div v-if="launchSearchIdx === idx" class="launch-search-panel">
                  <div class="launch-search-input">
                    <input v-model="launchSearchQuery" type="text" placeholder="Buscar por nome ou código…"
                      @keyup.enter="searchLaunchProduct" autofocus />
                    <button type="button" class="btn btn-primary btn-xs" @click="searchLaunchProduct" :disabled="launchSearching">
                      <i class="fas fa-search"></i>
                    </button>
                  </div>
                  <div v-if="launchSearchResults.length" class="launch-search-results">
                    <div v-for="p in launchSearchResults" :key="p.id" class="launch-search-result"
                      @click="matchProduct(idx, p)">
                      <span>{{ p.name }}</span>
                      <span class="sr-info">Estoque: {{ p.stock_quantity }} | {{ fmtBrl(p.cost) }}</span>
                    </div>
                  </div>
                  <div v-else-if="launchSearchQuery && !launchSearching" class="muted-sm">
                    Nenhum produto encontrado.
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div class="launch-totals">
            <span>Itens: <strong>{{ launchItems.length }}</strong></span>
            <span>Total: <strong>{{ fmtBrl(calcLaunchTotal()) }}</strong></span>
          </div>

          <div class="launch-footer-options">
            <div class="form-field" style="flex:1">
              <label>Vencimento da conta</label>
              <input v-model="launchDate" type="date" />
            </div>
            <div class="form-field" style="display:flex;align-items:center;gap:8px;margin-top:20px">
              <input v-model="launchCreateBill" type="checkbox" id="launchBill" />
              <label for="launchBill" style="margin:0">Criar conta a pagar</label>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button type="button" class="btn btn-ghost" @click="launchTarget = null">Cancelar</button>
          <button type="button" class="btn btn-primary btn-launch-confirm" :disabled="saving"
            @click="confirmLaunch">
            <i class="fas fa-rocket"></i> {{ saving ? 'Lançando…' : 'Lançar e atualizar estoque' }}
          </button>
        </div>
      </div>
    </div>

    <!-- Modal Cadastro Rápido de Produto -->
    <div class="modal" :class="{ 'is-open': quickProductModal }">
      <div class="modal-content modal-content-md">
        <div class="modal-header">
          <h2>Cadastro rápido de produto</h2>
          <button type="button" class="modal-close" @click="quickProductModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="saveQuickProduct">
          <div class="form-field">
            <label>Nome *</label>
            <input v-model="quickProduct.name" type="text" placeholder="Nome do produto" required />
          </div>
          <div class="form-row">
            <div class="form-field flex-1">
              <label>Código de barras</label>
              <input v-model="quickProduct.barcode" type="text" placeholder="EAN" />
            </div>
            <div class="form-field flex-1">
              <label>Preço de venda</label>
              <input v-model="quickProduct.price" type="text" placeholder="0,00" />
            </div>
          </div>
          <div class="form-field">
            <label>Custo unitário</label>
            <input v-model="quickProduct.cost" type="text" placeholder="0,00" />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-ghost" @click="quickProductModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Cadastrar' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <!-- Modal Cadastro Rápido de Fornecedor -->
    <div class="modal" :class="{ 'is-open': quickSupplierModal }">
      <div class="modal-content modal-content-md">
        <div class="modal-header">
          <h2>Cadastro rápido de fornecedor</h2>
          <button type="button" class="modal-close" @click="quickSupplierModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="saveQuickSupplier">
          <div class="form-field">
            <label>Nome / Razão Social *</label>
            <input v-model="quickSupplier.name" type="text" placeholder="Nome do fornecedor" required />
          </div>
          <div class="form-row">
            <div class="form-field flex-1">
              <label>CNPJ</label>
              <input v-model="quickSupplier.cnpj" type="text" placeholder="00.000.000/0000-00" />
            </div>
            <div class="form-field flex-1">
              <label>Telefone</label>
              <input v-model="quickSupplier.phone" type="text" placeholder="(00) 00000-0000" />
            </div>
          </div>
          <div class="form-field">
            <label>E-mail</label>
            <input v-model="quickSupplier.email" type="email" placeholder="email@exemplo.com" />
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-ghost" @click="quickSupplierModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Cadastrar' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <ConfirmDialog
      v-if="deleteTarget"
      title="Excluir compra"
      :message="'Excluir a compra #' + deleteTarget.id + '?'"
      confirm-text="Excluir"
      @confirm="confirmDelete"
      @cancel="deleteTarget = null"
    />
  </AppShell>
</template>

<style scoped>
.muted { color: var(--text-muted); padding: 24px 4px; }
.muted-sm { color: var(--text-muted); font-size: 13px; padding: 8px 4px; }
.input-with-btn { display: flex; gap: 4px; align-items: stretch; }
.input-with-btn select { flex: 1; }
.input-with-btn .btn { padding: 6px 10px; }
.header-actions { display: flex; gap: 8px; }
.search-bar { display: flex; align-items: center; gap: 8px; background: var(--surface, #fff); border: 1px solid var(--border, #d1d5db); border-radius: 8px; padding: 8px 12px; margin-bottom: 16px; }
.search-bar i { color: var(--text-muted, #999); }
.search-bar input { flex: 1; border: none; outline: none; font-size: 14px; background: transparent; }
.filter-select { border: 1px solid var(--border, #d1d5db); border-radius: 6px; padding: 4px 8px; font-size: 13px; background: var(--surface, #fff); }
.chave-text { font-family: monospace; font-size: 11px; word-break: break-all; }
.btn-launch { color: var(--primary, #2563eb) !important; }
.btn-launch-confirm { background: var(--primary, #2563eb); min-width: 200px; }
.form-row { display: flex; gap: 12px; }
.form-field { margin-bottom: 4px; }
.form-field label { display: block; font-size: 13px; font-weight: 600; color: var(--text-secondary, #666); margin-bottom: 4px; }
.form-field input, .form-field select, .form-field textarea { width: 100%; padding: 8px 10px; border: 1px solid var(--border, #d1d5db); border-radius: 6px; font-size: 14px; }
.form-field input:focus, .form-field select:focus, .form-field textarea:focus { outline: none; border-color: var(--primary, #2563eb); box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15); }
.form-field textarea { resize: vertical; }
.flex-1 { flex: 1; } .flex-2 { flex: 2; } .flex-3 { flex: 3; }
.items-section { margin: 12px 0; border: 1px solid var(--border, #e5e7eb); border-radius: 8px; padding: 12px; }
.items-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.items-header h3 { margin: 0; font-size: 14px; }
.item-row { display: flex; gap: 8px; align-items: flex-end; margin-bottom: 8px; }
.item-row .form-field { margin-bottom: 0; }
.remove-item { margin-bottom: 4px; }
.totals-row { display: flex; justify-content: flex-end; gap: 24px; font-size: 14px; margin: 8px 0; }
.detail-body { padding: 0 4px; }
.detail-row { display: flex; gap: 16px; flex-wrap: wrap; font-size: 14px; margin-bottom: 8px; }
.btn-sm { padding: 4px 10px; font-size: 13px; }
.btn-xs { padding: 3px 8px; font-size: 12px; }

.launch-body { max-height: 70vh; overflow-y: auto; }
.launch-info { display: flex; gap: 16px; flex-wrap: wrap; font-size: 14px; margin-bottom: 8px; padding: 8px 12px; background: var(--bg-secondary, #f9fafb); border-radius: 6px; }
.launch-hint { font-size: 13px; color: var(--text-secondary, #666); margin-bottom: 12px; }
.launch-items { display: flex; flex-direction: column; gap: 8px; }
.launch-item { border: 1px solid var(--border, #e5e7eb); border-radius: 8px; padding: 10px 12px; }
.launch-item.is-unmatched { border-color: #f59e0b; background: #fffbeb; }
.launch-item-header { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; }
.launch-item-num { font-size: 12px; color: var(--text-muted, #999); font-weight: 600; }
.launch-item-barcode { font-size: 12px; font-family: monospace; color: var(--text-muted, #999); }
.launch-item-qty { margin-left: auto; font-size: 13px; color: var(--text-secondary, #666); }
.launch-item-unit { font-size: 12px; color: var(--text-secondary, #666); }
.launch-conversion { display: flex; align-items: center; gap: 8px; margin-top: 6px; font-size: 13px; }
.launch-conversion label { color: var(--text-secondary, #666); white-space: nowrap; }
.inline-input { width: 60px; padding: 4px 8px; border: 1px solid var(--border, #d1d5db); border-radius: 4px; font-size: 13px; text-align: center; }
.conversion-info { font-size: 12px; color: var(--primary, #2563eb); font-weight: 600; }
.launch-item-matched { margin-top: 6px; }
.match-badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.match-badge.is-matched { background: #d1fae5; color: #065f46; }
.match-info { display: block; font-size: 12px; color: var(--text-secondary, #666); margin-top: 4px; }
.launch-item-actions { display: flex; gap: 6px; margin-top: 6px; }
.launch-item-unmatched { margin-top: 6px; }
.launch-search-row { display: flex; gap: 6px; }
.launch-search-panel { margin-top: 8px; }
.launch-search-input { display: flex; gap: 6px; }
.launch-search-input input { flex: 1; padding: 6px 10px; border: 1px solid var(--border, #d1d5db); border-radius: 6px; font-size: 13px; }
.launch-search-results { max-height: 150px; overflow-y: auto; border: 1px solid var(--border, #e5e7eb); border-radius: 6px; margin-top: 6px; }
.launch-search-result { display: flex; justify-content: space-between; padding: 8px 10px; cursor: pointer; font-size: 13px; border-bottom: 1px solid var(--border, #f3f4f6); }
.launch-search-result:last-child { border-bottom: none; }
.launch-search-result:hover { background: var(--bg-secondary, #f3f4f6); }
.sr-info { font-size: 12px; color: var(--text-muted, #999); }
.launch-totals { display: flex; justify-content: flex-end; gap: 24px; font-size: 14px; margin: 12px 0 8px; padding-top: 8px; border-top: 1px solid var(--border, #e5e7eb); }
.launch-footer-options { display: flex; gap: 12px; align-items: flex-end; }
</style>
