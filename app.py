import os
import secrets
import string
from flask import Flask, render_template, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from datetime import datetime
from sqlalchemy.pool import NullPool

app = Flask(__name__)

# Configurações do banco de dados Neon
# O Render automaticamente adiciona a variável DATABASE_URL
database_url = os.environ.get('DATABASE_URL')

# Neon usa postgresql:// mas algumas versões do SQLAlchemy precisam de postgresql://
if database_url and database_url.startswith('postgresql://neondb_owner:npg_pLaUwI7O6iHC@ep-falling-tree-aiqb3bkq-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'):
    database_url = database_url.replace('postgresql://neondb_owner:npg_pLaUwI7O6iHC@ep-falling-tree-aiqb3bkq-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require', 'postgresql://neondb_owner:npg_pLaUwI7O6iHC@ep-falling-tree-aiqb3bkq-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require', 1)

app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'poolclass': NullPool,  # Melhor para serverless/Render
    'pool_pre_ping': True,
    'connect_args': {
        'sslmode': 'require',  # Neon requer SSL
        'connect_timeout': 10,
    }
}

# Configurações de email
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER')

db = SQLAlchemy(app)
mail = Mail(app)

# Modelo do Usuário
class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    senha = db.Column(db.String(100), nullable=False)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f'<Usuario {self.email}>'

# Função para gerar senha aleatória
def gerar_senha(tamanho=12):
    """Gera uma senha segura aleatória"""
    caracteres = string.ascii_letters + string.digits + string.punctuation
    # Remove caracteres que podem causar confusão
    caracteres = caracteres.replace("'", "").replace('"', "").replace('\\', '')
    senha = ''.join(secrets.choice(caracteres) for _ in range(tamanho))
    return senha

# Função para enviar email
def enviar_email_boas_vindas(email, senha):
    """Envia email com as credenciais de acesso"""
    try:
        msg = Message(
            subject='Bem-vindo! Seus dados de acesso',
            recipients=[email]
        )
        msg.html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {{
                    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                }}
                .container {{
                    max-width: 600px;
                    margin: 40px auto;
                    background-color: #ffffff;
                    border-radius: 12px;
                    overflow: hidden;
                    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
                }}
                .header {{
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    color: white;
                    padding: 40px 30px;
                    text-align: center;
                }}
                .header h1 {{
                    margin: 0;
                    font-size: 28px;
                }}
                .content {{
                    padding: 40px 30px;
                }}
                .content h2 {{
                    color: #333;
                    margin-top: 0;
                }}
                .credentials {{
                    background-color: #f8f9fa;
                    border-left: 4px solid #667eea;
                    padding: 20px;
                    margin: 20px 0;
                    border-radius: 4px;
                }}
                .credentials p {{
                    margin: 10px 0;
                    font-size: 14px;
                    color: #555;
                }}
                .credentials strong {{
                    color: #333;
                    font-size: 16px;
                }}
                .password {{
                    font-family: 'Courier New', monospace;
                    background-color: #e9ecef;
                    padding: 8px 12px;
                    border-radius: 4px;
                    display: inline-block;
                    margin-top: 5px;
                    font-size: 16px;
                    color: #d63384;
                }}
                .footer {{
                    background-color: #f8f9fa;
                    padding: 20px 30px;
                    text-align: center;
                    color: #6c757d;
                    font-size: 12px;
                }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h1>🎉 Cadastro Realizado!</h1>
                </div>
                <div class="content">
                    <h2>Bem-vindo à nossa plataforma!</h2>
                    <p>Seu cadastro foi realizado com sucesso. Abaixo estão suas credenciais de acesso:</p>
                    
                    <div class="credentials">
                        <p><strong>Email:</strong> {email}</p>
                        <p><strong>Senha:</strong></p>
                        <div class="password">{senha}</div>
                    </div>
                    
                    <p style="color: #dc3545; margin-top: 20px;">
                        ⚠️ <strong>Importante:</strong> Guarde esta senha em local seguro. Por questões de segurança, 
                        recomendamos que você altere sua senha no primeiro acesso.
                    </p>
                </div>
                <div class="footer">
                    <p>Este é um email automático. Por favor, não responda.</p>
                </div>
            </div>
        </body>
        </html>
        """
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erro ao enviar email: {str(e)}")
        return False

# Rotas
@app.route('/')
def index():
    """Página inicial"""
    return render_template('index.html')

@app.route('/health')
def health():
    """Health check para o Render"""
    try:
        # Testa a conexão com o banco
        db.session.execute(db.text('SELECT 1'))
        return jsonify({'status': 'ok', 'database': 'connected'}), 200
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    """Endpoint para cadastro de usuário"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        
        # Validação básica
        if not email or '@' not in email or '.' not in email:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Por favor, insira um email válido.'
            }), 400
        
        # Verifica se o email já existe
        usuario_existente = Usuario.query.filter_by(email=email).first()
        if usuario_existente:
            return jsonify({
                'sucesso': False,
                'mensagem': 'Este email já está cadastrado.'
            }), 400
        
        # Gera senha
        senha_gerada = gerar_senha()
        
        # Cria novo usuário
        novo_usuario = Usuario(email=email, senha=senha_gerada)
        db.session.add(novo_usuario)
        db.session.commit()
        
        # Envia email
        email_enviado = enviar_email_boas_vindas(email, senha_gerada)
        
        if email_enviado:
            return jsonify({
                'sucesso': True,
                'mensagem': 'Cadastro realizado com sucesso! Verifique seu email.'
            }), 201
        else:
            # Mesmo que o email falhe, o cadastro foi feito
            return jsonify({
                'sucesso': True,
                'mensagem': 'Cadastro realizado! (Houve um problema ao enviar o email)',
                'aviso': True
            }), 201
            
    except Exception as e:
        db.session.rollback()
        print(f"Erro no cadastro: {str(e)}")
        return jsonify({
            'sucesso': False,
            'mensagem': 'Erro ao processar cadastro. Tente novamente.'
        }), 500

# Comando para criar as tabelas
@app.cli.command()
def init_db():
    """Inicializa o banco de dados"""
    with app.app_context():
        db.create_all()
        print("✅ Banco de dados criado com sucesso!")

@app.cli.command()
def test_db():
    """Testa a conexão com o banco de dados"""
    try:
        db.session.execute(db.text('SELECT 1'))
        print("✅ Conexão com o banco de dados OK!")
    except Exception as e:
        print(f"❌ Erro na conexão: {str(e)}")

if __name__ == '__main__':
    # O Render usa a variável PORT
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)


