import os
import secrets
import string
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime
from sqlalchemy.pool import NullPool

app = Flask(__name__)

# ================== BANCO DE DADOS (NEON + RENDER) ==================

database_url = os.environ.get('DATABASE_URL')

if not database_url:
    raise RuntimeError("DATABASE_URL não definida no ambiente!")

# Remove aspas ou espaços que às vezes o Render adiciona sem querer
database_url = database_url.strip().replace('"', '').replace("'", "")

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'poolclass': NullPool,   # ideal para Render/serverless
    'pool_pre_ping': True,
}

# ================== EMAIL ==================

app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

db = SQLAlchemy(app)
mail = Mail(app)

# ================== MODELO ==================

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    senha = db.Column(db.String(100), nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Usuario {self.email}>'

# ================== UTILIDADES ==================

def gerar_senha(tamanho=12):
    caracteres = string.ascii_letters + string.digits + string.punctuation
    caracteres = caracteres.replace("'", "").replace('"', "").replace('\\', '')
    return ''.join(secrets.choice(caracteres) for _ in range(tamanho))


def enviar_email_boas_vindas(email, senha):
    try:
        msg = Message(
            subject='Bem-vindo! Seus dados de acesso',
            recipients=[email]
        )
        msg.html = f"""
        <html>
        <body style="font-family:Arial;background:#f4f4f4;padding:20px">
            <div style="max-width:600px;margin:auto;background:white;padding:20px;border-radius:10px">
                <h2>🎉 Cadastro Realizado!</h2>
                <p>Seu acesso foi criado com sucesso.</p>
                <p><b>Email:</b> {email}</p>
                <p><b>Senha:</b></p>
                <div style="background:#eee;padding:10px;font-family:monospace">{senha}</div>
                <p style="color:red">Recomendamos alterar sua senha no primeiro acesso.</p>
            </div>
        </body>
        </html>
        """
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {e}")
        return False

# ================== ROTAS ==================

@app.route('/')
def index():
    return render_template('index.html')


@app.route('/health')
def health():
    try:
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'ok', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()

        if not email or '@' not in email or '.' not in email:
            return jsonify({'sucesso': False, 'mensagem': 'Email inválido.'}), 400

        if Usuario.query.filter_by(email=email).first():
            return jsonify({'sucesso': False, 'mensagem': 'Email já cadastrado.'}), 400

        senha_gerada = gerar_senha()

        novo_usuario = Usuario(email=email, senha=senha_gerada)
        db.session.add(novo_usuario)
        db.session.commit()

        enviar_email_boas_vindas(email, senha_gerada)

        return jsonify({'sucesso': True, 'mensagem': 'Cadastro realizado!'}), 201

    except Exception as e:
        db.session.rollback()
        print(f"Erro no cadastro: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro no servidor.'}), 500


# ================== COMANDOS CLI ==================

@app.cli.command()
def init_db():
    with app.app_context():
        db.create_all()
        print("✅ Banco criado!")


@app.cli.command()
def test_db():
    try:
        db.session.execute(db.text('SELECT 1'))
        print("✅ Conexão OK!")
    except Exception as e:
        print(f"❌ Erro: {e}")


# ================== START ==================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
