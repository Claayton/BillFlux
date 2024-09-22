from flask import Blueprint, render_template, request

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
        return f"Logged in as {email}"
    else:
        # Login falhou
        return "Invalid email or password"


@bp.route("/signup", methods=["POST"])
def signup():
    email = request.form.get("email")
    password = request.form.get("password")

    if email in users_db:
        # Usuário já existe
        return "User already exists"

    # Adiciona o novo usuário ao "banco de dados"
    users_db[email] = password
    return f"User {email} created successfully"
