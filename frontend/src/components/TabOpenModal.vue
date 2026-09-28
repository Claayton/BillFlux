<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { brl } from '@/utils/format'

const props = defineProps({
  /** Subtotal atual do carrinho (virará o total da comanda). */
  total: { type: Number, required: true },
  /** Quantidade de itens no carrinho (botão fica desabilitado sem itens). */
  itemCount: { type: Number, default: 0 },
  /** True enquanto a requisição de abertura está em andamento. */
  loading: { type: Boolean, default: false },
})
const emit = defineEmits(['confirm', 'cancel'])

const identification = ref('')
const print = ref(true)

const canConfirm = computed(
  () => identification.value.trim().length > 0 && props.itemCount > 0 && !props.loading
)

function submit() {
  if (!canConfirm.value) return
  emit('confirm', { identification: identification.value.trim(), print: print.value })
}

function onKeydown(event) {
  if (event.key === 'Escape') {
    event.preventDefault()
    emit('cancel')
  }
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<template>
  <div class="modal is-open">
    <div class="modal-content modal-content-sm">
      <div class="modal-header">
        <h2>Abrir comanda</h2>
        <button type="button" class="modal-close" aria-label="Fechar" @click="emit('cancel')">
          &times;
        </button>
      </div>

      <div class="pdv-modal-body">
        <div class="form-field">
          <label for="tab_identification">Identificação da comanda</label>
          <input
            id="tab_identification"
            ref="identificationInput"
            v-model="identification"
            type="text"
            maxlength="80"
            placeholder="Ex: Mesa 2, João, Rapaz da Saveiro…"
            autocomplete="off"
            autofocus
            @keydown.enter.prevent="submit"
          />
          <small class="tab-field-hint">Obrigatória — ajuda a encontrar a comanda depois.</small>
        </div>

        <div class="tab-open-total">
          <span>Total atual da comanda</span>
          <strong>{{ brl(total) }}</strong>
        </div>

        <label class="tab-open-print">
          <input v-model="print" type="checkbox" />
          <i class="fas fa-print"></i>
          Imprimir comanda
        </label>
      </div>

      <div class="modal-footer">
        <button type="button" class="btn btn-ghost modal-cancel" @click="emit('cancel')">
          Cancelar
        </button>
        <button type="button" class="btn btn-primary" :disabled="!canConfirm" @click="submit">
          <i class="fas fa-clipboard-list"></i>
          {{ loading ? 'Abrindo…' : 'Abrir comanda' }}
          <kbd>F4</kbd>
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.tab-field-hint {
  display: block;
  margin-top: 4px;
  font-size: 12px;
  color: var(--text-muted, #9ca3af);
}

.tab-open-total {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  padding: 12px 14px;
  border: 1px solid var(--border, #e5e7eb);
  border-radius: var(--brand-radius-sm, 8px);
  background: var(--surface-hover, #f9fafb);
}

.tab-open-total span {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted, #9ca3af);
}

.tab-open-total strong {
  font-size: 22px;
  font-weight: 800;
  font-variant-numeric: tabular-nums;
}

.tab-open-print {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  user-select: none;
}

.tab-open-print input {
  width: 16px;
  height: 16px;
  accent-color: var(--primary, #4f46e5);
  cursor: pointer;
}

.tab-open-print i {
  color: var(--text-muted, #9ca3af);
}
</style>
