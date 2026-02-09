import os
import secrets
import string
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message

app = Flask(__name__)

# ================== CONFIG BANCO (NEON) ==================
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# ================== CONFIG EMAIL (BREVO SMTP) ==================
app.config['MAIL_SERVER'] = 'smtp-relay.brevo.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.getenv("MAIL_USERNAME")
app.config['MAIL_PASSWORD'] = os.getenv("MAIL_PASSWORD")
app.config['MAIL_DEFAULT_SENDER'] = os.getenv("MAIL_DEFAULT_SENDER")

mail = Mail(app)

# ================== MODEL ==================
class Usuario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    senha = db.Column(db.String(100), nullable=False)
    data_cadastro = db.Column(db.DateTime, default=db.func.current_timestamp())

# ================== GERADOR DE SENHA ==================
def gerar_senha(tamanho=10):
    caracteres = string.ascii_letters + string.digits
    return ''.join(secrets.choice(caracteres) for _ in range(tamanho))

# ================== ENVIO DE EMAIL ==================
def enviar_email_boas_vindas(email, senha):
    try:
        msg = Message(
            subject='Bem-vindo! Seus dados de acesso',
            recipients=[email]
        )

        msg.html = f"""
        <div style="font-family:Arial;background:#f4f4f4;padding:20px">
            <div style="max-width:600px;margin:auto;background:white;padding:20px;border-radius:10px">
                <h2>🎉 Cadastro realizado!</h2>
                <p>Sua conta foi criada com sucesso.</p>
                <p><b>Email:</b> {email}</p>
                <p><b>Senha:</b></p>
                <div style="background:#eee;padding:10px;font-family:monospace">{senha}</div>
                <p style="color:red">Altere sua senha no primeiro acesso.</p>
            </div>
        </div>
        """

        mail.send(msg)
        return True

    except Exception as e:
        print("ERRO AO ENVIAR EMAIL:", e)
        return False

# ================== ROTAS ==================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/cadastrar", methods=["POST"])
def cadastrar():
    try:
        data = request.get_json()
        email = data.get("email")

        if not email:
            return jsonify({"sucesso": False, "mensagem": "Email obrigatório"})

        # Verifica se já existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            return jsonify({"sucesso": False, "mensagem": "Email já cadastrado"})

        senha = gerar_senha()

        novo_usuario = Usuario(email=email, senha=senha)
        db.session.add(novo_usuario)
        db.session.commit()

        # Enviar email
        enviado = enviar_email_boas_vindas(email, senha)

        if not enviado:
            return jsonify({
                "sucesso": True,
                "aviso": True,
                "mensagem": "Conta criada, mas houve problema ao enviar o email."
            })

        return jsonify({
            "sucesso": True,
            "mensagem": "Conta criada! Verifique seu email."
        })

    except Exception as e:
        print("ERRO NA ROTA:", e)
        return jsonify({"sucesso": False, "mensagem": "Erro no servidor"})

# ================== RUN ==================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)


