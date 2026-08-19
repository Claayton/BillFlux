// BillFlux — gerenciamento de modais e interações da página de contas.

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

// Remove tudo que não for dígito.
function digitsOnly(text) {
  return text.replace(/\D/g, '');
}

// Formata um número em reais: 301.29 -> "301,29", 1240.2 -> "1.240,20".
function formatMoney(value) {
  var fixed = value.toFixed(2);
  var parts = fixed.split('.');
  return parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, '.') + ',' + parts[1];
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

// Formata uma data ISO "2026-09-01" como "01/09/2026".
function formatDateBr(iso) {
  if (!iso) return '-';
  const parts = iso.split('-');
  if (parts.length !== 3) return iso;
  return parts[2] + '/' + parts[1] + '/' + parts[0];
}

// Uma data decodificada só é preenchida automaticamente se não estiver há
// mais de 7 dias no passado (datas futuras e recentes são preenchidas).
function shouldAutofillDate(isoDate) {
  if (!isoDate) return false;
  const d = new Date(isoDate + 'T00:00:00');
  if (isNaN(d.getTime())) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const limit = new Date(today);
  limit.setDate(limit.getDate() - 7);
  return d >= limit;
}

// Formata a linha digitável (47/48) em blocos para leitura; 44 fica como está.
function formatLinhaDigitavel(code) {
  var d = digitsOnly(code);
  if (d.length === 48) {
    return d.match(/.{12}/g).join(' ');
  }
  if (d.length === 47) {
    return [
      d.slice(0, 5) + '.' + d.slice(5, 10),
      d.slice(10, 15) + '.' + d.slice(15, 21),
      d.slice(21, 26) + '.' + d.slice(26, 32),
      d.slice(32),
    ].join(' ');
  }
  return d;
}

// Copia um texto para a área de transferência, com fallback para seleção manual.
function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    return navigator.clipboard.writeText(text).then(function () {
      return true;
    });
  }
  const input = document.createElement('textarea');
  input.value = text;
  input.style.position = 'fixed';
  input.style.opacity = '0';
  document.body.appendChild(input);
  input.select();
  const ok = document.execCommand('copy');
  document.body.removeChild(input);
  return Promise.resolve(ok);
}

// Converte linha digitável (47/48) ou código (44) em código de 44 dígitos.
function toBarcode(raw) {
  var digits = digitsOnly(raw);
  if (digits.length === 47) {
    return digits.slice(0, 4) + digits[32] + digits.slice(33) +
      digits.slice(4, 9) + digits.slice(10, 20) + digits.slice(21, 31);
  }
  if (digits.length === 48) {
    return digits.slice(0, 11) + digits.slice(12, 23) + digits.slice(24, 35) + digits.slice(36, 47);
  }
  if (digits.length === 44) {
    return digits;
  }
  return null;
}

// Valida o dígito verificador geral (módulo 11, pesos 2-9) do código de 44 dígitos.
function checkDvGeral(code) {
  if (code.length !== 44) return false;
  const dvPos = code[0] === '8' ? 3 : 4;
  const base = code.slice(0, dvPos) + code.slice(dvPos + 1);
  let sum = 0;
  for (let i = 0; i < base.length; i++) {
    sum += parseInt(base[base.length - 1 - i], 10) * (i % 8 + 2);
  }
  const resto = sum % 11;
  const dv = (resto === 0 || resto === 1) ? 0 : 11 - resto;
  return dv === parseInt(code[dvPos], 10);
}

// Extrai valor e vencimento de um código de barras brasileiro.
function decodeBarcode(raw) {
  var code = toBarcode(raw);
  if (!code || !checkDvGeral(code)) return null;
  var result = { value: null, vencimento: null };

  if (code[0] === '8') {
    if (code[2] === '6' || code[2] === '8') {
      result.value = parseInt(code.slice(4, 15), 10) / 100;
    }
    var y = parseInt(code.slice(19, 23), 10);
    var m = parseInt(code.slice(23, 25), 10);
    var d = parseInt(code.slice(25, 27), 10);
    if (y >= 1 && m >= 1 && m <= 12 && d >= 1 && d <= 31) {
      result.vencimento = String(y).padStart(4, '0') + '-' +
        String(m).padStart(2, '0') + '-' + String(d).padStart(2, '0');
    }
  } else {
    result.value = parseInt(code.slice(9, 19), 10) / 100;
    var factor = parseInt(code.slice(5, 9), 10);
    if (factor >= 1000 && factor <= 9999) {
      var ms = Date.UTC(1997, 9, 7) + (factor - 1000) * 86400000;
      result.vencimento = new Date(ms).toISOString().slice(0, 10);
    }
  }

  return result;
}

