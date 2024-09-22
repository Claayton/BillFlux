from flask import Blueprint, render_template, request, redirect, url_for, flash

bp = Blueprint("bp_home", __name__)

# Simulação de banco de dados para armazenar usuários (em memória)
users_db = {}

@bp.route("/")
@bp.route("/home/")
@bp.route("/home")
def index():
    return render_template("home.html")

@bp.route("/login", methods=["POST"])
def login():
    email = request.form.get("email")
    password = request.form.get("password")
    
    if email in users_db and users_db[email] == password:
        # Login bem-sucedido
        flash(f"Logged in as {email}", "success")
        return redirect(url_for('bp_home.index'))
    else:
        # Login falhou
        flash("Invalid email or password", "error")
        return redirect(url_for('bp_home.index'))

@bp.route("/signup", methods=["POST"])
def signup():
    email = request.form.get("email")
    password = request.form.get("password")
    confirm_password = request.form.get("confirm_password")
    
    if email in users_db:
        # Usuário já existe
        flash("User already exists", "error")
        return redirect(url_for('bp_home.index'))
    
    if password != confirm_password:
        # Senhas não coincidem
        flash("Passwords do not match", "error")
        return redirect(url_for('bp_home.index'))
    
    # Adiciona o novo usuário ao "banco de dados"
    users_db[email] = password
    flash(f"User {email} created successfully", "success")
    return redirect(url_for('bp_home.index'))
