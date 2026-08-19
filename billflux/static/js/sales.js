// BillFlux — interações da página de vendas diárias.

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

document.addEventListener('DOMContentLoaded', function () {
  // Máscara de moeda nos campos de total (lançamento e edição).
  var totalInputs = [document.getElementById('sale_total'), document.getElementById('edit_sale_total')];
  totalInputs.forEach(function (input) {
    if (input) input.addEventListener('input', function () { maskMoneyInput(input); });
  });

  var modal = document.getElementById('sale-modal');
  var form = document.getElementById('sale-edit-form');
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
    var closeBtn = modal.querySelector('.modal-close');
    if (closeBtn) closeBtn.addEventListener('click', function () { closeModal(modal); });
    var cancelBtn = modal.querySelector('.modal-cancel');
    if (cancelBtn) cancelBtn.addEventListener('click', function () { closeModal(modal); });
    modal.addEventListener('click', function (event) {
      if (event.target === modal) closeModal(modal);
    });
  }

  function csrfToken() {
    var input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : '';
  }

  // Ações do menu por linha: Editar / Excluir.
  document.querySelectorAll('[id^="sale-menu-"] .dropdown-item[data-action]').forEach(function (item) {
    item.addEventListener('click', function () {
      var action = item.getAttribute('data-action');
      var saleId = item.getAttribute('data-id');
      if (action === 'edit') {
        openEdit(item);
      } else if (action === 'delete') {
        if (!window.confirm('Excluir esta venda?')) return;
        fetch('/sales/delete/' + saleId, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken(),
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }).then(function () {
          window.location.reload();
        });
      }
    });
  });
});