document.addEventListener('DOMContentLoaded', function () {
  // Modal de cadastro
  const insertModal = document.getElementById('insert-modal');
  const openInsertBtn = document.getElementById('openInsertModalBtn');
  const openInsertBtnEmpty = document.getElementById('openInsertModalBtnEmpty');

  function openInsertModal() {
    openModal(insertModal);
  }

  if (openInsertBtn) openInsertBtn.addEventListener('click', openInsertModal);
  if (openInsertBtnEmpty) openInsertBtnEmpty.addEventListener('click', openInsertModal);

  // Fecha qualquer modal pelo botão "X" ou "Cancelar"
  document.querySelectorAll('.modal').forEach(function (modal) {
    const closeBtn = modal.querySelector('.modal-close');
    if (closeBtn) closeBtn.addEventListener('click', function () { closeModal(modal); });

    const cancelBtn = modal.querySelector('.modal-cancel');
    if (cancelBtn) cancelBtn.addEventListener('click', function () { closeModal(modal); });

    // Fecha ao clicar fora do conteúdo
    modal.addEventListener('click', function (event) {
      if (event.target === modal) closeModal(modal);
    });
  });

  // Modal de detalhes (abre ao clicar na linha ou no menu de ações).
  const detailsModal = document.getElementById('modal');
  const detailsModalEl = document.getElementById('modal-details');

  function fillDetailsItem(name, value) {
    const el = detailsModalEl.querySelector('[data-d="' + name + '"]');
    if (el) el.textContent = value || '-';
  }

  function showDetails(id) {
    const data = document.querySelector('.row-data[data-id="' + id + '"]');
    if (!data || !detailsModal) return;
    const row = document.querySelector('.account-row[data-id="' + id + '"]');
    const statusKey = row ? row.getAttribute('data-status') : '';
    const statusLabel = {
      paga: 'Paga',
      vencida: 'Vencida',
      hoje: 'Vence hoje',
      amanha: 'Vence amanhã',
      pendente: 'Pendente',
      semvenc: 'Sem vencimento',
    }[statusKey] || '-';
    const rawValue = data.getAttribute('data-value');
    fillDetailsItem('status', statusLabel);
    fillDetailsItem('reference', data.getAttribute('data-reference'));
    fillDetailsItem('suplyer', data.getAttribute('data-suplyer'));
    fillDetailsItem('category', data.getAttribute('data-account-name'));
    fillDetailsItem('due', formatDateBr(data.getAttribute('data-due')));
    fillDetailsItem('value', rawValue ? 'R$ ' + formatMoney(parseFloat(rawValue)) : '-');
    fillDetailsItem('doc', data.getAttribute('data-bar-code'));
    fillDetailsItem('created', formatDateBr(data.getAttribute('data-created')));
    fillDetailsItem('obs', data.getAttribute('data-obs'));
    openModal(detailsModal);
  }

  // Linha inteira clicável, exceto quando o clique for em um controle.
  document.querySelectorAll('.account-row').forEach(function (row) {
    row.addEventListener('click', function (event) {
      if (event.target.closest('a, button, select, input, .dropdown-panel')) return;
      const id = row.getAttribute('data-id');
      if (id) showDetails(id);
    });
  });

  // Preenchimento automático a partir do código de barras + máscara de moeda
  const barCodeInput = document.getElementById('bar_code');
  const valueInput = document.getElementById('value');
  const vencimentoInput = document.getElementById('vencimento');

  if (barCodeInput && valueInput && vencimentoInput) {
    barCodeInput.addEventListener('input', function () {
      const decoded = decodeBarcode(barCodeInput.value);
      if (!decoded) return;
      if (decoded.value !== null && valueInput.value === '') {
        valueInput.value = formatMoney(decoded.value);
      }
      if (shouldAutofillDate(decoded.vencimento) && vencimentoInput.value === '') {
        vencimentoInput.value = decoded.vencimento;
      }
    });

    valueInput.addEventListener('input', function () {
      maskMoneyInput(valueInput);
    });
  }

  // Enter não submete o formulário (o leitor de código de barras emite Enter
  // no fim): apenas avança para o próximo campo. O modal só salva pelo botão.
  function setupEnterNavigation(form) {
    if (!form) return;
    form.addEventListener('keydown', function (event) {
      if (event.key !== 'Enter') return;
      const target = event.target;
      if (target.tagName !== 'INPUT') return;
      const inputs = Array.prototype.filter.call(
        form.querySelectorAll('input'),
        function (el) { return el.type !== 'hidden'; }
      );
      const idx = inputs.indexOf(target);
      if (idx === -1) return;
      event.preventDefault();
      const next = inputs[idx + 1];
      if (next) next.focus();
    });
  }
  setupEnterNavigation(document.getElementById('insert-boletoForm'));
  setupEnterNavigation(document.getElementById('edit-boletoForm'));

  // Ações da tabela: Pagar / Editar / Excluir
  function csrfToken() {
    const input = document.querySelector('input[name="csrf_token"]');
    return input ? input.value : '';
  }

  function postAction(url) {
    return fetch(url, {
      method: 'POST',
      headers: {
        'X-CSRFToken': csrfToken(),
        'Content-Type': 'application/x-www-form-urlencoded',
      },
    });
  }

  const editModal = document.getElementById('edit-modal');

  function editBill(id) {
    const data = document.querySelector('.row-data[data-id="' + id + '"]');
    if (!data || !editModal) return;

    document.getElementById('edit_bill_id').value = id;

    const value = parseFloat(data.getAttribute('data-value'));
    document.getElementById('edit_value').value =
      isNaN(value) ? '' : formatMoney(value);
    document.getElementById('edit_vencimento').value = data.getAttribute('data-due');
    document.getElementById('edit_reference').value = data.getAttribute('data-reference');
    document.getElementById('edit_suplyer').value = data.getAttribute('data-suplyer');
    const editCategory = document.getElementById('edit_bill_category');
    if (editCategory) editCategory.value = data.getAttribute('data-account');
    document.getElementById('edit_obs').value = data.getAttribute('data-obs');
    document.getElementById('edit_bar_code').value = data.getAttribute('data-bar-code');
    document.getElementById('edit_pix_key').value = data.getAttribute('data-pix-key');
    document.getElementById('edit_pix_payload').value = data.getAttribute('data-pix-payload');
    document.getElementById('edit_pix_image').value = data.getAttribute('data-pix-image');

    openModal(editModal);
  }

  const payModal = document.getElementById('pay-modal');
  let currentPayBillId = null;
  let currentPayCode = '';
  let currentPayValue = null;
  let currentPaySuplyer = '';
  let currentPayKey = '';
  let currentPayPayload = '';
  let currentPayImage = '';

  function renderPayBarcode(code) {
    const svg = document.getElementById('pay-codigo-barras');
    const empty = document.getElementById('pay-barcode-empty');
    if (!svg) return;
    svg.innerHTML = '';
    const digits = digitsOnly(code);
    const normalized = toBarcode(digits);
    const barcode44 = normalized || (digits.length === 44 ? digits : '');
    if (!barcode44 || typeof JsBarcode === 'undefined') {
      svg.setAttribute('hidden', '');
      if (empty) empty.hidden = false;
      return;
    }
    // 405 módulos do código + zona de silêncio (10 módulos de cada lado).
    const totalModules = 425;
    const parent = svg.parentElement;
    const maxWidth = parent && parent.clientWidth ? parent.clientWidth - 24 : window.innerWidth - 80;
    const module = Math.max(2, Math.min(Math.floor(maxWidth / totalModules), 6));
    JsBarcode(svg, barcode44, {
      format: 'ITF',
      displayValue: false,
      width: module,
      height: Math.round(module * 47.5),
      margin: module * 10,
    });
    svg.removeAttribute('hidden');
    if (empty) empty.hidden = true;
  }

  function payBill(id) {
    const data = document.querySelector('.row-data[data-id="' + id + '"]');
    if (!data || !payModal) return;

    currentPayBillId = id;
    const code = data.getAttribute('data-bar-code') || '';
    currentPayCode = code;
    const rawValue = data.getAttribute('data-value');
    currentPayValue = rawValue ? parseFloat(rawValue) : null;
    currentPaySuplyer = data.getAttribute('data-suplyer') || '';
    currentPayKey = data.getAttribute('data-pix-key') || '';
    currentPayPayload = data.getAttribute('data-pix-payload') || '';
    currentPayImage = data.getAttribute('data-pix-image') || '';
    const value = currentPayValue;

    document.getElementById('pay-modal-barcode').textContent = formatLinhaDigitavel(code) || '-';
    document.getElementById('pay-modal-value').textContent = isNaN(value) ? '-' : 'R$ ' + formatMoney(value);
    document.getElementById('pay-modal-due').textContent = formatDateBr(data.getAttribute('data-due'));
    document.getElementById('pay-modal-reference').textContent = data.getAttribute('data-reference') || '-';
    document.getElementById('pay-modal-suplyer').textContent = data.getAttribute('data-suplyer') || '-';
    document.getElementById('pay-modal-type').textContent = data.getAttribute('data-account-name') || data.getAttribute('data-bill-type') || '-';
    document.getElementById('pay-modal-obs').textContent = data.getAttribute('data-obs') || '-';

    openModal(payModal);
    requestAnimationFrame(function () {
      renderPayBarcode(code);
    });

    // Aba inicial conforme o que foi cadastrado: só PIX -> PIX; só barcode ->
    // barcode; ambos -> PIX com opção de trocar. Esconde abas sem conteúdo.
    const hasBarcode = Boolean(currentPayCode);
    const hasPix = Boolean(currentPayKey || currentPayPayload || currentPayImage);
    const barcodeTab = document.querySelector('.pay-tab[data-pay-tab="barcode"]');
    const pixTab = document.querySelector('.pay-tab[data-pay-tab="pix"]');
    if (pixTab) pixTab.hidden = !hasPix;
    if (barcodeTab) barcodeTab.hidden = !hasBarcode && hasPix;
    const pixHint = document.getElementById('pix-hint');
    if (pixHint) pixHint.hidden = Boolean(currentPayPayload || currentPayImage) || !currentPayKey;
    activatePayTab(hasPix ? 'pix' : 'barcode');
    if (hasPix) renderPix();
  }

  const payCopyButton = document.getElementById('pay-copy');
  if (payCopyButton) {
    payCopyButton.addEventListener('click', function () {
      const code = digitsOnly(document.getElementById('pay-modal-barcode').textContent);
      if (!code) return;
      copyToClipboard(code).then(function (ok) {
        payCopyButton.textContent = ok ? 'Copiado!' : 'Copiar código';
        if (ok) {
          setTimeout(function () { payCopyButton.textContent = 'Copiar código'; }, 1500);
        }
      });
    });
  }

  // Reajusta o código de barras se a janela for redimensionada com o modal aberto.
  if (payModal) {
    window.addEventListener('resize', function () {
      if (payModal.classList.contains('is-open')) renderPayBarcode(currentPayCode);
    });
  }

  // Abas do modal de pagamento: Código de barras | PIX.
  function activatePayTab(name) {
    document.querySelectorAll('.pay-tab').forEach(function (t) { t.classList.remove('is-active'); });
    const tab = document.querySelector('.pay-tab[data-pay-tab="' + name + '"]');
    if (tab) tab.classList.add('is-active');
    const barcodePane = document.getElementById('pay-pane-barcode');
    const pixPane = document.getElementById('pay-pane-pix');
    if (barcodePane) barcodePane.hidden = name !== 'barcode';
    if (pixPane) pixPane.hidden = name !== 'pix';
  }

  document.querySelectorAll('.pay-tab').forEach(function (tab) {
    tab.addEventListener('click', function () {
      activatePayTab(tab.getAttribute('data-pay-tab'));
    });
  });

  // CRC-16/CCITT-FALSE (polinômio 0x1021, inicial 0xFFFF) exigido pelo PIX.
  function crc16Pix(data) {
    let crc = 0xFFFF;
    for (let i = 0; i < data.length; i++) {
      crc ^= data.charCodeAt(i) << 8;
      for (let j = 0; j < 8; j++) {
        crc = (crc & 0x8000) ? ((crc << 1) ^ 0x1021) & 0xFFFF : (crc << 1) & 0xFFFF;
      }
    }
    return crc.toString(16).toUpperCase().padStart(4, '0');
  }

  function emvField(id, value) {
    return id + String(value.length).padStart(2, '0') + value;
  }

  // Remove acentos e deixa apenas caracteres ASCII seguros.
  function ascii(text) {
    return String(text)
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .replace(/[^A-Za-z0-9 ]/g, ' ')
      .replace(/\s+/g, ' ')
      .trim()
      .toUpperCase();
  }

  function randomTxid() {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789';
    let out = '';
    for (let i = 0; i < 8; i++) out += chars[Math.floor(Math.random() * chars.length)];
    return out;
  }

  function buildPixPayload(key, amount, name, city) {
    const merchantInfo = emvField('00', 'br.gov.bcb.pix') + emvField('01', key);
    let payload =
      emvField('00', '01') +
      emvField('26', merchantInfo) +
      emvField('52', '0000') +
      emvField('53', '986') +
      emvField('54', amount.toFixed(2)) +
      emvField('58', 'BR') +
      emvField('59', name) +
      emvField('60', city) +
      emvField('62', emvField('05', randomTxid()));
    return payload + '6304' + crc16Pix(payload + '6304');
  }

  function renderPixQr(text) {
    const svg = document.getElementById('pix-qr-svg');
    if (!svg) return;
    svg.innerHTML = '';
    if (typeof qrcode === 'undefined') return;
    const qr = qrcode(0, 'M');
    qr.addData(text);
    qr.make();
    svg.innerHTML = qr.createSvgTag({ cellSize: 8, margin: 2, scalable: true });
  }

  // Mostra o QR PIX: imagem salva (quando a leitura falhou) tem prioridade,
  // depois o payload exato lido, e por fim a geração a partir da chave.
  function renderPix() {
    const payloadEl = document.getElementById('pix-copiacola');
    const pixImg = document.getElementById('pix-img');
    const pixSvg = document.getElementById('pix-qr-svg');
    const pixQrBox = document.querySelector('#pay-pane-pix .pix-qr');
    if (!payloadEl) return;

    if (currentPayImage) {
      if (pixImg) { pixImg.src = currentPayImage; pixImg.hidden = false; }
      if (pixSvg) pixSvg.hidden = true;
      if (pixQrBox) pixQrBox.hidden = true;
      const payload = currentPayPayload || '';
      payloadEl.textContent = payload;
      setPixCopyVisible(Boolean(payload));
      return;
    }
    if (pixImg) pixImg.hidden = true;
    if (pixSvg) pixSvg.hidden = false;
    if (pixQrBox) pixQrBox.hidden = false;

    if (currentPayPayload) {
      payloadEl.textContent = currentPayPayload;
      renderPixQr(currentPayPayload);
      setPixCopyVisible(true);
      return;
    }
    if (!currentPayKey) {
      setPixCopyVisible(false);
      return;
    }
    if (currentPayValue === null || isNaN(currentPayValue) || currentPayValue <= 0) {
      setPixCopyVisible(false);
      return;
    }
    const name = (ascii(currentPaySuplyer) || 'RECEBEDOR').slice(0, 25);
    const payload = buildPixPayload(currentPayKey, currentPayValue, name, 'BRASILIA');
    payloadEl.textContent = payload;
    renderPixQr(payload);
    setPixCopyVisible(true);
  }

  function setPixCopyVisible(visible) {
    const label = document.getElementById('pix-copiacola-label');
    const text = document.getElementById('pix-copiacola');
    const copy = document.getElementById('pix-copy');
    if (label) label.hidden = !visible;
    if (text) text.hidden = !visible;
    if (copy) copy.hidden = !visible;
  }

  // Lê o QR Code PIX a partir de uma imagem enviada no cadastro.
  const pixQrImage = document.getElementById('pix_qr_image');
  const pixUploadStatus = document.getElementById('pix_upload_status');
  const pixImageInput = document.getElementById('pix_image');

  function setPixStatus(message, ok) {
    if (!pixUploadStatus) return;
    pixUploadStatus.textContent = message;
    pixUploadStatus.hidden = false;
    pixUploadStatus.classList.toggle('is-ok', ok);
    pixUploadStatus.classList.toggle('is-error', !ok);
  }

  // Guarda a imagem exatamente como enviada (arquivo ou Ctrl+V), sem
  // converter/redimensionar — o que aparece no pagamento é o print original.
  function applyPixImage(dataUrl) {
    if (pixImageInput) pixImageInput.value = dataUrl;
    const preview = document.getElementById('pix_qr_preview');
    if (preview) {
      preview.src = dataUrl;
      preview.hidden = false;
    }
    setPixStatus('Imagem do QR PIX salva com sucesso!', true);
  }

  // Só reduz imagens muito grandes (>4MB) para não sobrecarregar o banco.
  function downscaleBigImage(file) {
    const image = new Image();
    image.onload = function () {
      const maxDim = Math.max(image.naturalWidth, image.naturalHeight);
      const scale = Math.min(1, 1400 / maxDim);
      const canvas = document.createElement('canvas');
      canvas.width = Math.round(image.naturalWidth * scale);
      canvas.height = Math.round(image.naturalHeight * scale);
      const ctx = canvas.getContext('2d');
      ctx.drawImage(image, 0, 0, canvas.width, canvas.height);
      applyPixImage(canvas.toDataURL('image/png'));
    };
    image.onerror = function () {
      setPixStatus('Não foi possível carregar a imagem.', false);
    };
    image.src = URL.createObjectURL(file);
  }

  function handlePixImage(file) {
    if (file.size > 4 * 1024 * 1024) {
      downscaleBigImage(file);
      return;
    }
    const reader = new FileReader();
    reader.onload = function () {
      applyPixImage(reader.result);
    };
    reader.onerror = function () {
      setPixStatus('Não foi possível carregar a imagem.', false);
    };
    reader.readAsDataURL(file);
  }

  if (pixQrImage && pixUploadStatus && pixImageInput) {
    pixQrImage.addEventListener('change', function () {
      const file = pixQrImage.files && pixQrImage.files[0];
      if (!file) return;
      handlePixImage(file);
    });

    // Ctrl+V em qualquer lugar do formulário de cadastro: se a área de
    // transferência tiver uma imagem, salva ela.
    const insertForm = document.getElementById('insert-boletoForm');
    if (insertForm) {
      insertForm.addEventListener('paste', function (event) {
        const items = event.clipboardData && event.clipboardData.items;
        if (!items) return;
        for (let i = 0; i < items.length; i++) {
          if (items[i].type && items[i].type.indexOf('image/') === 0) {
            const file = items[i].getAsFile();
            if (file) {
              event.preventDefault();
              handlePixImage(file);
            }
            return;
          }
        }
      });
    }
  }

  const pixCopy = document.getElementById('pix-copy');
  if (pixCopy) {
    pixCopy.addEventListener('click', function () {
      const code = document.getElementById('pix-copiacola').textContent;
      if (!code) return;
      copyToClipboard(code).then(function (ok) {
        pixCopy.textContent = ok ? 'Copiado!' : 'Copiar código PIX';
        if (ok) {
          setTimeout(function () { pixCopy.textContent = 'Copiar código PIX'; }, 1500);
        }
      });
    });
  }

  const paySaveButton = document.getElementById('pay-save-button');
  if (paySaveButton) {
    paySaveButton.addEventListener('click', function () {
      if (!currentPayBillId) return;
      if (!window.confirm('Confirmar o pagamento desta conta?')) return;
      postAction('/bills/pay/' + currentPayBillId).then(function () {
        window.location.reload();
      });
    });
  }

  function deleteBill(id) {
    if (!window.confirm('Excluir esta conta?')) return;
    postAction('/bills/delete/' + id).then(function () {
      window.location.reload();
    });
  }

  // Menu de ações por linha (⋯): Ver detalhes, Editar, Marcar como paga, Excluir.
  document.querySelectorAll('[id^="row-menu-"] .dropdown-item[data-action]').forEach(function (item) {
    item.addEventListener('click', function () {
      const action = item.getAttribute('data-action');
      const billId = item.getAttribute('data-id');
      if (!billId) return;
      if (action === 'details') showDetails(billId);
      else if (action === 'edit') editBill(billId);
      else if (action === 'pay') payBill(billId);
      else if (action === 'delete') deleteBill(billId);
    });
  });

  const editValueInput = document.getElementById('edit_value');
  if (editValueInput) {
    editValueInput.addEventListener('input', function () {
      maskMoneyInput(editValueInput);
    });
  }

  // Busca e filtros da tabela (client-side).
  const searchInput = document.getElementById('search');
  const statusFilter = document.getElementById('filter-status');
  const periodFilter = document.getElementById('filter-period');
  const typeFilter = document.getElementById('filter-type');
  const moreFiltersBtn = document.getElementById('more-filters-btn');
  const filterAdvanced = document.getElementById('filter-advanced');
  const noResultsRow = document.getElementById('no-results-row');
  const clearFiltersBtn = document.getElementById('clear-filters-btn');
  const rows = Array.prototype.slice.call(document.querySelectorAll('.account-row'));

  function todayIso() {
    const d = new Date();
    return d.getFullYear() + '-' +
      String(d.getMonth() + 1).padStart(2, '0') + '-' +
      String(d.getDate()).padStart(2, '0');
  }

  function monthOf(iso) {
    return iso ? iso.slice(0, 7) : null;
  }

  function shiftMonth(ym, delta) {
    const parts = ym.split('-');
    let y = parseInt(parts[0], 10);
    let m = parseInt(parts[1], 10) + delta;
    while (m < 1) { m += 12; y -= 1; }
    while (m > 12) { m -= 12; y += 1; }
    return y + '-' + String(m).padStart(2, '0');
  }

  function daysUntil(iso) {
    if (!iso) return null;
    const due = new Date(iso + 'T00:00:00');
    const now = new Date(todayIso() + 'T00:00:00');
    return Math.round((due - now) / 86400000);
  }

  function applyFilters() {
    const term = (searchInput ? searchInput.value : '').toLowerCase().trim();
    const status = statusFilter ? statusFilter.value : 'Todas';
    const period = periodFilter ? periodFilter.value : 'todos';
    const typeTerm = (typeFilter ? typeFilter.value : '').toLowerCase().trim();
    const thisMonth = monthOf(todayIso());
    const prevMonth = shiftMonth(thisMonth, -1);

    let visible = 0;
    rows.forEach(function (row) {
      const statusKey = row.getAttribute('data-status') || '';
      const due = row.getAttribute('data-due') || '';
      let show = true;

      if (term && (row.getAttribute('data-search') || '').indexOf(term) === -1) show = false;
      if (show && status !== 'Todas') {
        if (status === 'NaoPagas' && statusKey === 'paga') show = false;
        if (status === 'Pagas' && statusKey !== 'paga') show = false;
        if (status === 'Vencidas' && statusKey !== 'vencida') show = false;
        if (status === 'AVencer' && !(statusKey === 'pendente' || statusKey === 'hoje' || statusKey === 'amanha')) show = false;
        if (status === 'Hoje' && statusKey !== 'hoje') show = false;
      }
      if (show && period !== 'todos') {
        const dueMonth = monthOf(due);
        const days = daysUntil(due);
        if (period === 'este-mes' && dueMonth !== thisMonth) show = false;
        if (period === 'mes-passado' && dueMonth !== prevMonth) show = false;
        if (period === 'proximos-30' && (days === null || days < 0 || days > 30)) show = false;
        if (period === 'vencidas' && statusKey !== 'vencida') show = false;
      }
      if (show && typeTerm && (row.getAttribute('data-type') || '').indexOf(typeTerm) === -1) show = false;

      row.hidden = !show;
      if (show) visible++;
    });

    if (noResultsRow) noResultsRow.hidden = rows.length === 0 || visible !== 0;
  }

  function clearFilters() {
    if (searchInput) searchInput.value = '';
    if (statusFilter) statusFilter.value = 'Todas';
    if (periodFilter) periodFilter.value = 'todos';
    if (typeFilter) typeFilter.value = '';
    applyFilters();
  }

  if (searchInput) searchInput.addEventListener('input', applyFilters);
  if (statusFilter) statusFilter.addEventListener('change', applyFilters);
  if (periodFilter) periodFilter.addEventListener('change', applyFilters);
  if (typeFilter) typeFilter.addEventListener('input', applyFilters);
  if (clearFiltersBtn) clearFiltersBtn.addEventListener('click', clearFilters);
  if (moreFiltersBtn && filterAdvanced) {
    moreFiltersBtn.addEventListener('click', function () {
      const open = filterAdvanced.hidden;
      filterAdvanced.hidden = !open;
      moreFiltersBtn.setAttribute('aria-expanded', open ? 'true' : 'false');
      if (open && typeFilter) typeFilter.focus();
    });
  }

  // Ações do menu da toolbar (⋯): Imprimir / Limpar filtros.
  const toolbarMenu = document.getElementById('toolbar-menu');
  if (toolbarMenu) {
    toolbarMenu.querySelectorAll('.dropdown-item[data-action]').forEach(function (item) {
      item.addEventListener('click', function () {
        const action = item.getAttribute('data-action');
        if (action === 'imprimir') window.print();
        else if (action === 'limpar') clearFilters();
      });
    });
  }
});