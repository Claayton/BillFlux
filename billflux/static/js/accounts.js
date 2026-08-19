// BillFlux — interações da página de plano de contas.

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
  const modal = document.getElementById('account-modal');
  const form = document.getElementById('account-form');
  const titleEl = document.getElementById('account-modal-title');
  const nameInput = document.getElementById('account_name');
  const typeSelect = document.getElementById('account_type');
  const parentSelect = document.getElementById('account_parent');
  const colorSelect = document.getElementById('account_color');
  const idInput = document.getElementById('account_id');

  const openNewBtn = document.getElementById('openNewAccountBtn');

  function openNew() {
    form.action = '/accounts/new';
    titleEl.textContent = 'Nova categoria';
    idInput.value = '';
    nameInput.value = '';
    typeSelect.value = 'despesa';
    colorSelect.value = '';
    parentSelect.value = '';
    syncParentOptions();
    openModal(modal);
    nameInput.focus();
  }

  // Mostra no seletor de subcategoria apenas categorias do tipo selecionado.
  function syncParentOptions() {
    const wanted = typeSelect.value;
    Array.prototype.forEach.call(parentSelect.querySelectorAll('optgroup'), function (g) {
      const isReceita = g.label === 'Receitas';
      g.hidden = wanted === 'receita' ? !isReceita : isReceita;
    });
    if (parentSelect.selectedOptions.length) {
      const opt = parentSelect.selectedOptions[0];
      const group = opt.closest('optgroup');
      if (group && group.hidden) parentSelect.value = '';
    }
  }

  function openEdit(btn) {
    form.action = '/accounts/edit';
    titleEl.textContent = 'Editar categoria';
    idInput.value = btn.getAttribute('data-id');
    nameInput.value = btn.getAttribute('data-name');
    typeSelect.value = btn.getAttribute('data-type');
    colorSelect.value = btn.getAttribute('data-color');
    parentSelect.value = btn.getAttribute('data-parent');
    syncParentOptions();
    openModal(modal);
    nameInput.focus();
  }

  if (openNewBtn) openNewBtn.addEventListener('click', openNew);
  if (typeSelect) typeSelect.addEventListener('change', syncParentOptions);

  if (modal) {
    const closeBtn = modal.querySelector('.modal-close');
    if (closeBtn) closeBtn.addEventListener('click', function () { closeModal(modal); });
    const cancelBtn = modal.querySelector('.modal-cancel');
    if (cancelBtn) cancelBtn.addEventListener('click', function () { closeModal(modal); });
    modal.addEventListener('click', function (event) {
      if (event.target === modal) closeModal(modal);
    });
  }

  function csrfToken() {
    const input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : '';
  }

  // Ações do menu por linha: Editar / Excluir.
  document.querySelectorAll('[id^="account-menu-"] .dropdown-item[data-action]').forEach(function (item) {
    item.addEventListener('click', function () {
      const action = item.getAttribute('data-action');
      if (action === 'edit') {
        openEdit(item);
      } else if (action === 'delete') {
        const accountId = item.getAttribute('data-id');
        if (!window.confirm('Excluir esta categoria?')) return;
        fetch('/accounts/delete/' + accountId, {
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