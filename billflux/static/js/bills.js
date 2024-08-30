// Script para exibir o modal do botao de cadastrar novo boleto:

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('insert-modal');
    const openModalBtn = document.getElementById('openInsertModalBtn');
    const closeModalBtn = document.querySelector('.close');
    const barCodeInput = document.getElementById('bar_code');

    // Abre o modal
    openModalBtn.addEventListener('click', () => {
        modal.style.display = 'block';
        barCodeInput.focus();
    });

    // Fecha o modal quando o usuário clica no "X"
    closeModalBtn.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    // Fecha o modal se o usuário clicar fora do conteúdo do modal
    window.addEventListener('click', (event) => {
        if (event.target == modal) {
            modal.style.display = 'none';
        }
    });
});

// Script para exibir o modal dos campos referente a e observações:

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('modal');
    const btns = document.querySelectorAll('.view-details-btn');
    const span = document.getElementsByClassName('close')[0];
    const modalText = document.getElementById('modal-text');

    btns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Define o conteúdo do modal
            const text = btn.getAttribute('data-details');
            modalText.innerText = text;

            modal.style.display = 'block';
        });
    });

    span.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    window.addEventListener('click', (event) => {
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });
});

/// Script para excluir linha da tabela:
document.addEventListener('DOMContentLoaded', function() {

    document.querySelectorAll('#option-bill').forEach(function(selectElement) {
        selectElement.addEventListener('change', function(event) {
            var action = event.target.value;
            var row = event.target.closest('tr'); // Encontra a linha mais próxima do select
            const billId = this.getAttribute('data-id');
            var id = row.getAttribute('data-id'); // Obtém o ID da linha
            
            // Verifica a ação selecionada
            if (action === 'Excluir') {
                if (confirm('Tem certeza que deseja excluir este item?')) {
                    // Envia uma requisição para o backend para excluir o item
                    fetch(`/delete_bill/${billId}`, {
                        method: 'DELETE',
                        headers: {
                            'Content-Type': 'application/json'
                        }
                    }).then(response => {
                        if (response.ok) {
                            row.remove(); // Remove a linha da tabela
                        } else {
                            alert('Erro ao excluir o item.');
                        }
                    }).catch(error => {
                        console.error('Erro:', error);
                        alert('Erro ao excluir o item.');
                    });
                }
            }
            // Adicione mais ações aqui para 'Pagar' e 'Editar' se necessário
        });
    });
});

/// Script para pegar o codigo do boleto e extrair as informações necessarias
document.addEventListener('DOMContentLoaded', (event) => {
    const barCodeInput = document.getElementById('bar_code');
    const valueInput = document.getElementById('value');
    const vencimentoInput = document.getElementById('vencimento-input');
    const referenceInput = document.getElementById('reference'); // Campo "Referente a"

    if (barCodeInput) {
        // Evento para quando o campo perde o foco
        barCodeInput.addEventListener('blur', function() {
            const barCodeValue = barCodeInput.value.replace(/\D/g, '');
            console.log('Código de barras:', barCodeValue);
            // Aqui você pode fazer o que quiser com o valor do código de barras

            if (barCodeValue.length !== 47) {
                throw new Error('Linha digitável inválida. Deve conter 47 dígitos.');
            }

            // Data base: 7 de outubro de 1997
            const BASE_DATE = new Date(1997, 9, 7); 
            const fatorVencimento = parseInt(barCodeValue.substring(33, 37), 10);
            const valorBoleto = barCodeValue.substring(37, 47);

            // Calcula a data de vencimento
            const vencimentoDate = new Date(BASE_DATE.getTime() + (fatorVencimento * 24 * 60 * 60 * 1000));
            // Formata o valor do boleto
            const valor = (parseFloat(valorBoleto) / 100).toFixed(2);

            // Verifica se a data de vencimento é válida
            if (isNaN(vencimentoDate.getTime())) {
                alert('Data de vencimento inválida.');
                return;
            }

            function formatDateForInput(date) {
                const day = String(date.getDate()).padStart(2, '0');
                const month = String(date.getMonth() + 1).padStart(2, '0'); // Meses são zero-indexados
                const year = date.getFullYear();
                return `${year}-${month}-${day}`;
            }

            // Atualiza os campos de valor e vencimento
            valueInput.value = valor;
            vencimentoInput.value = formatDateForInput(vencimentoDate);
        
            // Define o foco no campo "Referente a"
            referenceInput.focus();

        });
    }
});
