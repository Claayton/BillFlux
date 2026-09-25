<script setup>
defineProps({
  title: { type: String, required: true },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Confirmar' },
  danger: { type: Boolean, default: false },
  summary: { type: Array, default: () => null },
})
const emit = defineEmits(['confirm', 'cancel'])
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
        <button type="button" class="btn btn-ghost modal-cancel" @click="emit('cancel')">Voltar</button>
        <button type="button" class="btn" :class="danger ? 'btn-danger' : 'btn-primary'" @click="emit('confirm')">
          {{ confirmLabel }}
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
</style>