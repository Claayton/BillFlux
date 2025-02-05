// Script para exibir ou esconder a senha
document.getElementById("togglePassword").addEventListener("click", function () {
    let passwordInput = document.getElementById("password");
    if (passwordInput.type === "password") {
        passwordInput.type = "text";
        this.textContent = "🙈"; // Ícone de "olho fechado"
    } else {
        passwordInput.type = "password";
        this.textContent = "👁️"; // Ícone de "olho aberto"
    }
});



// Script para exibir modal de cadastro de usuarios
document.addEventListener('DOMContentLoaded', function () {
    const signupBtn = document.getElementById('signup');
    const modalSignup = document.getElementById('modal-signup');
    const closeModal = document.querySelector('.close');

    // Abre o modal de cadastro quando o botão de signup é clicado
    signupBtn.addEventListener('click', function () {
        modalSignup.style.display = 'block';
    });

    // Fecha o modal quando o botão de fechar (x) é clicado
    closeModal.addEventListener('click', function () {
        modalSignup.style.display = 'none';
    });

    // Fecha o modal quando o usuário clica fora do modal
    window.addEventListener('click', function (event) {
        if (event.target == modalSignup) {
            modalSignup.style.display = 'none';
        }
    });
});
