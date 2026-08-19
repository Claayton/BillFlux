// BillFlux — PDV full-screen: busca, carrinho, formas de pagamento e F2.

function formatBRL(value) {
  return 'R$ ' + value.toFixed(2).replace('.', ',')
    .replace(/\B(?=(\d{3})+(?!\d))/g, '.');
}

document.addEventListener('DOMContentLoaded', function () {
  const PRODUCTS = (window.PDV_PRODUCTS || []).map(function (p) {
    return { id: p.id, name: p.name, barcode: (p.barcode || '').toLowerCase(), price: parseFloat(p.price), stock: parseInt(p.stock, 10) };
  });

  const searchInput = document.getElementById('pdv-search');
  const suggestionsEl = document.getElementById('pdv-suggestions');
  const cartItemsEl = document.getElementById('cart-items');
  const cartCountEl = document.getElementById('cart-count');
  const footerCountEl = document.getElementById('footer-count');
  const cartTotalEl = document.getElementById('cart-total');
  const hiddenItemsEl = document.getElementById('pdv-hidden-items');
  const finishBtn = document.getElementById('pdv-finish');
  const methodInput = document.getElementById('payment_method_id');
  const methodButtons = document.querySelectorAll('.pdv-method');
  const panelBlocks = document.querySelectorAll('.pdv-panel-block');

  const cart = new Map(); // id -> { id, name, price, stock, qty }
  let visibleProducts = [];
  let highlighted = -1;

  function byId(productId) {
    return PRODUCTS.find(function (p) { return p.id === productId; });
  }

  function incQty(productId) {
    const product = byId(productId);
    if (!product || product.stock <= 0) return;
    const item = cart.get(productId);
    if (item) {
      if (item.qty < product.stock) item.qty += 1;
    } else {
      cart.set(productId, { id: product.id, name: product.name, price: product.price, stock: product.stock, qty: 1 });
    }
    render();
  }

  function setQty(productId, quantity) {
    const product = byId(productId);
    if (!product || product.stock <= 0) return;
    const target = Math.min(Math.max(1, quantity), product.stock);
    cart.set(productId, { id: product.id, name: product.name, price: product.price, stock: product.stock, qty: target });
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

  // ---------- Busca / sugestões ----------
  function buildSuggestions(term) {
    const lower = term.toLowerCase();
    return PRODUCTS.filter(function (p) {
      return p.name.toLowerCase().indexOf(lower) !== -1 ||
        p.barcode.indexOf(lower) !== -1;
    });
  }

  function setHighlight(index) {
    highlighted = index;
    Array.prototype.forEach.call(suggestionsEl.children, function (el, i) {
      el.classList.toggle('is-highlighted', i === index);
    });
  }

  function showSuggestions(list) {
    visibleProducts = list;
    suggestionsEl.innerHTML = '';
    if (!list.length) {
      suggestionsEl.hidden = true;
      return;
    }
    list.forEach(function (p, i) {
      const btn = document.createElement('button');
      btn.type = 'button';
      btn.className = 'pdv-suggestion';
      btn.innerHTML =
        '<span class="pdv-suggestion-info">' +
        '<span class="pdv-suggestion-name"></span>' +
        '<span class="pdv-suggestion-sub"></span></span>' +
        '<span class="pdv-suggestion-price"></span>' +
        '<span class="pdv-suggestion-stock"></span>';
      btn.querySelector('.pdv-suggestion-name').textContent = p.name;
      btn.querySelector('.pdv-suggestion-sub').textContent =
        p.barcode ? 'Cód.: ' + p.barcode : 'Sem código de barras';
      btn.querySelector('.pdv-suggestion-price').textContent = formatBRL(p.price);
      const stockEl = btn.querySelector('.pdv-suggestion-stock');
      if (p.stock <= 0) {
        stockEl.textContent = 'Esgotado';
        stockEl.classList.add('is-out');
      } else {
        stockEl.textContent = p.stock + ' un';
      }
      btn.addEventListener('click', function () {
        incQty(p.id);
        clearSearch();
      });
      suggestionsEl.appendChild(btn);
    });
    suggestionsEl.hidden = false;
    setHighlight(0);
  }

  function clearSearch() {
    searchInput.value = '';
    suggestionsEl.hidden = true;
    visibleProducts = [];
    highlighted = -1;
    searchInput.focus();
  }

  function handleEnter() {
    const raw = searchInput.value.trim();
    if (!raw) return;

    const multiply = raw.match(/^(\d+)\s*\*\s*(.+)$/);
    if (multiply) {
      const n = parseInt(multiply[1], 10);
      const term = multiply[2].trim().toLowerCase();
      const product = PRODUCTS.find(function (p) { return p.barcode === term; }) ||
        PRODUCTS.find(function (p) { return p.name.toLowerCase() === term; });
      if (product) {
        setQty(product.id, n);
        clearSearch();
        return;
      }
    }

    const lower = raw.toLowerCase();
    const byBarcode = PRODUCTS.find(function (p) { return p.barcode === lower; });
    if (byBarcode) {
      incQty(byBarcode.id);
      clearSearch();
      return;
    }

    if (highlighted >= 0 && visibleProducts[highlighted]) {
      incQty(visibleProducts[highlighted].id);
      clearSearch();
      return;
    }

    if (visibleProducts.length === 1) {
      incQty(visibleProducts[0].id);
      clearSearch();
    }
  }

  if (searchInput) {
    searchInput.addEventListener('input', function () {
      showSuggestions(buildSuggestions(searchInput.value.trim()));
    });
    searchInput.addEventListener('keydown', function (event) {
      if (event.key === 'Enter') {
        event.preventDefault();
        handleEnter();
      } else if (event.key === 'ArrowDown') {
        event.preventDefault();
        if (visibleProducts.length) setHighlight((highlighted + 1) % visibleProducts.length);
      } else if (event.key === 'ArrowUp') {
        event.preventDefault();
        if (visibleProducts.length) setHighlight((highlighted - 1 + visibleProducts.length) % visibleProducts.length);
      } else if (event.key === 'Escape') {
        suggestionsEl.hidden = true;
      }
    });
    searchInput.addEventListener('blur', function () {
      setTimeout(function () { suggestionsEl.hidden = true; }, 150);
    });
  }

  // ---------- Carrinho ----------
  function syncHiddenInputs() {
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

  function render() {
    cartItemsEl.innerHTML = '';
    let total = 0;
    let count = 0;

    if (cart.size === 0) {
      cartItemsEl.innerHTML =
        '<div class="pdv-empty">' +
        '<div class="pdv-empty-icon"><i class="fas fa-shopping-cart"></i></div>' +
        '<h2>Carrinho vazio</h2>' +
        '<p>Digite o código de barras ou o nome do produto para começar.</p>' +
        '</div>';
    } else {
      cart.forEach(function (item) {
        count += item.qty;
        total += item.price * item.qty;

        const row = document.createElement('div');
        row.className = 'pdv-row';
        row.innerHTML =
          '<span class="pdv-row-num">#' + item.id + '</span>' +
          '<span class="pdv-row-qty">' + item.qty + '</span>' +
          '<span class="pdv-row-info"><span class="pdv-row-name"></span><span class="pdv-row-sub"></span></span>' +
          '<span class="pdv-row-price"></span>' +
          '<span class="pdv-row-qty-ctrl"></span>' +
          '<span class="pdv-row-remove"></span>';
        row.querySelector('.pdv-row-name').textContent = item.name;
        row.querySelector('.pdv-row-sub').textContent = formatBRL(item.price) + ' / un';
        row.querySelector('.pdv-row-price').textContent = formatBRL(item.price * item.qty);

        const qtyBox = row.querySelector('.pdv-row-qty-ctrl');
        const minusBtn = document.createElement('button');
        minusBtn.type = 'button';
        minusBtn.setAttribute('aria-label', 'Diminuir quantidade de ' + item.name);
        minusBtn.textContent = '\u2212';
        minusBtn.disabled = item.qty <= 1;
        minusBtn.addEventListener('click', function () { changeQty(item.id, -1); });
        const plusBtn = document.createElement('button');
        plusBtn.type = 'button';
        plusBtn.setAttribute('aria-label', 'Aumentar quantidade de ' + item.name);
        plusBtn.textContent = '+';
        plusBtn.disabled = item.qty >= item.stock;
        plusBtn.addEventListener('click', function () { changeQty(item.id, 1); });
        qtyBox.appendChild(minusBtn);
        qtyBox.appendChild(plusBtn);

        const removeBtn = row.querySelector('.pdv-row-remove');
        removeBtn.innerHTML = '<i class="fas fa-times"></i>';
        removeBtn.setAttribute('aria-label', 'Remover ' + item.name);
        removeBtn.addEventListener('click', function () {
          cart.delete(item.id);
          render();
        });

        cartItemsEl.appendChild(row);
      });
    }

    const label = count + (count === 1 ? ' item' : ' itens');
    cartCountEl.textContent = label;
    footerCountEl.textContent = label;
    cartTotalEl.textContent = formatBRL(total);
    finishBtn.disabled = count === 0;
    syncHiddenInputs();
  }

  // ---------- Formas de pagamento ----------
  methodButtons.forEach(function (btn) {
    btn.addEventListener('click', function () {
      methodButtons.forEach(function (b) { b.classList.remove('is-selected'); });
      btn.classList.add('is-selected');
      methodInput.value = btn.getAttribute('data-id');
    });
  });

  // ---------- Finalizar venda ----------
  function finishSale() {
    if (cart.size === 0) return;
    if (!methodInput.value) {
      panelBlocks.forEach(function (block) {
        block.classList.add('is-attention');
        setTimeout(function () { block.classList.remove('is-attention'); }, 1200);
      });
      return;
    }
    document.getElementById('pdv-form').submit();
  }

  finishBtn.addEventListener('click', finishSale);
  document.addEventListener('keydown', function (event) {
    if (event.key !== 'F2') return;
    event.preventDefault();
    finishSale();
  });

  render();
});