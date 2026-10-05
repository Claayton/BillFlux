<script setup>
import { ref, computed, nextTick, onBeforeUnmount, watch } from 'vue'
import { brl } from '@/utils/format'
import { normalizeForSearch } from '@/utils/normalize'

const props = defineProps({
  products: { type: Array, default: () => [] },
  placeholder: { type: String, default: 'Buscar produto…' },
})

const emit = defineEmits(['select'])

const query = ref('')
const open = ref(false)
const highlighted = ref(-1)
const inputEl = ref(null)
const dropdownEl = ref(null)
const dropdownStyle = ref({})

const suggestions = computed(() => {
  const q = normalizeForSearch(query.value.trim())
  if (!q) return []
  return props.products
    .filter((p) => p.active !== false)
    .filter(
      (p) =>
        normalizeForSearch(p.name).includes(q) ||
        normalizeForSearch(p.barcode || '').includes(q)
    )
    .slice(0, 30)
})

function updatePosition() {
  const el = inputEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  dropdownStyle.value = {
    position: 'fixed',
    top: `${rect.bottom + 6}px`,
    left: `${rect.left}px`,
    right: 'auto',
    width: `${rect.width}px`,
    zIndex: 3000,
  }
}

function openList() {
  open.value = true
  highlighted.value = -1
  updatePosition()
}

function setHighlight(index) {
  highlighted.value = index
  nextTick(() => {
    const el = dropdownEl.value?.querySelector('.pdv-suggestion.is-highlighted')
    if (el && typeof el.scrollIntoView === 'function') {
      el.scrollIntoView({ block: 'nearest' })
    }
  })
}

function choose(product) {
  emit('select', product)
  query.value = ''
  highlighted.value = -1
  open.value = false
  nextTick(() => inputEl.value?.focus())
}

function onKeydown(event) {
  if (event.key === 'ArrowDown') {
    event.preventDefault()
    if (!open.value) {
      openList()
    } else if (suggestions.value.length) {
      setHighlight(
        highlighted.value < 0 ? 0 : (highlighted.value + 1) % suggestions.value.length
      )
    }
  } else if (event.key === 'ArrowUp') {
    event.preventDefault()
    if (suggestions.value.length) {
      setHighlight(
        highlighted.value < 0
          ? suggestions.value.length - 1
          : (highlighted.value - 1 + suggestions.value.length) %
              suggestions.value.length
      )
    }
  } else if (event.key === 'Enter') {
    event.preventDefault()
    if (highlighted.value >= 0 && suggestions.value[highlighted.value]) {
      choose(suggestions.value[highlighted.value])
    } else if (suggestions.value.length === 1) {
      choose(suggestions.value[0])
    }
  } else if (event.key === 'Escape') {
    open.value = false
  }
}

function onBlur() {
  setTimeout(() => {
    open.value = false
  }, 150)
}

function onReposition() {
  if (open.value) updatePosition()
}

watch(open, (isOpen) => {
  if (isOpen) {
    window.addEventListener('scroll', onReposition, true)
    window.addEventListener('resize', onReposition)
  } else {
    window.removeEventListener('scroll', onReposition, true)
    window.removeEventListener('resize', onReposition)
  }
})

onBeforeUnmount(() => {
  window.removeEventListener('scroll', onReposition, true)
  window.removeEventListener('resize', onReposition)
})
</script>

<template>
  <div class="product-search">
    <div class="ps-field">
      <i class="fas fa-search ps-icon"></i>
      <input
        ref="inputEl"
        v-model="query"
        type="text"
        class="ps-input"
        :placeholder="placeholder"
        autocomplete="off"
        spellcheck="false"
        @input="openList"
        @focus="openList"
        @keydown="onKeydown"
        @blur="onBlur"
      />
      <button
        v-if="query"
        type="button"
        class="ps-clear"
        aria-label="Limpar busca"
        @mousedown.prevent="query = ''; open = false"
      >
        <i class="fas fa-times"></i>
      </button>
    </div>

    <Teleport to="body">
      <div
        v-if="open && suggestions.length"
        ref="dropdownEl"
        class="pdv-suggestions"
        :style="dropdownStyle"
      >
        <button
          v-for="(p, i) in suggestions"
          :key="p.id"
          type="button"
          class="pdv-suggestion"
          :class="{ 'is-highlighted': i === highlighted }"
          @mousedown.prevent="choose(p)"
        >
          <span class="pdv-suggestion-info">
            <span class="pdv-suggestion-name">{{ p.name }}</span>
            <span class="pdv-suggestion-sub">
              {{ p.barcode ? 'Cód.: ' + p.barcode : 'Sem código de barras' }}
            </span>
          </span>
          <span class="pdv-suggestion-price">{{ brl(p.price) }}</span>
          <span class="pdv-suggestion-stock" :class="{ 'is-out': p.stock_quantity <= 0 }">
            {{ p.stock_quantity <= 0 ? 'Esgotado' : p.stock_quantity + ' un' }}
          </span>
        </button>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.product-search {
  position: relative;
  width: 100%;
}

.ps-field {
  position: relative;
  display: flex;
  align-items: center;
}

.ps-icon {
  position: absolute;
  left: 12px;
  color: var(--text-muted, #9ca3af);
  font-size: 14px;
  pointer-events: none;
}

.ps-input {
  width: 100%;
  padding: 9px 34px 9px 36px;
  border: 1px solid var(--border, #d1d5db);
  border-radius: 6px;
  font-size: 14px;
  font-family: inherit;
}

.ps-input:focus {
  outline: none;
  border-color: var(--primary, #2563eb);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.15);
}

.ps-clear {
  position: absolute;
  right: 8px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--text-muted, #9ca3af);
  cursor: pointer;
}

.ps-clear:hover {
  background: var(--surface-hover, #f3f4f6);
  color: var(--text, #111827);
}
</style>
