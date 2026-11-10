<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import ThermalCoupon from '@/components/ThermalCoupon.vue'

const loading = ref(true)
const saving = ref(false)
const activeTab = ref('company')
const form = ref({})
const fiscalStatus = ref(null)
const checkingFiscal = ref(false)

const tabs = [
  { id: 'company', label: 'Empresa', icon: 'fas fa-store' },
  { id: 'pdv', label: 'PDV', icon: 'fas fa-cash-register' },
  { id: 'stock', label: 'Estoque', icon: 'fas fa-boxes' },
  { id: 'print', label: 'Impressão', icon: 'fas fa-print' },
  { id: 'fiscal', label: 'Fiscal', icon: 'fas fa-file-invoice-dollar' },
]

async function load() {
  loading.value = true
  try {
    const res = await api.get('/settings')
    form.value = { ...res.settings }
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    loading.value = false
  }
}

async function save() {
  saving.value = true
  try {
    const res = await api.put('/settings', { settings: { ...form.value } })
    form.value = { ...res.settings }
    ElMessage.success('Configurações salvas!')
  } catch (error) {
    ElMessage.error(error.message)
  } finally {
    saving.value = false
  }
}

function toggleAutoPrint(event) {
  form.value['pdv.auto_print'] = event.target.checked ? 'true' : 'false'
}

/** Alterna uma flag booleana guardada como 'true'/'false'. */
function isOn(key) {
  return form.value[key] === 'true'
}
function toggleSetting(key, event) {
  form.value[key] = event.target.checked ? 'true' : 'false'
}

function splitLines(text) {
  return (text || '').split('\n').map((l) => l.trim()).filter(Boolean)
}

/** Prévia ao vivo do cupom na aba Impressão. */
const previewWidth = computed(() =>
  form.value['receipt.width'] === '58' ? '58' : '80'
)
const previewHeaderLines = computed(() => splitLines(form.value['receipt.header']))
const previewFooterLines = computed(() => splitLines(form.value['receipt.footer']))
const previewOrder = {
  order_id: 1024,
  date: '2026-09-27T14:30:00',
  items: [
    { name: 'Coca-Cola 2L', quantity: 2, unit_price: 9.9, subtotal: 19.8 },
    { name: 'Pão francês', quantity: 5, unit_price: 0.75, subtotal: 3.75 },
  ],
  discount: 0,
  total: 23.55,
  payments: [{ name: 'Dinheiro', amount: 50 }],
  troco: 26.45,
  obs: 'Retirar no balcão 2',
  payment_method: 'Dinheiro',
  customer_name: 'Maria Souza',
}

onMounted(load)

/** Consulta o status fiscal (token/emitente/pendências) sem emitir nada. */
async function checkFiscal() {
  checkingFiscal.value = true
  try {
    fiscalStatus.value = await api.get('/fiscal/status')
  } catch (error) {
    fiscalStatus.value = null
    ElMessage.error(error.message)
  } finally {
    checkingFiscal.value = false
  }
}

watch(activeTab, (tab) => {
  if (tab === 'fiscal' && !fiscalStatus.value) checkFiscal()
})
</script>

