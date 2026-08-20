<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, maskMoney, moneyToDecimal } from '@/utils/format'
import AppShell from '@/components/AppShell.vue'

const data = ref(null)
const loading = ref(false)
const saving = ref(false)
const openMenu = ref(null)

const showProductModal = ref(false)
const editingProduct = ref(null)
const productForm = ref({})

const showAdjustModal = ref(false)
const adjustTarget = ref(null)
const adjustForm = ref({ delta: '', obs: '' })

const showMovementsModal = ref(false)
const movementsData = ref(null)

function toggleMenu(id) {
  openMenu.value = openMenu.value === id ? null : id
}

function closeMenus() {
  openMenu.value = null
}

function blankProduct() {
  return {
    name: '',
    price: '',
    cost: '0,00',
    barcode: '',
    stock_quantity: 0,
    min_stock: 0,
    obs: '',
    active: true,
  }
}

function openNewProduct() {
  editingProduct.value = null
  productForm.value = blankProduct()
  showProductModal.value = true
}

function openEditProduct(product) {
  editingProduct.value = product
  productForm.value = {
    name: product.name,
    price: maskMoney(String(product.price)),
    cost: maskMoney(String(product.cost)),
    barcode: product.barcode || '',
    min_stock: product.min_stock,
    obs: product.obs || '',
    active: product.active,
  }
  showProductModal.value = true
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
    ElMessage.success(editingProduct.value ? 'Produto atualizado!' : 'Produto cadastrado!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
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

async function removeProduct(product) {
  if (!window.confirm(`Excluir o produto "${product.name}"?`)) return
  try {
    data.value = await api.del(`/products/${product.id}`)
    ElMessage.success('Produto excluído.')
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
          <h1 class="page-title">Produtos</h1>
          <p class="page-subtitle">Catálogo do PDV com controle de estoque.</p>
        </div>
        <button type="button" class="btn btn-primary" @click="openNewProduct">
          <i class="fas fa-plus"></i> Novo produto
        </button>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else-if="data">
        <div class="table-card">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Produto</th>
                  <th class="th-amount">Preço</th>
                  <th class="th-amount">Custo</th>
                  <th class="th-number">Estoque</th>
                  <th>Código de barras</th>
                  <th>Status</th>
                  <th class="th-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="product in data.products"
                  :key="product.id"
                  :class="{ 'is-inactive': !product.active }"
                >
                  <td>
                    <span class="cell-title">{{ product.name }}</span>
                    <span v-if="product.obs" class="cell-sub">{{ product.obs }}</span>
                  </td>
                  <td class="cell-amount">{{ brl(product.price) }}</td>
                  <td class="cell-amount">{{ brl(product.cost) }}</td>
                  <td class="cell-stock" :class="{ 'cell-stock-low': product.min_stock && product.stock_quantity <= product.min_stock }">
                    {{ product.stock_quantity }}
                    <span v-if="product.min_stock" class="cell-sub">mín. {{ product.min_stock }}</span>
                  </td>
                  <td class="cell-barcode">{{ product.barcode || '—' }}</td>
                  <td>
                    <span class="status-badge" :class="product.active ? 'is-active' : 'is-inactive'">
                      {{ product.active ? 'Ativo' : 'Inativo' }}
                    </span>
                  </td>
                  <td class="cell-actions">
                    <div class="dropdown">
                      <button
                        type="button"
                        class="icon-btn row-menu-btn"
                        aria-haspopup="true"
                        aria-expanded="false"
                        aria-label="Ações do produto"
                        @click.stop="toggleMenu(product.id)"
                      >
                        <i class="fas fa-ellipsis-h"></i>
                      </button>
                      <div class="dropdown-panel" v-show="openMenu === product.id">
                        <button type="button" class="dropdown-item" @click="openEditProduct(product)">
                          <i class="fas fa-pen"></i> Editar
                        </button>
                        <button type="button" class="dropdown-item" @click="openAdjust(product)">
                          <i class="fas fa-balance-scale"></i> Ajustar estoque
                        </button>
                        <button type="button" class="dropdown-item" @click="openMovements(product)">
                          <i class="fas fa-history"></i> Movimentações
                        </button>
                        <button type="button" class="dropdown-item is-danger" @click="removeProduct(product)">
                          <i class="fas fa-trash"></i> Excluir
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
                <tr v-if="!data.products.length" class="empty-row">
                  <td colspan="7" class="empty-state">
                    <i class="fas fa-box-open"></i>
                    <h3>Nenhum produto cadastrado</h3>
                    <p>Cadastre os itens vendidos no PDV para começar.</p>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <p class="account-hint">
          <i class="fas fa-info-circle"></i>
          Produtos com estoque abaixo do mínimo ficam destacados. Produtos já vendidos não podem ser excluídos.
        </p>
      </template>
    </div>

    <div class="modal" :class="{ 'is-open': showProductModal }">
      <div class="modal-content modal-content-sm">
        <div class="modal-header">
          <h2>{{ editingProduct ? 'Editar produto' : 'Novo produto' }}</h2>
          <button type="button" class="modal-close" aria-label="Fechar" @click="showProductModal = false">&times;</button>
        </div>
        <form class="modal-form" @submit.prevent="saveProduct">
          <div class="form-field">
            <label for="product_name">Nome do produto</label>
            <input id="product_name" v-model="productForm.name" type="text" placeholder="Ex: Coca-Cola 2L" required />
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

          <div class="form-field">
            <label for="product_barcode">Código de barras (opcional)</label>
            <input id="product_barcode" v-model="productForm.barcode" type="text" placeholder="Ex: 7891000112345" />
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
            <input id="product_obs" v-model="productForm.obs" type="text" placeholder="Ex: fornecedor, validade..." />
          </div>

          <label class="form-check">
            <input id="product_active" v-model="productForm.active" type="checkbox" />
            <span>Produto ativo (aparece no PDV)</span>
          </label>

          <div class="modal-footer">
            <button type="button" class="btn btn-ghost modal-cancel" @click="showProductModal = false">Cancelar</button>
            <button type="submit" class="btn btn-primary" :disabled="saving">
              <i class="fas fa-check"></i> {{ saving ? 'Salvando…' : 'Salvar produto' }}
            </button>
          </div>
        </form>
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
  </AppShell>
</template>

<style scoped>
.muted {
  color: var(--text-muted);
  padding: 24px 4px;
}
</style>