// BillFlux — carrinho do PDV.

function formatBRL(value) {
  return 'R$ ' + value.toFixed(2).replace('.', ',')
    .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

document.addEventListener('DOMContentLoaded', function () {
  const grid = document.getElementById('pdv-grid');
  const searchInput = document.getElementById('pdv-search');
  const cartItemsEl = document.getElementById('cart-items');
  const cartCountEl = document.getElementById('cart-count');
  const cartTotalEl = document.getElementById('cart-total');
  const hiddenItemsEl = document.getElementById('pdv-hidden-items');
  const finishBtn = document.getElementById('pdv-finish');

  const products = {};
  document.querySelectorAll('.pdv-product').forEach(function (btn) {
    products[btn.getAttribute('data-id')] = {
      name: btn.getAttribute('data-name'),
      barcode: (btn.getAttribute('data-barcode') || '').toLowerCase(),
      price: parseFloat(btn.getAttribute('data-price')),
      stock: parseInt(btn.getAttribute('data-stock'), 10),
    };
  });

  const cart = new Map(); // id -> { id, name, price, qty, stock }

  function addToCart(productId) {
    const product = products[productId];
    if (!product || product.stock <= 0) return;
    const item = cart.get(productId);
    if (item) {
      if (item.qty >= product.stock) return;
      item.qty += 1;
    } else {
      cart.set(productId, { id: productId, name: product.name, price: product.price, qty: 1, stock: product.stock });
    }
    render();
  }

  function changeQty(productId, delta) {
    const item = cart.get(productId);
    if (!item) return;
    const next = item.qty + delta;
    if (next < 1 || next > item.stock) return;
    item.qty = next;
    render();
  }

  function removeItem(productId) {
    cart.delete(productId);
    render();
  }

  function render() {
    cartItemsEl.innerHTML = '';
    let total = 0;
    let count = 0;

    if (cart.size === 0) {
      cartItemsEl.innerHTML = '<p class="pdv-cart-empty">Nenhum item adicionado.</p>';
    } else {
      cart.forEach(function (item) {
        count += item.qty;
        total += item.price * item.qty;

        const row = document.createElement('div');
        row.className = 'pdv-cart-item';

        const info = document.createElement('div');
        info.className = 'pdv-cart-item-info';
        info.innerHTML =
          '<span class="pdv-cart-item-name"></span>' +
          '<span class="pdv-cart-item-sub"></span>';
        info.querySelector('.pdv-cart-item-name').textContent = item.name;
        info.querySelector('.pdv-cart-item-sub').textContent =
          formatBRL(item.price) + ' / un';

        const qtyBox = document.createElement('div');
        qtyBox.className = 'pdv-cart-item-qty';
        const minusBtn = document.createElement('button');
        minusBtn.type = 'button';
        minusBtn.textContent = '\u2212';
        minusBtn.addEventListener('click', function () { changeQty(item.id, -1); });
        const qtySpan = document.createElement('span');
        qtySpan.textContent = item.qty;
        const plusBtn = document.createElement('button');
        plusBtn.type = 'button';
        plusBtn.textContent = '+';
        plusBtn.addEventListener('click', function () { changeQty(item.id, 1); });
        qtyBox.appendChild(minusBtn);
        qtyBox.appendChild(qtySpan);
        qtyBox.appendChild(plusBtn);

        const line = document.createElement('span');
        line.className = 'pdv-cart-item-line';
        line.textContent = formatBRL(item.price * item.qty);

        const removeBtn = document.createElement('button');
        removeBtn.type = 'button';
        removeBtn.className = 'pdv-cart-item-remove';
        removeBtn.setAttribute('aria-label', 'Remover item');
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.addEventListener('click', function () { removeItem(item.id); });

        row.appendChild(info);
        row.appendChild(qtyBox);
        row.appendChild(line);
        row.appendChild(removeBtn);
        cartItemsEl.appendChild(row);
      });
    }

    cartCountEl.textContent = count;
    cartTotalEl.textContent = formatBRL(total);
    finishBtn.disabled = count === 0;

    hiddenItemsEl.innerHTML = '';
    cart.forEach(function (item) {
      const idInput = document.createElement('input');
      idInput.type = 'hidden';
      idInput.name = 'product_id';
      idInput.value = item.id;
      const qtyInput = document.createElement('input');
      qtyInput.type = 'hidden';
      qtyInput.name = 'quantity';
      qtyInput.value = item.qty;
      hiddenItemsEl.appendChild(idInput);
      hiddenItemsEl.appendChild(qtyInput);
    });
  }

  if (grid) {
    grid.addEventListener('click', function (event) {
      const btn = event.target.closest('.pdv-product');
      if (!btn) return;
      addToCart(btn.getAttribute('data-id'));
    });
  }

  // Busca por nome ou código de barras (filter + Enter = adiciona).
  function applySearch() {
    const term = (searchInput.value || '').toLowerCase().trim();
    document.querySelectorAll('.pdv-product').forEach(function (btn) {
      const text = (btn.getAttribute('data-name') + ' ' + (btn.getAttribute('data-barcode') || '')).toLowerCase();
      btn.hidden = term && text.indexOf(term) === -1;
    });
  }

  if (searchInput) {
    searchInput.addEventListener('input', applySearch);
    searchInput.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter') return;
      event.preventDefault();
      const term = (searchInput.value || '').toLowerCase().trim();
      if (!term) return;

      let matched = null;
      Object.keys(products).forEach(function (id) {
        if (products[id].barcode === term) matched = id;
      });
      if (matched) {
        addToCart(matched);
        searchInput.value = '';
        applySearch();
        return;
      }

      const visible = document.querySelectorAll('.pdv-product:not([hidden])');
      if (visible.length === 1) {
        addToCart(visible[0].getAttribute('data-id'));
        searchInput.value = '';
        applySearch();
      }
    });
  }

  render();
});