<template>
  <AppShell>
    <div class="dashboard config-page">
      <div class="page-header">
        <div>
          <h1 class="page-title">Configurações</h1>
          <p class="page-subtitle">Dados da empresa, comportamento do PDV e impressão.</p>
        </div>
      </div>

      <div v-if="loading" class="muted">Carregando…</div>
      <template v-else>
        <div class="filter-segmented config-tabs" role="tablist" aria-label="Categorias de configuração">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            type="button"
            role="tab"
            :aria-selected="activeTab === tab.id"
            :class="{ 'is-active': activeTab === tab.id }"
            :disabled="tab.soon"
            @click="!tab.soon && (activeTab = tab.id)"
          >
            <i :class="tab.icon"></i> {{ tab.label }}
            <span v-if="tab.soon" class="config-soon">em breve</span>
          </button>
        </div>

        <form class="config-panel" @submit.prevent="save">
          <!-- Empresa -->
          <div v-show="activeTab === 'company'" class="config-section">
            <h2>Empresa</h2>
            <p class="config-hint">Aparece no recibo e nos relatórios.</p>
            <div class="config-grid">
              <div class="form-field">
                <label for="cfg-name">Nome da empresa</label>
                <input id="cfg-name" v-model="form['company.name']" type="text" placeholder="Mercado Central" />
              </div>
              <div class="form-field">
                <label for="cfg-cnpj">CNPJ</label>
                <input id="cfg-cnpj" v-model="form['company.cnpj']" type="text" placeholder="00.000.000/0001-00" />
              </div>
              <div class="form-field">
                <label for="cfg-phone">Telefone</label>
                <input id="cfg-phone" v-model="form['company.phone']" type="text" placeholder="(11) 99999-9999" />
              </div>
              <div class="form-field config-grid-full">
                <label for="cfg-address">Endereço</label>
                <input id="cfg-address" v-model="form['company.address']" type="text" placeholder="Rua, nº — Bairro" />
              </div>
            </div>
          </div>

          <!-- PDV -->
          <div v-show="activeTab === 'pdv'" class="config-section">
            <h2>PDV</h2>
            <p class="config-hint">Como o caixa se comporta no balcão.</p>
            <label class="config-check">
              <input
                type="checkbox"
                :checked="form['pdv.auto_print'] === 'true'"
                @change="toggleAutoPrint"
              />
              <span>
                <strong>Imprimir cupom automaticamente</strong><br />
                Abre a impressão sozinho após cada venda concluída.
              </span>
            </label>
          </div>

          <!-- Estoque -->
          <div v-show="activeTab === 'stock'" class="config-section">
            <h2>Estoque</h2>
            <p class="config-hint">Alertas de reposição nos produtos.</p>
            <div class="config-grid">
              <div class="form-field">
                <label for="cfg-min">Estoque mínimo padrão</label>
                <input
                  id="cfg-min"
                  v-model="form['stock.default_min']"
                  type="number"
                  min="0"
                  step="1"
                  placeholder="5"
                />
                <small class="config-note">Usado ao cadastrar produto novo. Ajuste por produto continua livre.</small>
              </div>
            </div>
          </div>

          <!-- Impressão -->
          <div v-show="activeTab === 'print'" class="config-section">
            <h2>Impressão</h2>
            <p class="config-hint">Cupom térmico do PDV. O recibo completo continua disponível em Vendas.</p>
            <div class="print-layout">
              <div class="print-fields">
                <div class="form-field">
                  <span class="config-label">Largura do papel</span>
                  <div class="filter-segmented" role="group" aria-label="Largura do papel">
                    <button
                      type="button"
                      :class="{ 'is-active': form['receipt.width'] === '58' }"
                      @click="form['receipt.width'] = '58'"
                    >
                      58 mm
                    </button>
                    <button
                      type="button"
                      :class="{ 'is-active': form['receipt.width'] === '80' }"
                      @click="form['receipt.width'] = '80'"
                    >
                      80 mm
                    </button>
                  </div>
                </div>
                <div class="form-field">
                  <label for="cfg-header">Cabeçalho do cupom</label>
                  <textarea id="cfg-header" v-model="form['receipt.header']" rows="3" placeholder="Nome da loja, endereço…"></textarea>
                </div>
                <div class="form-field">
                  <label for="cfg-footer">Rodapé do cupom</label>
                  <textarea id="cfg-footer" v-model="form['receipt.footer']" rows="2" placeholder="Obrigado pela preferência!"></textarea>
                </div>
                <div class="form-field">
                  <label for="cfg-message">Mensagem da notinha</label>
                  <input id="cfg-message" v-model="form['receipt.message']" type="text" placeholder="Ex: Obrigado e volte sempre!" />
                </div>
                <div class="form-field">
                  <span class="config-label">Informações exibidas</span>
                  <div class="config-checks">
                    <label class="form-check"><input type="checkbox" :checked="isOn('receipt.show_cnpj')" @change="toggleSetting('receipt.show_cnpj', $event)" /> <span>Mostrar CNPJ</span></label>
                    <label class="form-check"><input type="checkbox" :checked="isOn('receipt.show_address')" @change="toggleSetting('receipt.show_address', $event)" /> <span>Mostrar endereço</span></label>
                    <label class="form-check"><input type="checkbox" :checked="isOn('receipt.show_phone')" @change="toggleSetting('receipt.show_phone', $event)" /> <span>Mostrar telefone</span></label>
                    <label class="form-check"><input type="checkbox" :checked="isOn('receipt.show_customer')" @change="toggleSetting('receipt.show_customer', $event)" /> <span>Mostrar cliente</span></label>
                  </div>
                </div>
              </div>

              <div class="coupon-preview">
                <span class="preview-label"><i class="fas fa-eye"></i> Prévia ao vivo</span>
                <ThermalCoupon
                  :width="previewWidth"
                  :company="form['company.name'] || 'BeeFlux'"
                  :header-lines="previewHeaderLines"
                  :footer-lines="previewFooterLines"
                  :order="previewOrder"
                  :company-cnpj="form['company.cnpj'] || ''"
                  :company-address="form['company.address'] || ''"
                  :company-phone="form['company.phone'] || ''"
                  :show-cnpj="isOn('receipt.show_cnpj')"
                  :show-address="isOn('receipt.show_address')"
                  :show-phone="isOn('receipt.show_phone')"
                  :show-customer="isOn('receipt.show_customer')"
                  :message="form['receipt.message'] || ''"
                />
                <span class="preview-note">Venda de exemplo — a impressão sai exatamente assim.</span>
              </div>
            </div>
          </div>

          <!-- Fiscal -->
          <div v-show="activeTab === 'fiscal'" class="config-section">
            <h2>Fiscal (NFC-e)</h2>
            <p class="config-hint">
              Emissão de NFC-e pelo PDV com o provedor Brasil NFe. O token de acesso
              fica no servidor, na variável <code>BRASILNFE_TOKEN</code>.
            </p>

            <div class="fiscal-status" :class="{ 'is-ready': fiscalStatus?.ready }">
              <i
                class="fiscal-status-icon fas"
                :class="fiscalStatus?.ready ? 'fa-check-circle' : 'fa-exclamation-triangle'"
              ></i>
              <div class="fiscal-status-text">
                <strong v-if="fiscalStatus">
                  {{ fiscalStatus.ready ? 'Pronto para emitir' : 'Faltam configurações' }}
                </strong>
                <strong v-else>Configuração fiscal</strong>
                <p v-if="fiscalStatus">
                  Token: {{ fiscalStatus.token_configured ? 'configurado' : 'ausente' }} ·
                  {{ fiscalStatus.pending_products }} produto(s) com pendência fiscal
                </p>
                <p v-else class="muted">
                  Verifique o token, o emitente e os produtos antes de emitir.
                </p>
              </div>
              <button
                type="button"
                class="btn btn-ghost btn-sm"
                :disabled="checkingFiscal"
                @click="checkFiscal"
              >
                <i class="fas" :class="checkingFiscal ? 'fa-circle-notch fa-spin' : 'fa-sync'"></i>
                {{ checkingFiscal ? 'Verificando…' : 'Verificar configuração' }}
              </button>
            </div>

            <div class="config-grid">
              <div class="form-field">
                <label for="cfg-fiscal-provider">Provedor</label>
                <select id="cfg-fiscal-provider" v-model="form['fiscal.provider']">
                  <option value="brasilnfe">Brasil NFe</option>
                </select>
              </div>
              <div class="form-field">
                <label for="cfg-fiscal-crt">Regime tributário (CRT)</label>
                <select id="cfg-fiscal-crt" v-model="form['fiscal.crt']">
                  <option value="1">1 — Simples Nacional</option>
                  <option value="2">2 — Simples Nacional (excesso de sublimite)</option>
                  <option value="3">3 — Regime Normal</option>
                </select>
              </div>
              <div class="form-field">
                <label for="cfg-fiscal-ie">Inscrição Estadual (IE)</label>
                <input id="cfg-fiscal-ie" v-model="form['fiscal.ie']" type="text" placeholder="Ex: 1234567890" />
              </div>
              <div class="form-field">
                <label for="cfg-fiscal-series">Série atual da NFC-e</label>
                <input id="cfg-fiscal-series" v-model="form['fiscal.nfce_series']" type="text" placeholder="Ex: 1" />
              </div>
              <div class="form-field">
                <label for="cfg-fiscal-last">Último número emitido</label>
                <input id="cfg-fiscal-last" v-model="form['fiscal.nfce_last_number']" type="text" placeholder="Ex: 1234" />
                <small class="config-note">Referência para migrar a numeração no painel do provedor.</small>
              </div>
            </div>

            <div class="form-field">
              <span class="config-label">Ambiente</span>
              <div class="filter-segmented" role="group" aria-label="Ambiente fiscal">
                <button
                  type="button"
                  :class="{ 'is-active': (form['fiscal.environment'] || 'homologacao') !== 'producao' }"
                  @click="form['fiscal.environment'] = 'homologacao'"
                >
                  Homologação
                </button>
                <button
                  type="button"
                  :class="{ 'is-active': form['fiscal.environment'] === 'producao' }"
                  @click="form['fiscal.environment'] = 'producao'"
                >
                  Produção
                </button>
              </div>
              <small class="config-note">Homologação emite notas de teste, sem valor fiscal.</small>
            </div>

            <div class="form-field">
              <span class="config-label">Impressão da NFC-e</span>
              <div class="filter-segmented" role="group" aria-label="Impressão da NFC-e">
                <button
                  type="button"
                  :class="{ 'is-active': (form['fiscal.print_mode'] || 'thermal') === 'thermal' }"
                  @click="form['fiscal.print_mode'] = 'thermal'"
                >
                  Térmico (80 mm)
                </button>
                <button
                  type="button"
                  :class="{ 'is-active': form['fiscal.print_mode'] === 'pdf' }"
                  @click="form['fiscal.print_mode'] = 'pdf'"
                >
                  PDF do DANFE
                </button>
                <button
                  type="button"
                  :class="{ 'is-active': form['fiscal.print_mode'] === 'none' }"
                  @click="form['fiscal.print_mode'] = 'none'"
                >
                  Não imprimir
                </button>
              </div>
            </div>

            <label class="config-check">
              <input
                type="checkbox"
                :checked="(form['fiscal.auto_retry'] || 'true') === 'true'"
                @change="toggleSetting('fiscal.auto_retry', $event)"
              />
              <span>
                <strong>Reenviar notas pendentes automaticamente</strong><br />
                Tenta de novo em segundo plano quando a SEFAZ/provedor voltar.
              </span>
            </label>

            <div class="fiscal-actions">
              <router-link class="btn btn-ghost btn-sm" to="/products?fiscal=pending">
                <i class="fas fa-list-check"></i> Ver pendências fiscais
              </router-link>
              <small class="config-note">
                NCM/CFOP/CSOSN são preenchidos em Produtos → Dados → Dados fiscais.
              </small>
            </div>
          </div>

          <div class="config-actions">
            <button type="submit" class="btn btn-brand" :disabled="saving">
              <i class="fas fa-save"></i> {{ saving ? 'Salvando…' : 'Salvar alterações' }}
            </button>
          </div>
        </form>
      </template>
    </div>
  </AppShell>
