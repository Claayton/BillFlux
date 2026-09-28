<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { brl } from '@/utils/format'
import { normalizeForSearch } from '@/utils/normalize'
import { tabLabel } from '@/utils/tabs'

const props = defineProps({
  /** Comandas abertas (payload da API). */
  tabs: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  /** Id da comanda em atendimento no PDV (destaque na lista). */
  activeId: { type: Number, default: null },
})
const emit = defineEmits(['close', 'select', 'print', 'cancel'])

const search = ref('')

const filtered = computed(() => {
  const term = normalizeForSearch(search.value.trim())
  if (!term) return props.tabs
  return props.tabs.filter((tab) => {
    const haystack = normalizeForSearch(
      `${tab.number} ${tabLabel(tab.number)} ${tab.identification}`
    )
    return haystack.includes(term)
  })
})

function formatOpenTime(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return '—'
  const time = date.toLocaleTimeString('pt-BR', { hour: '2-digit', minute: '2-digit' })
  const now = new Date()
  const sameDay =
    date.getDate() === now.getDate() &&
    date.getMonth() === now.getMonth() &&
    date.getFullYear() === now.getFullYear()
  if (sameDay) return `Aberta às ${time}`
  return date.toLocaleDateString('pt-BR', { day: '2-digit', month: '2-digit' }) + ` às ${time}`
}

function unitsLabel(tab) {
  const units = tab.units_count ?? 0
  const lines = tab.item_count ?? 0
  return `${units} ${units === 1 ? 'item' : 'itens'} · ${lines} ${lines === 1 ? 'linha' : 'linhas'}`
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('close')
  }
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="modal is-open">
    <div class="modal-content tab-list-modal">
      <div class="modal-header">
        <h2>
          Comandas abertas
          <span class="tab-list-count">{{ tabs.length }}</span>
        </h2>
        <button type="button" class="modal-close" aria-label="Fechar" @click="emit('close')">
          &times;
        </button>
      </div>

      <div class="tab-list-body">
        <div class="tab-list-search">
          <i class="fas fa-search"></i>
          <input
            v-model="search"
            type="text"
            placeholder="Buscar por número ou identificação…"
            autocomplete="off"
            spellcheck="false"
            autofocus
          />
        </div>

        <div v-if="loading" class="tab-list-empty">Carregando comandas…</div>

        <div v-else-if="!filtered.length" class="tab-list-empty">
          <i class="fas fa-folder-open"></i>
          <span>{{ search ? 'Nenhuma comanda encontrada.' : 'Nenhuma comanda aberta.' }}</span>
        </div>

        <div v-else class="tab-list">
          <button
            v-for="tab in filtered"
            :key="tab.id"
            type="button"
            class="tab-card"
            :class="{ 'is-active': tab.id === activeId }"
            @click="emit('select', tab)"
          >
            <span class="tab-card-main">
              <span class="tab-card-title">
                <strong>{{ tabLabel(tab.number) }}</strong>
                <span class="tab-card-identification">{{ tab.identification }}</span>
                <span v-if="tab.id === activeId" class="tab-card-badge">Em atendimento</span>
              </span>
              <span class="tab-card-meta">
                {{ formatOpenTime(tab.opened_at) }} · {{ unitsLabel(tab) }}
              </span>
            </span>
            <span class="tab-card-total">{{ brl(tab.total) }}</span>
            <span class="tab-card-actions">
              <span
                class="tab-card-action"
                role="button"
                title="Imprimir comanda"
                @click.stop="emit('print', tab)"
              >
                <i class="fas fa-print"></i>
              </span>
              <span
                class="tab-card-action is-danger"
                role="button"
                title="Cancelar comanda"
                @click.stop="emit('cancel', tab)"
              >
                <i class="fas fa-ban"></i>
              </span>
            </span>
          </button>
        </div>
      </div>

      <div class="modal-footer">
        <button type="button" class="btn btn-ghost modal-cancel" @click="emit('close')">
          Fechar <kbd>Esc</kbd>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tab-list-modal {
  max-width: 520px;
}

.tab-list-count {
  display: inline-block;
  min-width: 24px;
  padding: 1px 8px;
  margin-left: 8px;
  border-radius: 999px;
  background: color-mix(in srgb, var(--primary, #4f46e5) 12%, transparent);
  color: var(--primary, #4f46e5);
  font-size: 13px;
  font-weight: 700;
  text-align: center;
  vertical-align: middle;
}

.tab-list-body {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 60vh;
  overflow-y: auto;
}

.tab-list-search {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  border: 1px solid var(--border, #d1d5db);
  border-radius: 8px;
  background: var(--surface, #fff);
}

.tab-list-search i {
  color: var(--text-muted, #999);
  font-size: 13px;
}

.tab-list-search input {
  flex: 1;
  border: none;
  outline: none;
  font-size: 13px;
  background: transparent;
}

.tab-list-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 32px 16px;
  color: var(--text-muted, #9ca3af);
  font-size: 14px;
  text-align: center;
}

.tab-list-empty i {
  font-size: 26px;
  opacity: 0.6;
}

.tab-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.tab-card {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: var(--brand-radius-sm, 8px);
  background: var(--surface, #fff);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.15s ease, background 0.15s ease;
}

.tab-card:hover {
  border-color: var(--primary, #4f46e5);
  background: color-mix(in srgb, var(--primary, #4f46e5) 4%, white);
}

.tab-card.is-active {
  border-color: var(--primary, #4f46e5);
  background: color-mix(in srgb, var(--primary, #4f46e5) 8%, white);
}

.tab-card-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tab-card-title {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.tab-card-title strong {
  font-size: 14px;
  font-variant-numeric: tabular-nums;
}

.tab-card-identification {
  font-size: 14px;
  font-weight: 600;
  color: var(--text, #111827);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tab-card-badge {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--primary, #4f46e5) 12%, transparent);
  color: var(--primary, #4f46e5);
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
}

.tab-card-meta {
  font-size: 12px;
  color: var(--text-muted, #6b7280);
}

.tab-card-total {
  font-size: 15px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
  white-space: nowrap;
}

.tab-card-actions {
  display: flex;
  gap: 4px;
}

.tab-card-action {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--radius-sm, 6px);
  color: var(--text-muted, #6b7280);
  font-size: 13px;
}

.tab-card-action:hover {
  background: var(--surface-hover, #f3f4f6);
  color: var(--text, #111827);
}

.tab-card-action.is-danger:hover {
  background: color-mix(in srgb, var(--danger, #dc2626) 10%, transparent);
  color: var(--danger, #dc2626);
}
</style>
