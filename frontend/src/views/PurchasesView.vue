<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { normalizeForSearch } from '@/utils/normalize'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'
import ProductSearch from '@/components/ProductSearch.vue'

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
const launchPaid = ref(false)
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

const statusLabel = { rascunho: 'Rascunho', confirmada: 'Confirmada', cancelada: 'Cancelada' }
const statusClass = { rascunho: 'is-low', confirmada: 'is-ok', cancelada: 'is-off' }

const filtered = computed(() => {
  let list = purchases.value
  const q = normalizeForSearch(search.value)
  if (q) {
    list = list.filter(p =>
      normalizeForSearch(p.nf_number || '').includes(q) ||
      normalizeForSearch(p.nf_chave || '').includes(q) ||
      normalizeForSearch(p.supplier_name || '').includes(q) ||
      normalizeForSearch(p.obs || '').includes(q)
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
  items.value = []
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
    if (!items.value.length) items.value = []
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
  if (!items.value.length) {
    ElMessage.warning('Adicione ao menos um produto à compra.')
    return
  }
  if (items.value.some(i => !i.product_id)) {
    ElMessage.warning('Todos os itens precisam estar vinculados a um produto.')
    return
  }
  saving.value = true
  try {
    const payload = {
      ...form.value,
      items: items.value,
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

function removeItem(index) {
  items.value.splice(index, 1)
}

function addProductItem(product) {
  const existing = items.value.find(i => i.product_id === product.id)
  if (existing) {
    existing.quantity = (parseInt(existing.quantity) || 0) + 1
  } else {
    items.value.push({
      product_id: product.id,
      product_name: product.name,
      barcode: product.barcode || '',
      quantity: 1,
      unit_cost: product.cost != null ? String(product.cost) : '',
    })
  }
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
  launchCreateBill.value = false
  launchPaid.value = true
  const data = await api.get(`/purchases/${purchase.id}`)
  launchItems.value = data.items.map(item => ({
    ...item,
    product_id: item.product_id || null,
    matched: !!item.product_id,
    units_per_case: 1,
    units: [],
    selected_unit_id: null,
    product_price: null,
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
          li.product_price = res.product.price
          li.matched = true
          li.units = (res.product.units || []).map(u => ({ ...u }))
          if (li.units.length) {
            const matched = li.barcode ? li.units.find(u => u.barcode === li.barcode) : null
            const def = matched || li.units.find(u => u.is_default) || li.units[0]
            li.units_per_case = def.factor
          }
        }
      } catch { /* no match */ }
    } else if (li.matched && li.product_id) {
      try {
        const res = await api.get(`/products/${li.product_id}`)
        if (res.product) {
          li.product_name_existing = res.product.name
          li.existing_stock = res.product.stock_quantity
          li.existing_cost = res.product.cost
          li.product_price = res.product.price
          li.units = (res.product.units || []).map(u => ({ ...u }))
          if (li.units.length) {
            const def = li.units.find(u => u.is_default) || li.units[0]
            li.units_per_case = def.factor
          }
        }
      } catch { /* ignore */ }
    }
  }
}

function custoUnitario(item) {
  const factor = parseInt(item.units_per_case) || 1
  if (factor <= 0) return 0
  return (parseFloat(item.unit_cost) || 0) / factor
}

function marginFor(item, price, factor) {
  const p = parseFloat(price) || 0
  if (p <= 0) return null
  const cost = custoUnitario(item) * (parseInt(factor) || 1)
  return ((p - cost) / p) * 100
}

function matchProduct(idx, product) {
  const li = launchItems.value[idx]
  li.product_id = product.id
  li.product_name_existing = product.name
  li.existing_stock = product.stock_quantity
  li.existing_cost = product.cost
  li.product_price = product.price
  li.matched = true
  li.units = (product.units || []).map(u => ({ ...u }))
  if (li.units.length) {
    const def = li.units.find(u => u.is_default) || li.units[0]
    li.units_per_case = def.factor
  }
}

function unmatchProduct(idx) {
  const li = launchItems.value[idx]
  li.product_id = null
  li.product_name_existing = null
  li.existing_stock = null
  li.existing_cost = null
  li.matched = false
  li.units = []
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
      li.units = []
      li.product_price = qp.price ? parseFloat(qp.price) : null
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

function entradaUn(item) {
  return (parseInt(item.quantity) || 0) * (parseInt(item.units_per_case) || 1)
}

function calcLaunchTotal() {
  return launchItems.value.reduce((acc, i) => {
    return acc + (parseInt(i.quantity) || 0) * (parseFloat(i.unit_cost) || 0)
  }, 0)
}

function launchItemPayload(li) {
  const payload = {
    id: li.id,
    product_id: li.product_id,
    quantity: parseInt(li.quantity) || 0,
    unit_cost: li.unit_cost,
    factor: parseInt(li.units_per_case) || 1,
    unit_com: li.unit_com || null,
  }
  if (li.units && li.units.length > 1) {
    payload.unit_prices = li.units.map(u => ({ unit_id: u.id, price: u.price }))
  } else {
    payload.price = li.product_price
    if (li.units && li.units.length === 1) {
      payload.unit_prices = [{ unit_id: li.units[0].id, price: li.product_price }]
    }
  }
  return payload
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
      paid: launchPaid.value,
      items: launchItems.value.map(launchItemPayload),
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

const chaveCopied = ref(false)
let chaveCopiedTimer = null

async function copyChave() {
  const raw = String(detailPurchase.value?.nf_chave || '').replace(/\s/g, '')
  if (!raw) return
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(raw)
    } else {
      const ta = document.createElement('textarea')
      ta.value = raw
      document.body.appendChild(ta)
      ta.select()
      document.execCommand('copy')
      ta.remove()
    }
    chaveCopied.value = true
    ElMessage.success('Chave copiada')
    clearTimeout(chaveCopiedTimer)
    chaveCopiedTimer = setTimeout(() => {
      chaveCopied.value = false
    }, 1500)
  } catch {
    ElMessage.error('Não foi possível copiar a chave.')
  }
}

const openMenuId = ref(null)
const menuPos = ref({ top: 0, left: 0 })

const menuPurchase = computed(() =>
  (purchases.value || []).find((p) => p.id === openMenuId.value) || null
)

function toggleMenu(purchase, event) {
  if (openMenuId.value === purchase.id) {
    closeMenu()
    return
  }
  const rect = event?.currentTarget?.getBoundingClientRect()
  let top = 80
  let left = Math.max(8, window.innerWidth - 216)
  if (rect) {
    const PANEL_W = 200
    const PANEL_H = 170
    const up = window.innerHeight - rect.bottom < PANEL_H + 12 && rect.top > PANEL_H + 12
    top = up ? rect.top - PANEL_H - 6 : rect.bottom + 6
    left = Math.max(8, Math.min(rect.right - PANEL_W, window.innerWidth - PANEL_W - 8))
  }
  menuPos.value = { top, left }
  openMenuId.value = purchase.id
}

function closeMenu() {
  openMenuId.value = null
}

function onKeydown(event) {
  if (event.key !== 'Escape') return
  if (detailModal.value) {
    detailModal.value = false
    return
  }
  closeMenu()
}

onMounted(() => {
  load(); loadProducts(); loadSuppliers()
  document.addEventListener('keydown', onKeydown)
  window.addEventListener('scroll', closeMenu, true)
  window.addEventListener('resize', closeMenu)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  window.removeEventListener('scroll', closeMenu, true)
  window.removeEventListener('resize', closeMenu)
  clearTimeout(chaveCopiedTimer)
})
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
          <button type="button" class="btn-brand" @click="openNew">
            <i class="fas fa-plus"></i> Nova compra
          </button>
        </div>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else>
        <div class="products-toolbar">
          <div class="search-box products-search-box">
            <i class="fas fa-search"></i>
            <input
              v-model="search"
              type="text"
              placeholder="Buscar por NF, chave ou fornecedor..."
              aria-label="Buscar por NF, chave ou fornecedor"
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
            <option value="">Todos os status</option>
            <option value="rascunho">Rascunho</option>
            <option value="confirmada">Confirmada</option>
            <option value="cancelada">Cancelada</option>
          </select>
        </div>

        <div
          v-if="openMenuId !== null"
          class="popover-overlay"
          @click="closeMenu()"
        ></div>

        <div class="table-card">
          <div class="table-container">
            <table class="data-table purchases-table">
              <thead>
                <tr>
                  <th class="col-nf">Nº NF</th>
                  <th>Fornecedor</th>
                  <th class="col-chave">Chave NF-e</th>
                  <th class="th-amount col-total">Total</th>
                  <th class="col-data">Data</th>
                  <th class="col-status">Status</th>
                  <th class="th-actions"><span class="sr-only">Ações</span></th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="p in filtered" :key="p.id" style="cursor:pointer" @click="openDetail(p)">
                  <td class="col-nf nowrap">{{ p.nf_number || '—' }}</td>
                  <td>
                    <span class="cell-title" :title="p.supplier_name || ''">{{ p.supplier_name || '—' }}</span>
                  </td>
                  <td class="col-chave">
                    <span class="chave-short" :title="p.nf_chave || ''">{{ fmtChave(p.nf_chave) }}</span>
                  </td>
                  <td class="cell-amount nowrap">{{ fmtBrl(p.net_total) }}</td>
                  <td class="col-data nowrap">{{ fmtDate(p.created_at) }}</td>
                  <td class="col-status">
                    <span class="status-badge" :class="statusClass[p.status]">
                      {{ statusLabel[p.status] || p.status }}
                    </span>
                  </td>
                  <td class="cell-actions" @click.stop>
                    <div v-if="p.status === 'rascunho' || p.status === 'confirmada'" class="row-menu">
                      <button
                        type="button"
                        class="icon-btn"
                        title="Ações"
                        :aria-label="`Ações da compra ${p.nf_number || p.id}`"
                        :aria-expanded="openMenuId === p.id ? 'true' : 'false'"
                        @click="toggleMenu(p, $event)"
                      >
                        <i class="fas fa-ellipsis-v"></i>
                      </button>
                    </div>
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
    <Teleport to="body">
      <div
        v-if="menuPurchase"
        class="row-menu-panel menu-float"
        role="menu"
        :style="{ top: menuPos.top + 'px', left: menuPos.left + 'px' }"
      >
        <template v-if="menuPurchase.status === 'rascunho'">
          <button type="button" role="menuitem" @click="openLaunchModal(menuPurchase); closeMenu()">
            <i class="fas fa-rocket"></i> Lançar no estoque
          </button>
          <button type="button" role="menuitem" @click="openEdit(menuPurchase); closeMenu()">
            <i class="fas fa-pen"></i> Editar
          </button>
          <button type="button" role="menuitem" class="is-danger" @click="deleteTarget = menuPurchase; closeMenu()">
            <i class="fas fa-trash"></i> Excluir
          </button>
        </template>
        <template v-else-if="menuPurchase.status === 'confirmada'">
          <button type="button" role="menuitem" class="is-danger" @click="cancelPurchase(menuPurchase); closeMenu()">
            <i class="fas fa-times"></i> Cancelar compra
          </button>
        </template>
      </div>
    </Teleport>

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
            </div>
            <ProductSearch
              :products="allProducts"
              placeholder="Buscar produto para adicionar…"
              @select="addProductItem"
            />

            <p v-if="!items.length" class="muted-sm">
              Nenhum item. Busque um produto acima para adicionar.
            </p>
            <div v-else class="item-list">
              <div v-for="(item, idx) in items" :key="idx" class="item-row">
                <div class="form-field flex-3">
                  <label>Produto</label>
                  <input :value="item.product_name" type="text" disabled />
                </div>
                <div class="form-field flex-1">
                  <label>Qtd</label>
                  <input v-model.number="item.quantity" type="number" min="1" />
                </div>
                <div class="form-field flex-1">
                  <label>Custo unit.</label>
                  <input v-model="item.unit_cost" type="number" step="0.01" placeholder="0,00" />
                </div>
                <div class="form-field flex-1">
                  <label>Total</label>
                  <input :value="fmtBrl(calcItemTotal(item))" type="text" disabled />
                </div>
                <button type="button" class="icon-btn remove-item" @click="removeItem(idx)">
                  <i class="fas fa-times"></i>
                </button>
              </div>
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
    <div class="modal" :class="{ 'is-open': detailModal }" @click.self="detailModal = false">
      <div class="modal-content detail-modal">
        <div class="modal-header detail-header">
          <div>
            <h2>
              Compra #{{ detailPurchase?.id }}
              <span
                v-if="detailPurchase"
                class="status-badge"
                :class="statusClass[detailPurchase.status]"
              >{{ statusLabel[detailPurchase.status] }}</span>
            </h2>
            <p v-if="detailPurchase" class="detail-sub">
              NF {{ detailPurchase.nf_number || '—' }} · {{ fmtDate(detailPurchase.created_at) }}
            </p>
          </div>
          <button type="button" class="modal-close" aria-label="Fechar" @click="detailModal = false">&times;</button>
        </div>
        <div v-if="detailPurchase" class="detail-body">
          <div class="detail-supplier">
            <span>Fornecedor</span>
            <strong :title="detailPurchase.supplier_name || ''">
              {{ detailPurchase.supplier_name || '—' }}
            </strong>
          </div>
          <dl class="detail-money">
            <div>
              <dt>Total</dt>
              <dd>{{ fmtBrl(detailPurchase.total) }}</dd>
            </div>
            <div>
              <dt>Frete</dt>
              <dd>{{ fmtBrl(detailPurchase.freight) }}</dd>
            </div>
            <div>
              <dt>Desconto</dt>
              <dd>{{ fmtBrl(detailPurchase.discount) }}</dd>
            </div>
            <div class="is-total">
              <dt>Líquido</dt>
              <dd>{{ fmtBrl(detailPurchase.net_total) }}</dd>
            </div>
          </dl>
          <div v-if="detailPurchase.nf_chave" class="detail-chave">
            <div class="detail-chave-head">
              <span>Chave de acesso</span>
              <button
                type="button"
                class="icon-btn chave-copy"
                title="Copiar chave"
                aria-label="Copiar chave de acesso"
                @click="copyChave"
              >
                <i :class="chaveCopied ? 'fas fa-check' : 'fas fa-copy'"></i>
              </button>
            </div>
            <code :title="detailPurchase.nf_chave">{{ fmtChave(detailPurchase.nf_chave) }}</code>
          </div>
          <h3>Itens ({{ detailItems.length }})</h3>
          <div v-if="detailItems.length" class="table-container">
            <table class="data-table detail-table">
              <thead>
                <tr><th>Produto</th><th class="th-number col-qtd">Qtd</th><th class="th-amount col-custo">Custo unit.</th><th class="th-amount col-total">Total</th></tr>
              </thead>
              <tbody>
                <tr v-for="item in detailItems" :key="item.id">
                  <td><span class="cell-title" :title="item.product_name || ''">{{ item.product_name || '—' }}</span></td>
                  <td class="cell-number">{{ item.quantity }}</td>
                  <td class="cell-amount">{{ fmtBrl(item.unit_cost) }}</td>
                  <td class="cell-amount">{{ fmtBrl(item.total) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
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
            <div
              v-for="(li, idx) in launchItems"
              :key="idx"
              class="li-card"
              :class="{ 'is-unmatched': !li.matched }"
            >
              <div class="li-head">
                <span class="li-num">#{{ idx + 1 }}</span>
                <strong class="li-name">{{ li.product_name || 'Sem nome' }}</strong>
                <span v-if="li.matched" class="match-badge is-matched">
                  <i class="fas fa-link"></i> {{ li.product_name_existing }}
                </span>
                <span v-else class="match-badge is-unmatched-badge">Não vinculado</span>
                <button
                  v-if="li.matched"
                  type="button"
                  class="btn btn-ghost btn-xs li-unlink"
                  @click="unmatchProduct(idx)"
                >
                  <i class="fas fa-unlink"></i> Desvincular
                </button>
              </div>

              <div class="li-meta">
                <span v-if="li.barcode">EAN {{ li.barcode }}</span>
                <span v-if="li.unit_com">NF-e: {{ li.quantity }} {{ li.unit_com }}</span>
                <span v-if="li.matched">Estoque atual: {{ li.existing_stock }} un.</span>
              </div>

              <div v-if="li.matched" class="li-grid">
                <div class="li-cell">
                  <label>Qtd (nota)</label>
                  <span class="li-readonly">{{ li.quantity }}</span>
                </div>
                <div class="li-cell">
                  <label>Un. por caixa</label>
                  <input v-model.number="li.units_per_case" type="number" min="1" class="li-input" />
                </div>
                <div class="li-cell is-cost">
                  <label>Valor (nota)</label>
                  <input v-model="li.unit_cost" type="number" step="0.01" min="0" class="li-input" />
                </div>
                <div class="li-cell">
                  <label>Custo por unidade</label>
                  <span class="li-readonly">{{ fmtBrl(custoUnitario(li)) }}</span>
                </div>
                <div class="li-cell">
                  <label>Entrada</label>
                  <span class="li-readonly"><strong>{{ entradaUn(li) }}</strong> un.</span>
                </div>
              </div>

              <div v-if="li.matched" class="li-prices">
                <span class="li-prices-title">Preços de venda</span>
                <template v-if="li.units && li.units.length > 1">
                  <div v-for="u in li.units" :key="u.id" class="li-price-row">
                    <span class="li-price-name">{{ u.name }} <small>({{ u.factor }}x)</small></span>
                    <input v-model="u.price" type="number" step="0.01" min="0" class="li-input li-price-input" />
                    <span
                      v-if="marginFor(li, u.price, u.factor) !== null"
                      class="margin-badge"
                      :class="{ 'is-negative': marginFor(li, u.price, u.factor) < 0 }"
                    >
                      Lucro {{ marginFor(li, u.price, u.factor).toFixed(0) }}%
                    </span>
                  </div>
                </template>
                <div v-else class="li-price-row">
                  <span class="li-price-name">Preço de venda</span>
                  <input v-model="li.product_price" type="number" step="0.01" min="0" class="li-input li-price-input" />
                  <span
                    v-if="marginFor(li, li.product_price, 1) !== null"
                    class="margin-badge"
                    :class="{ 'is-negative': marginFor(li, li.product_price, 1) < 0 }"
                  >
                    Lucro {{ marginFor(li, li.product_price, 1).toFixed(0) }}%
                  </span>
                </div>
              </div>

              <div v-else class="li-search">
                <ProductSearch
                  :products="allProducts"
                  placeholder="Buscar produto por nome ou código…"
                  @select="matchProduct(idx, $event)"
                />
                <button type="button" class="btn btn-ghost btn-xs" @click="openQuickProduct(idx)">
                  <i class="fas fa-plus"></i> Cadastro rápido
                </button>
              </div>
            </div>
          </div>

          <div class="launch-totals">
            <span>Itens: <strong>{{ launchItems.length }}</strong></span>
            <span>Total: <strong>{{ fmtBrl(calcLaunchTotal()) }}</strong></span>
          </div>

          <div class="launch-footer-options">
            <div class="form-field launch-due">
              <label>Vencimento da conta</label>
              <input v-model="launchDate" type="date" :disabled="!launchCreateBill" />
            </div>
            <div class="launch-checks">
              <label class="launch-check">
                <input v-model="launchPaid" type="checkbox" />
                <span>Conta já paga</span>
              </label>
              <label class="launch-check">
                <input v-model="launchCreateBill" type="checkbox" />
                <span>Criar conta a pagar</span>
              </label>
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
      confirm-label="Excluir"
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
.products-toolbar .toolbar-select-status {
  width: 180px;
}

/* Tabela com layout fixo: Fornecedor flexível, demais compactas */
.purchases-table {
  table-layout: fixed;
}
.purchases-table .col-nf {
  width: 100px;
}
.purchases-table .col-chave {
  width: 210px;
}
.purchases-table .col-total {
  width: 130px;
}
.purchases-table .col-data {
  width: 122px;
}
.purchases-table .col-status {
  width: 130px;
}
.purchases-table tbody td {
  min-width: 0;
  padding: 10px 16px;
  overflow: hidden;
  text-overflow: ellipsis;
}
.purchases-table .cell-title,
.purchases-table .chave-short {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.purchases-table .cell-actions {
  padding-left: 8px;
  padding-right: 8px;
  overflow: visible;
}
.chave-short {
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}
.nowrap {
  white-space: nowrap;
  font-variant-numeric: tabular-nums;
}
.purchases-table tbody tr:hover td {
  background: var(--surface-hover);
}

/* Modal de detalhes */
.detail-modal {
  max-width: 780px;
}

.detail-header h2 {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-sub {
  margin: 4px 0 0;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
}

.detail-body {
  padding: 20px 24px 24px;
}

.detail-supplier {
  margin-bottom: 16px;
}

.detail-supplier span {
  display: block;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.detail-supplier strong {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.detail-money {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  margin: 0 0 16px;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: var(--brand-radius-sm);
  background: var(--surface-hover);
}

.detail-money > div {
  min-width: 0;
}

.detail-money dt {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
  margin-bottom: 4px;
}

.detail-money dd {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.detail-money .is-total dd {
  color: var(--primary-hover);
  font-weight: 800;
}

.detail-chave {
  margin-bottom: 10px;
  padding: 12px 14px;
  border: 1px solid var(--border);
  border-radius: var(--brand-radius-sm);
  background: var(--surface-hover);
}

.detail-chave-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 6px;
}

.detail-chave-head span {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.6px;
  color: var(--text-muted);
}

.chave-copy {
  width: 28px;
  height: 28px;
  font-size: 13px;
}

.detail-chave code {
  display: block;
  font-family: var(--font-mono);
  font-size: 12px;
  color: var(--text-secondary);
  word-break: break-all;
  line-height: 1.6;
}

.detail-body h3 {
  font-size: 15px;
  font-weight: 800;
  letter-spacing: -0.2px;
  margin: 0 0 10px;
}

.detail-table {
  table-layout: fixed;
}

.detail-table .col-qtd {
  width: 70px;
}

.detail-table .col-custo {
  width: 130px;
}

.detail-table .col-total {
  width: 130px;
}

.detail-table tbody td {
  padding: 10px 14px;
  min-width: 0;
}

@media (max-width: 640px) {
  .detail-money {
    grid-template-columns: repeat(2, 1fr);
  }
}

.detail-table .cell-number {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* Menu flutuante via Teleport: fixo na viewport, acima de tudo */
.menu-float {
  position: fixed;
  top: auto;
  right: auto;
  bottom: auto;
  z-index: 1200;
}

@media (max-width: 900px) {
  .purchases-table .col-data {
    display: none;
  }
  .products-toolbar {
    flex-wrap: wrap;
  }
  .products-toolbar .btn-brand {
    width: 100%;
  }
}
@media (max-width: 640px) {
  .purchases-table .col-chave {
    width: 150px;
  }
  .products-toolbar .toolbar-select-status {
    flex: 1 1 45%;
    width: auto;
    min-width: 0;
  }
}
.btn-launch-confirm { background: var(--primary, #2563eb); min-width: 200px; }
.form-row { display: flex; gap: 16px; }
.form-field { margin-bottom: 14px; }
.form-field label { display: block; font-size: 13px; font-weight: 600; color: var(--text-secondary, #666); margin-bottom: 6px; }
.form-field input, .form-field select, .form-field textarea { width: 100%; padding: 9px 12px; border: 1px solid var(--border, #d1d5db); border-radius: 6px; font-size: 14px; }
.form-field input:focus, .form-field select:focus, .form-field textarea:focus { outline: none; border-color: var(--primary, #2563eb); box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15); }
.form-field input:disabled { background: var(--surface-hover, #f3f4f6); color: var(--text-muted, #9ca3af); cursor: not-allowed; }
.form-field textarea { resize: vertical; }
.flex-1 { flex: 1; } .flex-2 { flex: 2; } .flex-3 { flex: 3; }
.items-section { margin: 12px 0; border: 1px solid var(--border, #e5e7eb); border-radius: 8px; padding: 14px 16px; }
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
.li-card { border: 1px solid var(--border, #e5e7eb); border-radius: 8px; padding: 12px 14px; }
.li-card.is-unmatched { border-color: #f59e0b; background: #fffbeb; }
.li-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.li-num { font-size: 12px; color: var(--text-muted, #999); font-weight: 700; }
.li-name { font-size: 14px; font-weight: 700; }
.li-unlink { margin-left: auto; }
.li-meta { display: flex; gap: 14px; flex-wrap: wrap; font-size: 12px; color: var(--text-secondary, #666); margin-top: 4px; }
.match-badge { display: inline-flex; align-items: center; gap: 4px; padding: 3px 8px; border-radius: 4px; font-size: 12px; font-weight: 600; }
.match-badge.is-matched { background: #d1fae5; color: #065f46; }
.match-badge.is-unmatched-badge { background: #fef3c7; color: #92400e; }

.li-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(108px, 1fr));
  gap: 10px 14px;
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px dashed var(--border, #e5e7eb);
}
.li-cell { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.li-cell label { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; color: var(--text-muted, #999); }
.li-readonly { font-size: 14px; color: var(--text, #111827); font-variant-numeric: tabular-nums; }
.li-input {
  width: 100%;
  padding: 7px 10px;
  border: 1px solid var(--border, #d1d5db);
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
  font-variant-numeric: tabular-nums;
}
.li-input:focus { outline: none; border-color: var(--primary, #2563eb); box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15); }
.li-prices { margin-top: 10px; padding-top: 10px; border-top: 1px dashed var(--border, #e5e7eb); display: flex; flex-direction: column; gap: 8px; }
.li-prices-title { font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.4px; color: var(--text-muted, #999); }
.li-price-row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.li-price-name { flex: 1; min-width: 120px; font-size: 13px; font-weight: 600; color: var(--text, #111827); }
.li-price-name small { color: var(--text-muted, #999); font-weight: 500; }
.li-price-input { width: 140px; border-color: var(--primary, #2563eb); }
.li-search { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
.li-search .product-search { flex: 1; }
.margin-badge { display: inline-flex; align-self: flex-start; padding: 3px 10px; border-radius: 6px; font-size: 13px; font-weight: 800; background: #d1fae5; color: #065f46; }
.margin-badge.is-negative { background: #fee2e2; color: #991b1b; }
.item-list { display: flex; flex-direction: column; gap: 8px; }
.launch-totals { display: flex; justify-content: flex-end; gap: 24px; font-size: 14px; margin: 12px 0 8px; padding-top: 8px; border-top: 1px solid var(--border, #e5e7eb); }
.launch-footer-options { display: flex; gap: 20px; align-items: flex-start; margin-top: 4px; padding-top: 14px; border-top: 1px solid var(--border, #e5e7eb); }
.launch-due { flex: 1; margin-bottom: 0; }
.launch-checks { display: flex; flex-direction: column; gap: 10px; padding-top: 24px; }
.launch-check { display: inline-flex; align-items: center; gap: 8px; font-size: 13px; font-weight: 600; color: var(--text, #111827); cursor: pointer; white-space: nowrap; }
.launch-check input { width: 16px; height: 16px; margin: 0; accent-color: var(--primary, #2563eb); cursor: pointer; }
.launch-check.is-disabled { opacity: 0.5; cursor: not-allowed; }
.launch-check.is-disabled input { cursor: not-allowed; }

/* Footer como filho direto do .modal-content (ex.: Lançar Compra): o
   .modal-footer global não tem padding horizontal/inferior; aqui garante. */
.modal-content > .modal-footer {
  margin-top: 0;
  padding: 18px 24px;
}
</style>