</template>

<style scoped>
.config-tabs {
  margin-bottom: 20px;
}

.config-soon {
  margin-left: 6px;
  padding: 2px 6px;
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  color: var(--text-muted);
  background: var(--surface-hover);
  border-radius: 999px;
}

.config-tabs button:disabled {
  cursor: not-allowed;
  opacity: 0.75;
}

.config-panel {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg, 16px);
  padding: clamp(20px, 3vw, 32px);
  max-width: 820px;
}

.config-section h2 {
  margin: 0 0 4px;
  font-size: 18px;
}

.config-hint {
  margin: 0 0 20px;
  font-size: 13px;
  color: var(--text-secondary);
}

.config-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 0 16px;
}

.config-grid-full {
  grid-column: 1 / -1;
}

.config-label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--text);
}

.config-note {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  color: var(--text-muted);
}

.config-checks {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 8px 16px;
}

.config-checks .form-check {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.config-check {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  padding: 14px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  cursor: pointer;
  font-size: 14px;
  line-height: 1.5;
}

.config-check input {
  margin-top: 3px;
  accent-color: var(--primary);
}

.config-check strong {
  color: var(--text);
}

.config-actions {
  margin-top: 24px;
  padding-top: 20px;
  border-top: 1px solid var(--border);
}

/* ---------- Prévia do cupom ---------- */
.print-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 24px;
  align-items: start;
}

.coupon-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 16px;
  background: var(--surface-hover);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  max-height: 480px;
  overflow: auto;
}

.preview-label {
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--text-muted);
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.preview-note {
  font-size: 11px;
  color: var(--text-muted);
  text-align: center;
  max-width: 240px;
}

@media (max-width: 900px) {
  .print-layout {
    grid-template-columns: 1fr;
  }
}

.fiscal-status {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  margin-bottom: 16px;
  border: 1px solid var(--border);
  border-radius: 10px;
  background: var(--surface-hover, #f9fafb);
}
.fiscal-status.is-ready {
  border-color: #86efac;
  background: rgba(34, 197, 94, 0.08);
}
.fiscal-status-icon {
  font-size: 20px;
  color: #d97706;
}
.fiscal-status.is-ready .fiscal-status-icon {
  color: #16a34a;
}
.fiscal-status-text {
  flex: 1;
  min-width: 0;
}
.fiscal-status-text p {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
}
.fiscal-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 10px;
}
</style>
