// Script para exibir o modal do botao de cadastrar novo boleto:

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('insert-modal');
    const openModalBtn = document.getElementById('openInsertModalBtn');
    const closeModalBtn = document.querySelector('.close');

    // Abre o modal
    openModalBtn.addEventListener('click', () => {
        modal.style.display = 'block';
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