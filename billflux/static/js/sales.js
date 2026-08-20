// BillFlux — interações da página de vendas diárias.

// Configuração global do HTMX: injeta o token CSRF em toda requisição.
document.body.addEventListener('htmx:configRequest', function (event) {
  var token = document.querySelector('meta[name="csrf-token"]');
  if (token) event.detail.headers['X-CSRFToken'] = token.content;
});

function openModal(modal) {
  if (!modal) return;
  modal.classList.add('is-open');
  document.body.classList.add('modal-open');
}

function closeModal(modal) {
  if (!modal) return;
  modal.classList.remove('is-open');
  document.body.classList.remove('modal-open');
}

// Fecha o modal de edição após um salvamento HTMX bem-sucedido.
function closeSaleModal(event) {
  if (event && event.detail && !event.detail.successful) return;
  closeModal(document.getElementById('sale-modal'));
}

// Mantém apenas dígitos (0-9).
function digitsOnly(value) {
  return String(value).replace(/\D/g, '');
}

// Máscara de moeda enquanto digita (centavos no final): "15050" -> "150,50".
function maskMoneyInput(input) {
  var digits = digitsOnly(input.value);
  if (!digits) {
    input.value = '';
    return;
  }
  var padded = digits.padStart(3, '0');
  var cents = padded.slice(-2);
  var integer = padded.slice(0, -2).replace(/^0+/, '') || '0';
  input.value = integer.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ',' + cents;
}

// Métricas: filtro de período + mostrar/ocultar valores (oculto por padrão).
function money(value) {
  return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(Number(value));
}

function renderStats() {
  var statsRow = document.getElementById('stats-row');
  if (!statsRow) return;
  var periods = JSON.parse(statsRow.getAttribute('data-periods'));
  var period = statsRow.getAttribute('data-active') || 'hoje';
  var revealed = statsRow.getAttribute('data-revealed') === 'true';

  statsRow.querySelectorAll('[data-stat]').forEach(function (el) {
    if (!revealed) {
      el.textContent = el.getAttribute('data-mask');
      return;
    }
    var stat = el.getAttribute('data-stat');
    var value = periods[period][stat];
    var text = (stat === 'total' || stat === 'avg') ? money(value) : String(value);
    el.textContent = text;
  });
}

// Liga um listener só uma vez (rebind seguro após swaps do HTMX).
function bindOnce(el, eventName, handler) {
  if (!el || el.getAttribute('data-init')) return;
  el.setAttribute('data-init', '1');
  el.addEventListener(eventName, handler);
}

function initSalesPage() {
  // Máscara de moeda nos campos de total (lançamento e edição).
  var totalInputs = [document.getElementById('sale_total'), document.getElementById('edit_sale_total')];
  totalInputs.forEach(function (input) {
    bindOnce(input, 'input', function () { maskMoneyInput(input); });
  });

  // Filtro de período das métricas.
  bindOnce(document.getElementById('period-filter'), 'click', function (event) {
    var button = event.target.closest('[data-period]');
    if (!button) return;
    var filter = document.getElementById('period-filter');
    var statsRow = document.getElementById('stats-row');
    filter.querySelectorAll('[data-period]').forEach(function (b) {
      b.classList.remove('is-active');
    });
    button.classList.add('is-active');
    statsRow.setAttribute('data-active', button.getAttribute('data-period'));
    renderStats();
  });

  // Mostrar/ocultar valores.
  bindOnce(document.getElementById('toggle-values'), 'click', function () {
    var statsRow = document.getElementById('stats-row');
    var toggle = document.getElementById('toggle-values');
    var revealed = statsRow.getAttribute('data-revealed') === 'true';
    var next = !revealed;
    statsRow.setAttribute('data-revealed', next ? 'true' : 'false');
    toggle.setAttribute('aria-pressed', next ? 'true' : 'false');
    toggle.setAttribute('title', next ? 'Ocultar valores' : 'Mostrar valores');
    toggle.setAttribute('aria-label', next ? 'Ocultar valores' : 'Mostrar valores');
    toggle.querySelector('i').className = next ? 'fas fa-eye' : 'fas fa-eye-slash';
    renderStats();
  });

  renderStats();

  // Fecha os avisos flash (incluindo os inseridos pelo HTMX).
  document.querySelectorAll('.flash-close').forEach(function (btn) {
    bindOnce(btn, 'click', function () { btn.parentElement.remove(); });
  });

  // Modal de edição.
  var modal = document.getElementById('sale-modal');
  var dateInput = document.getElementById('edit_sale_date');
  var totalInput = document.getElementById('edit_sale_total');
  var obsInput = document.getElementById('edit_sale_obs');

  function openEdit(item) {
    var id = item.getAttribute('data-id');
    var data = document.querySelector('.row-data[data-id="' + id + '"]');
    if (!data) return;
    dateInput.value = data.getAttribute('data-date');
    totalInput.value = data.getAttribute('data-total');
    obsInput.value = data.getAttribute('data-obs');
    openModal(modal);
    totalInput.focus();
  }

  if (modal) {
    bindOnce(modal.querySelector('.modal-close'), 'click', function () { closeModal(modal); });
    bindOnce(modal.querySelector('.modal-cancel'), 'click', function () { closeModal(modal); });
    bindOnce(modal, 'click', function (event) {
      if (event.target === modal) closeModal(modal);
    });
  }

  // Ações do menu por linha: Editar (excluir é feito via HTMX).
  document.querySelectorAll('[id^="sale-menu-"] .dropdown-item[data-action="edit"]').forEach(function (item) {
    bindOnce(item, 'click', function () { openEdit(item); });
  });
}

document.addEventListener('DOMContentLoaded', initSalesPage);
document.addEventListener('htmx:afterSettle', initSalesPage);