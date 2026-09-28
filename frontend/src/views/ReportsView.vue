<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { brl, brdateShort } from '@/utils/format'
import { normalizeForSearch } from '@/utils/normalize'
import AppShell from '@/components/AppShell.vue'
import ConfirmDialog from '@/components/ConfirmDialog.vue'

const activeTab = ref('movements')
const tabs = [
  { id: 'movements', label: 'Movimentações', icon: 'fas fa-exchange-alt' },
  { id: 'low', label: 'Estoque baixo', icon: 'fas fa-exclamation-triangle' },
  { id: 'inventory', label: 'Inventário', icon: 'fas fa-clipboard-check' },
]

const MOVEMENT_LIMIT = 100
const typeLabels = {
  entrada: 'Entrada',
  saida: 'Saída',
  ajuste: 'Ajuste',
}

const movements = ref([])
const movementsTotal = ref(0)
const movementsLoading = ref(false)
const movFilters = ref({ type: '', date_from: '', date_to: '', product: null })

function buildMovementsQuery(limit, offset) {
  const params = new URLSearchParams()
  const filters = movFilters.value
  if (filters.type) params.set('type', filters.type)
  if (filters.date_from) params.set('date_from', filters.date_from)
  if (filters.date_to) params.set('date_to', filters.date_to)
  if (filters.product) params.set('product_id', String(filters.product.id))
  params.set('limit', String(limit))
  params.set('offset', String(offset))
  return params.toString()
}

async function loadMovements(reset = true) {
  movementsLoading.value = true
  try {
    const offset = reset ? 0 : movements.value.length
    const data = await api.get(
      `/reports/movements?${buildMovementsQuery(MOVEMENT_LIMIT, offset)}`
    )
    movements.value = reset
      ? data.movements
      : [...movements.value, ...data.movements]
    movementsTotal.value = data.total
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    movementsLoading.value = false
  }
}

const hasMoreMovements = computed(() => movements.value.length < movementsTotal.value)

const productQuery = ref('')
const productResults = ref([])
let productSearchTimer = null

async function searchFilterProduct() {
  const query = productQuery.value.trim()
  if (!query) {
    productResults.value = []
    return
  }
  try {
    const data = await api.get(`/products/search?q=${encodeURIComponent(query)}`)
    productResults.value = data.products
  } catch {
    productResults.value = []
  }
}

function onProductQuery() {
  clearTimeout(productSearchTimer)
  productSearchTimer = setTimeout(searchFilterProduct, 250)
}

function selectFilterProduct(product) {
  movFilters.value.product = product
  productQuery.value = ''
  productResults.value = []
  loadMovements(true)
}

function clearFilterProduct() {
  movFilters.value.product = null
  loadMovements(true)
}

