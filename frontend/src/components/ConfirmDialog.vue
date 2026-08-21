<script setup>
defineProps({
  title: { type: String, required: true },
  message: { type: String, default: '' },
  confirmLabel: { type: String, default: 'Confirmar' },
  danger: { type: Boolean, default: false },
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
        <p>{{ message }}</p>
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
</style>