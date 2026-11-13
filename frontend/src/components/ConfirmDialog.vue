<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'

const props = defineProps({
  title: { type: String, required: true },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Confirmar' },
  cancelLabel: { type: String, default: 'Voltar' },
  danger: { type: Boolean, default: false },
  summary: { type: Array, default: () => null },
  inputLabel: { type: String, default: '' },
  inputPlaceholder: { type: String, default: '' },
  /**
   * Navegação por teclado: ←/↑ escolhem "não", →/↓ escolhem o confirmar,
   * Enter/Espaço executam a escolha e Esc cancela.
   */
  keyboard: { type: Boolean, default: false },
  /** Atalho direto para o botão de confirmar (ex.: "p"). */
  confirmKey: { type: String, default: '' },
  /** Atalho direto para o botão de cancelar (ex.: "Escape"). */
  cancelKey: { type: String, default: '' },
})
const emit = defineEmits(['confirm', 'cancel'])
const inputText = ref('')
const selected = ref('confirm')

const keyLabel = (key) => {
  if (!key) return ''
  if (key === 'Escape') return 'Esc'
  if (key === ' ') return 'Espaço'
  return key.toUpperCase()
}
const cancelKeyLabel = computed(() => keyLabel(props.cancelKey))
const confirmKeyLabel = computed(() => keyLabel(props.confirmKey))

function matches(event, key) {
  if (!key) return false
  return event.key.toLowerCase() === key.toLowerCase()
}

function onKeydown(event) {
  if (!props.keyboard) return
  const tag = event.target?.tagName
  const typing =
    tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || event.target?.isContentEditable

  if (event.key === 'Escape') {
    event.preventDefault()
    emit('cancel')
  } else if (!typing && matches(event, props.cancelKey)) {
    event.preventDefault()
    emit('cancel')
  } else if (!typing && matches(event, props.confirmKey)) {
    event.preventDefault()
    emit('confirm', inputText.value)
  } else if (
    event.key === 'ArrowLeft' ||
    event.key === 'ArrowUp' ||
    event.key === 'ArrowRight' ||
    event.key === 'ArrowDown'
  ) {
    event.preventDefault()
    selected.value =
      event.key === 'ArrowLeft' || event.key === 'ArrowUp' ? 'cancel' : 'confirm'
  } else if (event.key === 'Enter' || event.key === ' ' || event.key === 'Spacebar') {
    event.preventDefault()
    if (selected.value === 'confirm') emit('confirm', inputText.value)
    else emit('cancel')
  }
}

onMounted(() => {
  if (props.keyboard) document.addEventListener('keydown', onKeydown)
})
onBeforeUnmount(() => {
  if (props.keyboard) document.removeEventListener('keydown', onKeydown)
})
</script>

<template>
  <div class="modal is-open">
    <div class="modal-content modal-content-sm">
      <div class="modal-header">
        <h2>{{ title }}</h2>
        <button type="button" class="modal-close" aria-label="Fechar" @click="emit('cancel')">&times;</button>
      </div>
      <div class="confirm-body">
        <p v-if="message">{{ message }}</p>
        <div v-if="inputLabel" class="form-field confirm-input">
          <label>{{ inputLabel }}</label>
          <input v-model="inputText" type="text" :placeholder="inputPlaceholder" />
        </div>
        <dl v-if="summary && summary.length" class="confirm-summary">
          <div
            v-for="row in summary"
            :key="row.label"
            class="confirm-summary-row"
            :class="row.tone ? `is-${row.tone}` : ''"
          >
            <dt>{{ row.label }}</dt>
            <dd>{{ row.value }}</dd>
          </div>
        </dl>
      </div>
      <div class="modal-footer">
        <button
          type="button"
          class="btn btn-ghost modal-cancel"
          :class="{ 'is-selected': keyboard && selected === 'cancel' }"
          @mouseenter="selected = 'cancel'"
          @focus="selected = 'cancel'"
          @click="emit('cancel')"
        >{{ cancelLabel }} <kbd v-if="cancelKeyLabel">{{ cancelKeyLabel }}</kbd></button>
        <button
          type="button"
          class="btn"
          :class="[danger ? 'btn-danger' : 'btn-primary', { 'is-selected': keyboard && selected === 'confirm' }]"
          @mouseenter="selected = 'confirm'"
          @focus="selected = 'confirm'"
          @click="emit('confirm', inputText)"
        >
          {{ confirmLabel }} <kbd v-if="confirmKeyLabel">{{ confirmKeyLabel }}</kbd>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.confirm-body {
  padding: 20px 24px;
  font-size: 14px;
  color: var(--text);
  line-height: 1.5;
}
.confirm-body p {
  margin: 0 0 12px;
}

.confirm-body p:last-child {
  margin-bottom: 0;
}

.confirm-input {
  margin-top: 12px;
  margin-bottom: 0;
}

.confirm-summary {
  margin: 0;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.confirm-summary-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 10px 14px;
  font-size: 14px;
}

.confirm-summary-row + .confirm-summary-row {
  border-top: 1px solid var(--border);
}

.confirm-summary-row dt {
  color: var(--text-secondary);
  font-weight: 500;
}

.confirm-summary-row dd {
  margin: 0;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.confirm-summary-row.is-ok dd {
  color: var(--success);
}

.confirm-summary-row.is-warn dd {
  color: var(--warning);
}

.confirm-summary-row.is-bad dd {
  color: var(--danger);
}
.modal-footer {
  margin-top: 0;
  padding: 16px 24px 20px;
}
.modal-footer .btn.is-selected {
  outline: 2px solid var(--primary);
  outline-offset: 2px;
  box-shadow: 0 0 0 4px var(--primary-soft);
}
</style>