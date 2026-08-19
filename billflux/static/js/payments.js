// BillFlux — interações da página de formas de pagamento.

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
  const modal = document.getElementById('method-modal');
  const form = document.getElementById('method-form');
  const nameInput = document.getElementById('method_name');
  const openNewBtn = document.getElementById('openNewMethodBtn');

  function csrfToken() {
    const input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : '';
  }

  if (openNewBtn) {
    openNewBtn.addEventListener('click', function () {
      form.action = '/payments/new';
      nameInput.value = '';
      openModal(modal);
      nameInput.focus();
    });
  }

  if (modal) {
    const closeBtn = modal.querySelector('.modal-close');
    if (closeBtn) closeBtn.addEventListener('click', function () { closeModal(modal); });
    const cancelBtn = modal.querySelector('.modal-cancel');
    if (cancelBtn) cancelBtn.addEventListener('click', function () { closeModal(modal); });
    modal.addEventListener('click', function (event) {
      if (event.target === modal) closeModal(modal);
    });
  }

  document.querySelectorAll('[id^="method-menu-"] .dropdown-item[data-action]').forEach(function (item) {
    item.addEventListener('click', function () {
      const action = item.getAttribute('data-action');
      const methodId = item.getAttribute('data-id');
      if (action === 'toggle') {
        fetch('/payments/toggle/' + methodId, {
          method: 'POST',
          headers: {
            'X-CSRFToken': csrfToken(),
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }).then(function () {
          window.location.reload();
        });
      } else if (action === 'delete') {
        if (!window.confirm('Excluir esta forma de pagamento?')) return;
        fetch('/payments/delete/' + methodId, {
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