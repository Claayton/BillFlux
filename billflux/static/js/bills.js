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