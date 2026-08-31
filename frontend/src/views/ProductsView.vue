<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, maskMoney, moneyToDecimal } from '@/utils/format'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const data = ref(null)
const categories = ref([])
const suppliers = ref([])
const loading = ref(false)
const saving = ref(false)

const showProductModal = ref(false)
const editingProduct = ref(null)
const productForm = ref({})
const cloneSource = ref(null)
const detailsTab = ref('dados')
const movementsLoading = ref(false)
const movementsList = ref([])

const showAdjustModal = ref(false)
const adjustTarget = ref(null)
const adjustForm = ref({ delta: '', obs: '' })

const showMovementsModal = ref(false)
const movementsData = ref(null)

const showNewCategory = ref(false)
const newCategoryName = ref('')
const creatingCategory = ref(false)
const deleteTarget = ref(null)
const searchQuery = ref('')
const activeCategoryId = ref(null)

const filteredProducts = computed(() => {
  if (!data.value) return []
  let list = data.value.products || []
  if (activeCategoryId.value !== null) {
    list = list.filter(p => p.category_id === activeCategoryId.value)
  }
  const q = searchQuery.value.trim().toLowerCase()
  if (q) {
    list = list.filter(p =>
      p.name.toLowerCase().includes(q) ||
      (p.barcode || '').toLowerCase().includes(q) ||
      (p.secondary_code || '').toLowerCase().includes(q) ||
      (p.category_name || '').toLowerCase().includes(q)
    )
  }
  return list
})

function blankProduct() {
  return {
    name: '',
    price: '',
    cost: '0,00',
    barcode: '',
    secondary_code: '',
    category_id: null,
    suppliers: '',
    supplier_id: null,
    stock_quantity: 0,
    min_stock: 0,
    obs: '',
    active: true,
  }
}

function openNewProduct() {
  editingProduct.value = null
  productForm.value = blankProduct()
  cloneSource.value = null
  showNewCategory.value = false
  newCategoryName.value = ''
  detailsTab.value = 'dados'
  showProductModal.value = true
}

function openEditProduct(product) {
  editingProduct.value = product
  cloneSource.value = null
  showNewCategory.value = false
  newCategoryName.value = ''
  productForm.value = {
    name: product.name,
    price: maskMoney(String(Math.round(product.price * 100))),
    cost: maskMoney(String(Math.round(product.cost * 100))),
    barcode: product.barcode || '',
    secondary_code: product.secondary_code || '',
    category_id: product.category_id || null,
    suppliers: product.suppliers || '',
    supplier_id: product.supplier_id || null,
    min_stock: product.min_stock,
    obs: product.obs || '',
    active: product.active,
  }
  detailsTab.value = 'dados'
  movementsList.value = []
  showProductModal.value = true
}

async function openDetailsTab(tab) {
  detailsTab.value = tab
  if (tab === 'transacoes' && editingProduct.value && !movementsList.value.length) {
    movementsLoading.value = true
    try {
      const data = await api.get(`/products/${editingProduct.value.id}/movements`)
      movementsList.value = data.movements || []
    } catch (error) {
      ElMessage.error(error.message)
    } finally {
      movementsLoading.value = false
    }
  }
}

function maskPrice(event) {
  productForm.value.price = maskMoney(event.target.value)
}

function maskCost(event) {
  productForm.value.cost = maskMoney(event.target.value)
}

function openAdjust(product) {
  adjustTarget.value = product
  adjustForm.value = { delta: '', obs: '' }
  showAdjustModal.value = true
}

async function openMovements(product) {
  try {
    movementsData.value = await api.get(`/products/${product.id}/movements`)
    showMovementsModal.value = true
  } catch (error) {
    ElMessage.error(error.message)
  }
}

async function load() {
  loading.value = true
  try {
    data.value = await api.get('/products')
  } finally {
    loading.value = false
  }
}