async function exportMovementsCsv() {
  try {
    const data = await api.get(`/reports/movements?${buildMovementsQuery(500, 0)}`)
    const escape = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`
    const lines = ['Data;Produto;Tipo;Quantidade;Observação']
    for (const m of data.movements) {
      lines.push(
        [
          escape(m.created_at),
          escape(m.product_name),
          escape(typeLabels[m.movement_type] || m.movement_type),
          escape(m.quantity),
          escape(m.obs),
        ].join(';')
      )
    }
    const blob = new Blob(['\uFEFF' + lines.join('\n')], {
      type: 'text/csv;charset=utf-8;',
    })
    const link = document.createElement('a')
    link.href = URL.createObjectURL(blob)
    link.download = 'movimentacoes-estoque.csv'
    link.click()
    URL.revokeObjectURL(link.href)
  } catch (error) {
    ElMessage.error(error.message)
  }
}

const lowStock = ref(null)
const lowLoading = ref(false)

async function loadLowStock() {
  lowLoading.value = true
  try {
    lowStock.value = await api.get('/reports/low-stock')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    lowLoading.value = false
  }
}

const inventoryProducts = ref([])
const inventoryLoading = ref(false)
const inventorySearch = ref('')
const counted = ref({})
const confirmInventory = ref(false)
const applyingInventory = ref(false)

async function loadInventory() {
  inventoryLoading.value = true
  try {
    const data = await api.get('/products')
    inventoryProducts.value = (data.products || []).filter((p) => p.active)
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    inventoryLoading.value = false
  }
}

const inventoryFiltered = computed(() => {
  const query = normalizeForSearch(inventorySearch.value)
  if (!query) return inventoryProducts.value
  return inventoryProducts.value.filter(
    (p) =>
      normalizeForSearch(p.name).includes(query) ||
      normalizeForSearch(p.barcode || '').includes(query)
  )
})

function countedValue(product) {
  const raw = counted.value[product.id]
  if (raw === undefined || raw === '') return null
  const value = Number(raw)
  if (Number.isNaN(value) || value < 0) return null
  return value
}

const pendingChanges = computed(() =>
  inventoryProducts.value.filter((product) => {
    const value = countedValue(product)
    return value !== null && value !== product.stock_quantity
  })
)

const pendingCount = computed(() => pendingChanges.value.length)

async function applyInventory() {
  confirmInventory.value = false
  applyingInventory.value = true
  try {
    const items = pendingChanges.value.map((product) => ({
      product_id: product.id,
      counted: countedValue(product),
    }))
    const result = await api.post('/inventory/count', { items })
    ElMessage.success(
      `Contagem aplicada: ${result.adjusted} produto(s) ajustado(s).`
    )
    counted.value = {}
    await loadInventory()
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    applyingInventory.value = false
  }
}

function selectTab(tabId) {
  activeTab.value = tabId
  if (tabId === 'low' && lowStock.value === null) loadLowStock()
  if (tabId === 'inventory' && !inventoryProducts.value.length) loadInventory()
}

onMounted(() => {
  loadMovements(true)
})
</script>

<template>
  <AppShell>
    <div class="dashboard reports-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">Relatórios</h1>
          <p class="page-subtitle">
            Movimentações de estoque, pontos baixos e contagem de inventário.
          </p>
        </div>
      </div>

      <div class="filter-segmented reports-tabs" role="tablist" aria-label="Relatórios de estoque">
        <button
          v-for="tab in tabs"
          :key="tab.id"
          type="button"
          role="tab"
          :aria-selected="activeTab === tab.id"
          :class="{ 'is-active': activeTab === tab.id }"
          @click="selectTab(tab.id)"
        >
          <i :class="tab.icon"></i> {{ tab.label }}
        </button>
      </div>

      <!-- Movimentações -->
      <section v-show="activeTab === 'movements'" class="reports-section" data-tab="movements">
        <div class="products-toolbar reports-filters">
          <select
            v-model="movFilters.type"
            class="toolbar-select toolbar-select-status"
            aria-label="Filtrar por tipo"
            @change="loadMovements(true)"
          >
            <option value="">Todos os tipos</option>
            <option value="entrada">Entradas</option>
            <option value="saida">Saídas</option>
            <option value="ajuste">Ajustes</option>
          </select>
          <label class="date-field">
            <span>De</span>
            <input
              v-model="movFilters.date_from"
              type="date"
              aria-label="Data inicial"
              @change="loadMovements(true)"
            />
          </label>
          <label class="date-field">
            <span>Até</span>
            <input
              v-model="movFilters.date_to"
              type="date"
              aria-label="Data final"
              @change="loadMovements(true)"
            />
          </label>
          <div class="reports-product-filter">
            <div v-if="movFilters.product" class="product-chip">
              <span>{{ movFilters.product.name }}</span>
              <button type="button" aria-label="Limpar produto" @click="clearFilterProduct">
                <i class="fas fa-times"></i>
              </button>
            </div>
            <div v-else class="search-box">
              <i class="fas fa-search"></i>
              <input
                v-model="productQuery"
                type="text"
                placeholder="Filtrar por produto..."
                aria-label="Filtrar por produto"
                @input="onProductQuery"
              />
            </div>
            <ul v-if="productResults.length" class="product-results">
              <li v-for="product in productResults" :key="product.id">
                <button type="button" @click="selectFilterProduct(product)">
                  {{ product.name }}
                </button>
              </li>
            </ul>
          </div>
          <button type="button" class="btn btn-ghost" @click="exportMovementsCsv">
            <i class="fas fa-file-csv"></i> Exportar CSV
          </button>
        </div>

        <div v-if="movementsLoading && !movements.length" class="muted">Carregando…</div>
        <div v-else class="table-card">
          <div class="table-container">
            <table class="data-table reports-table">
              <thead>
                <tr>
                  <th class="col-date">Data</th>
                  <th>Produto</th>
                  <th class="col-type">Tipo</th>
                  <th class="col-qty">Qtd</th>
                  <th class="col-obs">Observação</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="movement in movements" :key="movement.id">
                  <td class="col-date">{{ brdateShort(movement.created_at) }}</td>
                  <td>{{ movement.product_name }}</td>
                  <td class="col-type">
                    <span class="mv-badge" :class="`is-${movement.movement_type}`">
                      {{ typeLabels[movement.movement_type] || movement.movement_type }}
                    </span>
                  </td>
                  <td class="col-qty" :class="`qty-${movement.movement_type}`">
                    {{
                      movement.movement_type === 'entrada' ? '+' : movement.movement_type === 'saida' ? '−' : ''
                    }}
                    {{ Math.abs(movement.quantity) }}
                  </td>
                  <td class="col-obs cell-ellipsis">{{ movement.obs || '—' }}</td>
                </tr>
                <tr v-if="!movements.length">
                  <td colspan="5" class="empty-row">Nenhuma movimentação encontrada.</td>
                </tr>
              </tbody>
            </table>
          </div>
          <div class="reports-table-footer">
            <span class="muted">
              {{ movements.length }} de {{ movementsTotal }} movimentação(ões)
            </span>
            <button
              v-if="hasMoreMovements"
              type="button"
              class="btn btn-ghost"
              :disabled="movementsLoading"
              @click="loadMovements(false)"
            >
              Carregar mais
            </button>
          </div>
        </div>
      </section>

      <!-- Estoque baixo -->
      <section v-show="activeTab === 'low'" class="reports-section" data-tab="low">
        <div v-if="lowStock === null || lowLoading" class="muted">Carregando…</div>
        <template v-else>
          <div class="reports-stats">
            <div class="stat-card">
              <span class="stat-label">Produtos críticos</span>
              <span class="stat-value">{{ lowStock.count }}</span>
            </div>
            <div class="stat-card">
              <span class="stat-label">Zerados</span>
              <span class="stat-value">
                {{ lowStock.products.filter((p) => p.out_of_stock).length }}
              </span>
            </div>
          </div>
          <div class="table-card">
            <div class="table-container">
              <table class="data-table reports-table">
                <thead>
                  <tr>
                    <th>Produto</th>
                    <th class="col-cat">Categoria</th>
                    <th class="col-qty">Atual</th>
                    <th class="col-qty">Mínimo</th>
                    <th class="col-qty">Ideal</th>
                    <th class="col-qty">Déficit</th>
                    <th class="col-status">Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="product in lowStock.products" :key="product.id">
                    <td>{{ product.name }}</td>
                    <td class="col-cat">{{ product.category_name || '—' }}</td>
                    <td class="col-qty">{{ product.stock_quantity }}</td>
                    <td class="col-qty">{{ product.min_stock }}</td>
                    <td class="col-qty">{{ product.ideal_stock }}</td>
                    <td class="col-qty">{{ product.deficit || '—' }}</td>
                    <td class="col-status">
                      <span
                        class="mv-badge"
                        :class="
                          product.out_of_stock || product.stock_quantity < 0
                            ? 'is-saida'
                            : 'is-ajuste'
                        "
                      >
                        {{
                          product.out_of_stock
                            ? 'Zerado'
                            : product.stock_quantity < 0
                              ? 'Negativo'
                              : 'Abaixo do mínimo'
                        }}
                      </span>
                    </td>
                  </tr>
                  <tr v-if="!lowStock.products.length">
                    <td colspan="7" class="empty-row">
                      Nenhum produto abaixo do mínimo. Tudo certo por aqui!
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </template>
      </section>

      <!-- Inventário -->
      <section v-show="activeTab === 'inventory'" class="reports-section" data-tab="inventory">
        <div class="reports-note">
          <i class="fas fa-info-circle"></i>
          Digite a quantidade contada de cada produto. Somente os campos preenchidos
          são ajustados; os demais permanecem intactos.
        </div>

        <div class="products-toolbar reports-filters">
          <div class="search-box products-search-box">
            <i class="fas fa-search"></i>
            <input
              v-model="inventorySearch"
              type="text"
              placeholder="Buscar produto para contar..."
              aria-label="Buscar produto"
            />
            <button
              v-if="inventorySearch"
              type="button"
              class="search-clear"
              aria-label="Limpar busca"
              @click="inventorySearch = ''"
            >
              <i class="fas fa-times"></i>
            </button>
          </div>
          <button
            type="button"
            class="btn-brand"
            :disabled="!pendingCount || applyingInventory"
            @click="confirmInventory = true"
          >
            <i class="fas fa-check"></i>
            Aplicar contagem
            <span v-if="pendingCount" class="pending-pill">{{ pendingCount }}</span>
          </button>
        </div>

        <div v-if="inventoryLoading" class="muted">Carregando…</div>
        <div v-else class="table-card">
          <div class="table-container">
            <table class="data-table reports-table inventory-table">
              <thead>
                <tr>
                  <th>Produto</th>
                  <th class="col-qty">Estoque atual</th>
                  <th class="col-count">Contado</th>
                  <th class="col-diff">Diferença</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="product in inventoryFiltered" :key="product.id">
                  <td>{{ product.name }}</td>
                  <td class="col-qty">{{ product.stock_quantity }}</td>
                  <td class="col-count">
                    <input
                      :value="counted[product.id] ?? ''"
                      type="number"
                      min="0"
                      step="1"
                      class="count-input"
                      :aria-label="`Contagem de ${product.name}`"
                      @input="counted[product.id] = $event.target.value"
                    />
                  </td>
                  <td
                    class="col-diff"
                    :class="{
                      'diff-positive': countedValue(product) !== null && countedValue(product) > product.stock_quantity,
                      'diff-negative': countedValue(product) !== null && countedValue(product) < product.stock_quantity,
                      'diff-equal': countedValue(product) === product.stock_quantity,
                    }"
                  >
                    <template v-if="countedValue(product) === null">—</template>
                    <template v-else-if="countedValue(product) === product.stock_quantity">
                      igual
                    </template>
                    <template v-else>
                      {{
                        countedValue(product) - product.stock_quantity > 0 ? '+' : ''
                      }}{{ countedValue(product) - product.stock_quantity }}
                    </template>
                  </td>
                </tr>
                <tr v-if="!inventoryFiltered.length">
                  <td colspan="4" class="empty-row">Nenhum produto encontrado.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <ConfirmDialog
        v-if="confirmInventory"
        title="Aplicar contagem do inventário?"
        message="O estoque será ajustado para os valores contados e cada alteração ficará registrada no histórico de movimentações."
        confirm-label="Aplicar"
        :summary="[
          { label: 'Produtos contados', value: String(pendingCount) },
          {
            label: 'Ajustes a aplicar',
            value: String(pendingChanges.length),
          },
        ]"
        @confirm="applyInventory"
        @cancel="confirmInventory = false"
      />
    </div>
  </AppShell>
</template>

<style scoped>
.reports-tabs {
  margin-bottom: 18px;
}

.reports-filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}

.date-field {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 0.85rem;
  color: var(--text-muted, #6b7280);
}

.date-field input {
  padding: 8px 10px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
  background: #fff;
  font-size: 0.85rem;
}

.reports-product-filter {
  position: relative;
  min-width: 220px;
}

.product-chip {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 999px;
  background: #eef2ff;
  font-size: 0.85rem;
}

.product-chip button {
  border: 0;
  background: none;
  cursor: pointer;
  color: inherit;
  padding: 0;
}

.product-results {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  z-index: 30;
  background: #fff;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 10px;
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.08);
  max-height: 220px;
  overflow-y: auto;
  padding: 4px;
  margin: 0;
  list-style: none;
}

.product-results button {
  width: 100%;
  text-align: left;
  border: 0;
  background: none;
  padding: 8px 10px;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.88rem;
}

.product-results button:hover {
  background: #f3f4f6;
}

.reports-stats {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
}

.reports-note {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 10px 14px;
  border-radius: 10px;
  background: #eff6ff;
  color: #1d4ed8;
  font-size: 0.88rem;
  margin-bottom: 16px;
}

.reports-table .col-date {
  width: 96px;
}
.reports-table .col-type {
  width: 110px;
}
.reports-table .col-qty {
  width: 80px;
  text-align: center;
}
.reports-table .col-cat {
  width: 150px;
}
.reports-table .col-status {
  width: 150px;
}
.reports-table .col-count {
  width: 130px;
}
.reports-table .col-diff {
  width: 110px;
  text-align: center;
  font-weight: 600;
}
.reports-table .col-obs {
  max-width: 240px;
}
.reports-table .empty-row {
  text-align: center;
  color: var(--text-muted, #6b7280);
  padding: 26px 0 !important;
}

.mv-badge {
  display: inline-block;
  padding: 3px 9px;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 600;
}
.mv-badge.is-entrada {
  background: #dcfce7;
  color: #15803d;
}
.mv-badge.is-saida {
  background: #fee2e2;
  color: #b91c1c;
}
.mv-badge.is-ajuste {
  background: #dbeafe;
  color: #1d4ed8;
}

.qty-entrada {
  color: #15803d;
  font-weight: 600;
}
.qty-saida {
  color: #b91c1c;
  font-weight: 600;
}

.reports-table-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-top: 1px solid var(--border, #e5e7eb);
}

.count-input {
  width: 92px;
  padding: 7px 9px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: 8px;
  font-size: 0.88rem;
  text-align: center;
}

.diff-positive {
  color: #15803d;
}
.diff-negative {
  color: #b91c1c;
}
.diff-equal {
  color: var(--text-muted, #6b7280);
  font-weight: 500;
}

.pending-pill {
  display: inline-block;
  min-width: 20px;
  padding: 1px 6px;
  margin-left: 6px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.25);
  font-size: 0.78rem;
}

.cell-ellipsis {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 900px) {
  .reports-filters {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
