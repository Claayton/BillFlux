// BillFlux — interações da página de produtos.

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

document.addEventListener('DOMContentLoaded', function () {
  const productModal = document.getElementById('product-modal');
  const productForm = document.getElementById('product-form');
  const productTitle = document.getElementById('product-modal-title');
  const productIdInput = document.getElementById('product_id');
  const nameInput = document.getElementById('product_name');
  const priceInput = document.getElementById('product_price');
  const costInput = document.getElementById('product_cost');
  const barcodeInput = document.getElementById('product_barcode');
  const stockInput = document.getElementById('product_stock_quantity');
  const minStockInput = document.getElementById('product_min_stock');
  const obsInput = document.getElementById('product_obs');
  const activeInput = document.getElementById('product_active');

  const adjustModal = document.getElementById('adjust-modal');
  const adjustForm = document.getElementById('adjust-form');
  const adjustProductId = document.getElementById('adjust_product_id');
  const adjustProductName = document.getElementById('adjust_product_name');
  const adjustCurrentStock = document.getElementById('adjust_current_stock');
  const adjustDelta = document.getElementById('adjust_delta');
  const adjustObs = document.getElementById('adjust_obs');

  const movementsModal = document.getElementById('movements-modal');
  const movementsProductName = document.getElementById('movements_product_name');
  const movementsList = document.getElementById('movements-list');

  function csrfToken() {
    const input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : '';
  }

  function digitsOnly(value) {
    return String(value).replace(/\D/g, '');
  }

  // Máscara de moeda (centavos no final): "15050" -> "150,50".
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

  [priceInput, costInput].forEach(function (input) {
    if (input) input.addEventListener('input', function () { maskMoneyInput(input); });
  });

  function bindModal(modal) {
    if (!modal) return;
    const closeBtn = modal.querySelector('.modal-close');
    if (closeBtn) closeBtn.addEventListener('click', function () { closeModal(modal); });
    const cancelBtn = modal.querySelector('.modal-cancel');
    if (cancelBtn) cancelBtn.addEventListener('click', function () { closeModal(modal); });
    modal.addEventListener('click', function (event) {
      if (event.target === modal) closeModal(modal);
    });
  }

  bindModal(productModal);
  bindModal(adjustModal);
  bindModal(movementsModal);

  const openNewBtn = document.getElementById('openNewProductBtn');
  if (openNewBtn) {
    openNewBtn.addEventListener('click', function () {
      productForm.action = '/products/new';
      productTitle.textContent = 'Novo produto';
      productIdInput.value = '';
      nameInput.value = '';
      priceInput.value = '';
      costInput.value = '0,00';
      barcodeInput.value = '';
      stockInput.value = '0';
      minStockInput.value = '0';
      obsInput.value = '';
      activeInput.checked = true;
      openModal(productModal);
      nameInput.focus();
    });
  }

  function openEdit(btn) {
    productForm.action = '/products/edit';
    productTitle.textContent = 'Editar produto';
    productIdInput.value = btn.getAttribute('data-id');
    nameInput.value = btn.getAttribute('data-name');
    priceInput.value = btn.getAttribute('data-price');
    costInput.value = btn.getAttribute('data-cost');
    barcodeInput.value = btn.getAttribute('data-barcode');
    minStockInput.value = btn.getAttribute('data-min-stock');
    obsInput.value = btn.getAttribute('data-obs');
    activeInput.checked = btn.getAttribute('data-active') === '1';
    openModal(productModal);
    nameInput.focus();
  }

  function openAdjust(btn) {
    adjustProductId.value = btn.getAttribute('data-id');
    adjustProductName.textContent = btn.getAttribute('data-name');
    adjustCurrentStock.textContent =
      'Estoque atual: ' + btn.getAttribute('data-stock') + ' unidade(s)';
    adjustDelta.value = '';
    adjustObs.value = '';
    openModal(adjustModal);
    adjustDelta.focus();
  }

  function openMovements(btn) {
    movementsProductName.textContent = btn.getAttribute('data-name');
    movementsList.innerHTML = '<p class="movement-empty">Carregando...</p>';
    openModal(movementsModal);
    fetch('/products/movements/' + btn.getAttribute('data-id'))
      .then(function (response) { return response.text(); })
      .then(function (html) { movementsList.innerHTML = html; });
  }

  document.querySelectorAll('[id^="product-menu-"] .dropdown-item[data-action]').forEach(function (item) {
    item.addEventListener('click', function () {
      const action = item.getAttribute('data-action');
      if (action === 'edit') {
        openEdit(item);
      } else if (action === 'adjust') {
        openAdjust(item);
      } else if (action === 'movements') {
        openMovements(item);
      } else if (action === 'delete') {
        const productId = item.getAttribute('data-id');
        if (!window.confirm('Excluir este produto?')) return;
        fetch('/products/delete/' + productId, {
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