async function createQuickCategory() {
  const name = newCategoryName.value.trim()
  if (!name) return
  creatingCategory.value = true
  try {
    const res = await api.post('/categories', { name })
    categories.value = res.categories || []
    const created = categories.value.find(c => c.name.toLowerCase() === name.toLowerCase())
    if (created) productForm.value.category_id = created.id
    newCategoryName.value = ''
    showNewCategory.value = false
    ElMessage.success('Categoria criada!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    creatingCategory.value = false
  }
}

async function saveProduct() {
  const price = moneyToDecimal(productForm.value.price)
  const cost = moneyToDecimal(productForm.value.cost)
  if (!productForm.value.name || price === null || price < 0 || cost === null || cost < 0) {
    ElMessage.warning('Informe nome, preço e custo válidos.')
    return
  }
  saving.value = true
  try {
    const payload = {
      name: productForm.value.name,
      price: String(price),
      cost: String(cost),
      barcode: productForm.value.barcode,
      secondary_code: productForm.value.secondary_code,
      category_id: productForm.value.category_id,
      suppliers: productForm.value.suppliers,
      supplier_id: productForm.value.supplier_id,
      min_stock: Number(productForm.value.min_stock) || 0,
      obs: productForm.value.obs,
      active: productForm.value.active,
    }
    if (editingProduct.value) {
      data.value = await api.put(`/products/${editingProduct.value.id}`, payload)
    } else {
      payload.stock_quantity = Number(productForm.value.stock_quantity) || 0
      data.value = await api.post('/products', payload)
    }
    showProductModal.value = false
    cloneSource.value = null
    ElMessage.success(editingProduct.value ? 'Produto atualizado!' : 'Produto cadastrado!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

// Clona o produto em edição: preenche o modal como produto novo com as
// mesmas informações (menos o id e o código de barras), sem fechar.
function cloneProduct() {
  if (!editingProduct.value) return
  const product = editingProduct.value
  cloneSource.value = product.name
  editingProduct.value = null
  productForm.value = {
    name: product.name,
    price: maskMoney(String(Math.round(product.price * 100))),
    cost: maskMoney(String(Math.round(product.cost * 100))),
    barcode: '',
    secondary_code: product.secondary_code || '',
    category_id: product.category_id || null,
    suppliers: product.suppliers || '',
    supplier_id: product.supplier_id || null,
    stock_quantity: 0,
    min_stock: product.min_stock,
    obs: product.obs || '',
    active: product.active,
  }
  detailsTab.value = 'dados'
  movementsList.value = []
  ElMessage.info('Altere as informações e salve o novo produto.')
}

async function saveAdjust() {
  const delta = Number(adjustForm.value.delta)
  if (!delta) {
    ElMessage.warning('Informe a quantidade (use sinal - para saída).')
    return
  }
  saving.value = true
  try {
    data.value = await api.post(`/products/${adjustTarget.value.id}/adjust`, {
      delta,
      obs: adjustForm.value.obs,
    })
    showAdjustModal.value = false
    ElMessage.success('Estoque ajustado!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

function removeProduct(product) {
  deleteTarget.value = product
}

async function confirmDelete() {
  const product = deleteTarget.value
  deleteTarget.value = null
  if (!product) return
  try {
    data.value = await api.del(`/products/${product.id}`)
    ElMessage.success('Produto excluído.')
  } catch (error) {
    ElMessage.error(error.message)
  }
}

function deleteMessage() {
  return 'Excluir o produto "' + (deleteTarget.value?.name || '') + '"? Essa ação não pode ser desfeita.'
}

onMounted(async () => {
  load()
  try {
    const res = await api.get('/categories')
    categories.value = res.categories || []
  } catch { /* ignora */ }
  try {
    const res = await api.get('/products')
    suppliers.value = res.suppliers || []
  } catch { /* ignora */ }
  document.addEventListener('keydown', onModalKeydown)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onModalKeydown)
})

// No modal de produto, Enter (leitor de código de barras) não salva:
// só F2 ou o botão "Salvar produto".
function onModalKeydown(event) {
  if (event.key === 'F2' && showProductModal.value && detailsTab.value === 'dados') {
    event.preventDefault()
    saveProduct()
  }
}
</script>

<template>
  <AppShell>
    <div class="dashboard products-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">Produtos</h1>
          <p class="page-subtitle">Catálogo do PDV com controle de estoque.</p>
        </div>
        <button type="button" class="btn btn-primary" @click="openNewProduct">
          <i class="fas fa-plus"></i> Novo produto
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="products-layout">
          <aside class="products-sidebar">
            <h3 class="sidebar-title">Categorias</h3>
            <ul class="sidebar-list">
              <li>
                <button
                  type="button"
                  class="sidebar-item"
                  :class="{ 'is-active': activeCategoryId === null }"
                  @click="activeCategoryId = null"
                >
                  <i class="fas fa-layer-group"></i> Todos
                  <span class="sidebar-count">{{ data.products.length }}</span>
                </button>
              </li>
              <li v-for="cat in categories.filter(c => c.active)" :key="cat.id">
                <button
                  type="button"
                  class="sidebar-item"
                  :class="{ 'is-active': activeCategoryId === cat.id }"
                  @click="activeCategoryId = cat.id"
                >
                  {{ cat.name }}
                  <span class="sidebar-count">{{ data.products.filter(p => p.category_id === cat.id).length }}</span>
                </button>
              </li>
            </ul>
          </aside>

          <div class="products-main">
            <div class="products-search">
              <i class="fas fa-search"></i>
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Buscar por nome, código ou categoria..."
              />
              <button
                v-if="searchQuery"
                type="button"
                class="search-clear"
                @click="searchQuery = ''"
              >
                <i class="fas fa-times"></i>
              </button>
            </div>

            <div class="table-card">
              <div class="table-container">
                <table class="data-table">
                  <thead>
                    <tr>
                      <th>Produto</th>
                      <th class="th-amount">Preço</th>
                      <th class="th-number">Estoque</th>
                      <th class="th-actions"></th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="product in filteredProducts"
                      :key="product.id"
                      :class="{ 'is-active': product.active, 'is-inactive': !product.active }"
                    >
                      <td>
                        <span class="cell-title">{{ product.name }}</span>
                        <span v-if="product.category_name" class="cell-sub">{{ product.category_name }}</span>
                        <span v-else-if="product.obs" class="cell-sub">{{ product.obs }}</span>
                      </td>
                      <td class="cell-amount">{{ brl(product.price) }}</td>
                      <td class="cell-stock" :class="{ 'cell-stock-low': product.min_stock && product.stock_quantity <= product.min_stock }">
                        {{ product.stock_quantity }}
                        <span v-if="product.min_stock" class="cell-sub">mín. {{ product.min_stock }}</span>
                      </td>
                      <td class="cell-actions">
                        <div class="product-actions">
                      <button
                        type="button"
                        class="icon-btn"
                        title="Editar"
                        aria-label="Editar produto"
                        @click="openEditProduct(product)"
                      >
                        <i class="fas fa-pen"></i>
                      </button>
                      <button
                        type="button"
                        class="icon-btn"
                        title="Ajustar estoque"
                        aria-label="Ajustar estoque"
                        @click="openAdjust(product)"
                      >
                        <i class="fas fa-balance-scale"></i>
                      </button>
                      <button
                        type="button"
                        class="icon-btn"
                        title="Movimentações"
                        aria-label="Movimentações"
                        @click="openMovements(product)"
                      >
                        <i class="fas fa-history"></i>
                      </button>
                      <button
                        type="button"
                        class="icon-btn is-danger"
                        title="Excluir"
                        aria-label="Excluir produto"
                        @click="removeProduct(product)"
                      >
                        <i class="fas fa-trash"></i>
                      </button>
                    </div>
                  </td>
                </tr>
                <tr v-if="!filteredProducts.length" class="empty-row">
                  <td colspan="4" class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <h3 v-if="searchQuery || activeCategoryId !== null">Nenhum produto encontrado</h3>
                    <h3 v-else>Nenhum produto cadastrado</h3>
                    <p v-if="searchQuery || activeCategoryId !== null">Tente outros filtros ou limpe a busca.</p>
                    <p v-else>Cadastre os itens vendidos no PDV para começar.</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
          </div>
        </div>

        <p class="account-hint">
          <i class="fas fa-info-circle"></i>
          Produtos com estoque abaixo do mínimo ficam destacados. Produtos já vendidos não podem ser excluídos.
        </p>
      </template>
    </div>

    <div class="modal" :class="{ 'is-open': showProductModal }">
      <div class="modal-content modal-content-wide">
        <div class="modal-header">
          <h2>{{ editingProduct ? 'Detalhes do produto' : 'Novo produto' }}</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="showProductModal = false">&times;</button>
        </div>

        <p v-if="cloneSource" class="clone-hint">
          <i class="fas fa-clone"></i> Clonando de "{{ cloneSource }}" — altere o que precisar e salve.
        </p>

        <div class="modal-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            :class="{ 'is-active': detailsTab === 'dados' }"
            @click="detailsTab = 'dados'"
          >
            <i class="fas fa-box"></i> Dados
          </button>
          <button
            type="button"
            role="tab"
            :class="{ 'is-active': detailsTab === 'transacoes' }"
            @click="openDetailsTab('transacoes')"
          >
            <i class="fas fa-history"></i> Transações
          </button>
        </div>

        <form
          v-show="detailsTab === 'dados'"
          class="modal-form"
          @submit.prevent="saveProduct"
          @keydown.enter.prevent
        >
          <div class="form-grid" v-if="editingProduct">
            <div class="form-field">
              <label>Código (ID)</label>
              <input type="text" :value="'#' + editingProduct.id" readonly />
            </div>
            <div class="form-field">
              <label for="product_name">Nome do produto</label>
              <input id="product_name" v-model="productForm.name" type="text" placeholder="Ex: Coca-Cola 2L" required />
            </div>
          </div>

          <div class="form-field" v-else>
            <label for="product_name">Nome do produto</label>
            <input id="product_name" v-model="productForm.name" type="text" placeholder="Ex: Coca-Cola 2L" required />
          </div>

          <div class="form-grid">
            <div class="form-field">
              <label for="product_barcode">Código de barras (EAN)</label>
              <input id="product_barcode" v-model="productForm.barcode" type="text" placeholder="Opcional..." />
            </div>
            <div class="form-field">
              <label for="product_secondary_code">Código secundário</label>
              <input id="product_secondary_code" v-model="productForm.secondary_code" type="text" placeholder="Opcional..." />
            </div>
          </div>

          <div class="form-grid">
            <div class="form-field">
              <label for="product_category">Categoria</label>
              <div class="category-row">
                <select id="product_category" v-model="productForm.category_id">
                  <option :value="null">Sem categoria</option>
                  <option
                    v-for="cat in categories.filter(c => c.active)"
                    :key="cat.id"
                    :value="cat.id"
                  >{{ cat.name }}</option>
                </select>
                <button
                  type="button"
                  class="icon-btn category-add-btn"
                  title="Nova categoria"
                  aria-label="Adicionar nova categoria"
                  @click="showNewCategory = !showNewCategory"
                >
                  <i class="fas fa-plus"></i>
                </button>
              </div>
              <div v-if="showNewCategory" class="category-inline">
                <input
                  v-model="newCategoryName"
                  type="text"
                  placeholder="Nome da categoria..."
                  class="category-inline-input"
                  @keydown.enter.prevent="createQuickCategory"
                  @keydown.escape="showNewCategory = false"
                />
                <button
                  type="button"
                  class="icon-btn"
                  title="Criar categoria"
                  :disabled="creatingCategory || !newCategoryName.trim()"
                  @click="createQuickCategory"
                >
                  <i class="fas fa-check"></i>
                </button>
              </div>
            </div>
            <div class="form-field">
              <label for="product_supplier">Fornecedor</label>
              <select id="product_supplier" v-model="productForm.supplier_id">
                <option :value="null">Sem fornecedor</option>
                <option
                  v-for="sup in suppliers.filter(s => s.active)"
                  :key="sup.id"
                  :value="sup.id"
                >{{ sup.name }}</option>
              </select>
            </div>
          </div>

          <div class="form-grid">
            <div class="form-field">
              <label for="product_price">Preço (R$)</label>
              <input id="product_price" :value="productForm.price" type="text" placeholder="0,00" inputmode="decimal" required @input="maskPrice" />
            </div>
            <div class="form-field">
              <label for="product_cost">Custo (R$)</label>
              <input id="product_cost" :value="productForm.cost" type="text" placeholder="0,00" inputmode="decimal" required @input="maskCost" />
            </div>
          </div>

          <div class="form-grid">
            <div class="form-field">
              <label for="product_stock">Estoque {{ editingProduct ? '' : 'inicial' }}</label>
              <input
                id="product_stock"
                v-model="productForm.stock_quantity"
                type="number"
                min="0"
                :disabled="!!editingProduct"
              />
            </div>
            <div class="form-field">
              <label for="product_min_stock">Estoque mínimo</label>
              <input id="product_min_stock" v-model="productForm.min_stock" type="number" min="0" />
            </div>
          </div>

          <div class="form-field">
            <label for="product_obs">Observações (opcional)</label>
            <input id="product_obs" v-model="productForm.obs" type="text" placeholder="Ex: validade, lote..." />
          </div>

          <label class="form-check">
            <input id="product_active" v-model="productForm.active" type="checkbox" />
            <span>Produto ativo (aparece no PDV)</span>
          </label>

          <div class="modal-footer">
            <button
              v-if="editingProduct"
              type="button"
              class="btn btn-ghost modal-clone"
              :disabled="saving"
              @click="cloneProduct"
            >
              <i class="fas fa-clone"></i> Clonar
            </button>
            <button type="button" class="btn btn-ghost modal-cancel" @click="showProductModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Salvar produto' }}
            </button>
          </div>
        </form>

        <div v-show="detailsTab === 'transacoes'" class="modal-body product-movements">
          <p v-if="editingProduct" class="adjust-current-stock">
            {{ editingProduct.name }} — estoque atual: {{ editingProduct.stock_quantity }} unidade(s)
          </p>
          <p v-if="movementsLoading" class="muted">Carregando movimentações…</p>
          <table v-else-if="movementsList.length" class="data-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Tipo</th>
                <th class="th-number">Qtd</th>
                <th>Motivo</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="move in movementsList" :key="move.id">
                <td class="cell-sub">{{ move.date.replace('T', ' ').slice(0, 16) }}</td>
                <td>
                  <span class="status-badge" :class="move.quantity >= 0 ? 'is-active' : 'is-inactive'">
                    {{ move.movement_type }}
                  </span>
                </td>
                <td class="cell-number">{{ move.quantity >= 0 ? '+' : '' }}{{ move.quantity }}</td>
                <td class="cell-obs">{{ move.obs || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="adjust-current-stock">Nenhuma movimentação registrada.</p>
        </div>
      </div>
    </div>

    <div class="modal" :class="{ 'is-open': showAdjustModal }">
      <div class="modal-content modal-content-sm">
        <div class="modal-header">
          <h2>Ajustar estoque</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="showAdjustModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="saveAdjust">
          <p class="adjust-product-name">{{ adjustTarget?.name }}</p>
          <p class="adjust-current-stock">Estoque atual: {{ adjustTarget?.stock_quantity }} unidade(s)</p>

          <div class="form-field">
            <label for="adjust_delta">Quantidade (use sinal - para saída)</label>
            <input id="adjust_delta" v-model="adjustForm.delta" type="number" placeholder="Ex: 10 ou -5" required />
          </div>

          <div class="form-field">
            <label for="adjust_obs">Motivo (opcional)</label>
            <input id="adjust_obs" v-model="adjustForm.obs" type="text" placeholder="Ex: quebra, entrada de mercadoria..." />
          </div>

          <div class="modal-footer">
            <button type="button" class="btn btn-ghost modal-cancel" @click="showAdjustModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Aplicando…' : 'Aplicar ajuste' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <div class="modal" :class="{ 'is-open': showMovementsModal }">
      <div class="modal-content modal-content-sm">
        <div class="modal-header">
          <h2>Movimentações</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="showMovementsModal = false">&times;</button>
        </div>
        <div class="modal-body">
          <p class="adjust-product-name">{{ movementsData?.name }}</p>
          <p class="adjust-current-stock">Estoque atual: {{ movementsData?.stock_quantity }} unidade(s)</p>
          <table v-if="movementsData?.movements?.length" class="data-table">
            <thead>
              <tr>
                <th>Data</th>
                <th>Tipo</th>
                <th class="th-number">Qtd</th>
                <th>Motivo</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="move in movementsData.movements" :key="move.id">
                <td class="cell-sub">{{ move.date.replace('T', ' ').slice(0, 16) }}</td>
                <td>
                  <span class="status-badge" :class="move.quantity >= 0 ? 'is-active' : 'is-inactive'">
                    {{ move.movement_type }}
                  </span>
                </td>
                <td class="cell-number">{{ move.quantity >= 0 ? '+' : '' }}{{ move.quantity }}</td>
                <td class="cell-obs">{{ move.obs || '—' }}</td>
              </tr>
            </tbody>
          </table>
          <p v-else class="adjust-current-stock">Nenhuma movimentação registrada.</p>
        </div>
      </div>
    </div>
    <ConfirmDialog
      v-if="deleteTarget"
      title="Excluir produto"
      :message="deleteMessage()"
      confirm-label="Excluir"
      danger
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
.product-actions {
  display: flex;
  gap: 2px;
  justify-content: flex-end;
}
.product-actions .icon-btn {
  width: 32px;
  height: 32px;
  font-size: 14px;
}
.product-actions .icon-btn.is-danger {
  color: var(--danger, #dc2626);
}
.product-actions .icon-btn.is-danger:hover {
  background: color-mix(in srgb, var(--danger, #dc2626) 10%, transparent);
  color: var(--danger, #dc2626);
}
.category-row {
  display: flex;
  gap: 4px;
}
.category-row select {
  flex: 1;
}
.category-add-btn {
  width: 36px;
  height: 36px;
  flex-shrink: 0;
  border: 1px dashed var(--border, #ccc);
  border-radius: 6px;
  color: var(--primary, #2563eb);
}
.category-add-btn:hover {
  background: color-mix(in srgb, var(--primary, #2563eb) 10%, transparent);
}
.category-inline {
  display: flex;
  gap: 4px;
  margin-top: 6px;
}
.category-inline-input {
  flex: 1;
  padding: 6px 10px;
  border: 1px solid var(--border, #ccc);
  border-radius: 6px;
  font-size: 13px;
}
.category-inline .icon-btn {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  color: var(--primary, #2563eb);
}
.category-inline .icon-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

/* Products layout: sidebar + main */
.products-page {
  padding-left: 0;
  padding-right: 0;
}
.products-page .page-header {
  padding: 0 24px;
}
.products-page .account-hint {
  padding: 0 24px;
}
.products-layout {
  display: flex;
  gap: 0;
}
.products-sidebar {
  width: 210px;
  flex-shrink: 0;
  padding: 0 20px 0 0;
  border-right: 1px solid var(--border, #e5e7eb);
}
.sidebar-title {
  font-size: 12px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted, #999);
  margin: 0 0 8px 8px;
  font-weight: 600;
}
.sidebar-list {
  list-style: none;
  padding: 0;
  margin: 0;
  background: var(--surface, #fff);
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 10px;
  overflow: hidden;
}
.sidebar-item {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 10px 14px;
  border: none;
  background: none;
  color: var(--text, #333);
  font-size: 14px;
  cursor: pointer;
  text-align: left;
  border-bottom: 1px solid var(--border, #f0f0f0);
}
.sidebar-item:last-child {
  border-bottom: none;
}
.sidebar-item:hover {
  background: var(--hover, #f5f5f5);
}
.sidebar-item.is-active {
  background: color-mix(in srgb, var(--primary, #2563eb) 8%, transparent);
  color: var(--primary, #2563eb);
  font-weight: 600;
}
.sidebar-item i {
  width: 16px;
  text-align: center;
  font-size: 12px;
}
.sidebar-count {
  margin-left: auto;
  font-size: 12px;
  color: var(--text-muted, #999);
  background: var(--bg, #f3f4f6);
  padding: 1px 8px;
  border-radius: 10px;
}

/* Search bar */
.products-main {
  flex: 1;
  min-width: 0;
  padding: 0 24px;
}
.products-search {
  position: relative;
  margin-bottom: 16px;
}
.products-search i.fa-search {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--text-muted, #999);
  font-size: 14px;
  pointer-events: none;
}
.products-search input {
  width: 100%;
  padding: 10px 36px 10px 40px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
  font-size: 14px;
  background: var(--surface, #fff);
  color: var(--text, #333);
  outline: none;
  transition: border-color 0.15s;
}
.products-search input:focus {
  border-color: var(--primary, #2563eb);
}
.search-clear {
  position: absolute;
  right: 8px;
  top: 50%;
  transform: translateY(-50%);
  background: none;
  border: none;
  color: var(--text-muted, #999);
  cursor: pointer;
  padding: 4px;
  font-size: 13px;
}
.search-clear:hover {
  color: var(--text, #333);
}
</style>