"""
SISTEMA COMPLETO - VERSÃO CLOUD READY
Para Render + Neon
"""

import os
import random
import string
import re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import psycopg2
from psycopg2.pool import SimpleConnectionPool
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl
from functools import wraps
from dotenv import load_dotenv
from flask_cors import CORS  

print("=" * 60)
print("🚀 SISTEMA COMPLETO - VERSÃO CLOUD")
print("=" * 60)

# ============================================
# CONFIGURAÇÕES DE AMBIENTE
# ============================================

load_dotenv()  # Carrega variáveis do .env

# Configurações do Neon (PostgreSQL Cloud)
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_pLaUwI7O6iHC@ep-falling-tree-aiqb3bkq-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')

# Configurações do Render
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:5000')

# Configurações SMTP (Gmail)
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER', '')
SMTP_PASS = os.getenv('SMTP_PASS', '')

# Configurações da aplicação
SECRET_KEY = os.getenv('SECRET_KEY', 'sistema-completo-seguro-cloud-2024')

# ============================================
# INICIALIZAÇÃO FLASK
# ============================================

app = Flask(__name__)
CORS(app)

app.secret_key = SECRET_KEY
app.config['PERMANENT_SESSION_LIFETIME'] = 1800  # 30 minutos
app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Pool de conexões para melhor performance
connection_pool = None

def init_connection_pool():
    """Inicializa pool de conexões com Neon"""
    global connection_pool
    if DATABASE_URL:
        try:
            connection_pool = SimpleConnectionPool(
                1, 20, DATABASE_URL, sslmode='require'
            )
            print("✅ Pool de conexões inicializado com Neon")
            return True
        except Exception as e:
            print(f"❌ Erro ao criar pool: {e}")
    return False

def get_connection():
    """Obtém conexão do pool"""
    if connection_pool:
        return connection_pool.getconn()
    else:
        # Fallback para conexão direta
        try:
            conn = psycopg2.connect(DATABASE_URL, sslmode='require')
            return conn
        except Exception as e:
            print(f"❌ Erro conexão direta: {e}")
            return None

def return_connection(conn):
    """Retorna conexão ao pool"""
    if connection_pool:
        connection_pool.putconn(conn)
    else:
        conn.close()

# ============================================
# FUNÇÕES DO BANCO DE DADOS - CLOUD
# ============================================

def verificar_conexao_neon():
    """Verifica conexão com Neon"""
    print("\n🔍 VERIFICANDO CONEXÃO COM NEON...")
    
    conn = get_connection()
    if not conn:
        print("❌ Não conectou ao Neon")
        print(f"   DATABASE_URL: {DATABASE_URL[:50]}..." if DATABASE_URL else "   DATABASE_URL não definida")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Verificar versão do PostgreSQL
        cursor.execute("SELECT version()")
        version = cursor.fetchone()[0]
        print(f"✅ Conectado ao PostgreSQL: {version.split(',')[0]}")
        
        # Verificar se tabelas existem
        cursor.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_name IN ('usuarios', 'historico_senhas')
        """)
        tabelas = cursor.fetchall()
        
        if tabelas:
            print(f"✅ Tabelas encontradas: {[t[0] for t in tabelas]}")
        else:
            print("⚠️  Tabelas não encontradas. Execute criar_tabelas.sql no Neon")
        
        cursor.close()
        return_connection(conn)
        return True
        
    except Exception as e:
        print(f"❌ Erro na verificação: {e}")
        return_connection(conn)
        return False

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def validar_email(email):
    """Valida formato do email"""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

def gerar_senha_aleatoria(tamanho=12):
    """Gera senha aleatória"""
    caracteres = string.ascii_letters + string.digits + "!@#$%&*"
    senha = ''.join(random.choice(caracteres) for _ in range(tamanho))
    return senha

def enviar_email(destinatario, assunto, mensagem):
    """Envia email via SMTP"""
    try:
        print(f"📤 Enviando email para: {destinatario}")
        
        # Se não tem credenciais SMTP, apenas simula
        if not SMTP_USER or not SMTP_PASS:
            print("⚠️ Credenciais SMTP não configuradas - simulando envio")
            return True
        
        context = ssl.create_default_context()
        
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            
            msg = MIMEMultipart('alternative')
            msg['From'] = SMTP_USER
            msg['To'] = destinatario
            msg['Subject'] = assunto
            
            msg.attach(MIMEText(mensagem, 'html'))
            server.send_message(msg)
            
            print(f"✅ Email enviado com sucesso!")
            return True
            
    except Exception as e:
        print(f"❌ Erro ao enviar email: {e}")
        return False

# ============================================
# FUNÇÕES DE BANCO DE DADOS
# ============================================

def email_existe(email):
    """Verifica se email já está cadastrado - Cloud"""
    email = email.strip().lower()
    
    conn = get_connection()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s)", (email,))
        resultado = cursor.fetchone()
        cursor.close()
        return_connection(conn)
        
        return resultado is not None
    except Exception as e:
        print(f"❌ Erro email_existe: {e}")
        return_connection(conn)
        return False

def salvar_usuario(email, senha):
    """Salva novo usuário - Cloud"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO usuarios (email, senha) 
               VALUES (%s, %s) RETURNING id""",
            (email.lower(), senha)
        )
        
        resultado = cursor.fetchone()
        if resultado:
            user_id = resultado[0]
            conn.commit()
            cursor.close()
            return_connection(conn)
            return user_id
        else:
            conn.rollback()
            cursor.close()
            return_connection(conn)
            return None
            
    except Exception as e:
        print(f"❌ Erro salvar_usuario: {e}")
        conn.rollback()
        cursor.close()
        return_connection(conn)
        return None

def verificar_credenciais(email, senha):
    """Verifica se email e senha estão corretos"""
    print(f"🔐 Verificando credenciais para: {email}")
    
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, email FROM usuarios WHERE email = %s AND senha = %s",
            (email.lower(), senha)
        )
        usuario = cursor.fetchone()
        
        cursor.close()
        return_connection(conn)
        
        if usuario:
            print(f"✅ Login válido para: {email}")
            return {'id': usuario[0], 'email': usuario[1]}
        else:
            print(f"❌ Credenciais inválidas para: {email}")
            return None
            
    except Exception as e:
        print(f"❌ Erro em verificar_credenciais: {e}")
        return_connection(conn)
        return None

# ============================================
# MIDDLEWARE PARA LOGIN
# ============================================

def login_required(f):
    """Decorator para exigir login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect('/login')
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# MIDDLEWARE PARA HTTPS NO RENDER
# ============================================

@app.before_request
def before_request():
    """Força HTTPS no Render"""
    if request.url.startswith('http://'):
        url = request.url.replace('http://', 'https://', 1)
        return redirect(url, code=301)

# ============================================
# ROTAS PÚBLICAS
# ============================================

@app.route('/')
def index():
    """Página inicial"""
    return render_template('index.html')

@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    """Processa cadastro de novo usuário - VERSÃO COM LOGS DETALHADOS"""
    print("\n" + "="*60)
    print("🚀 /cadastrar INICIADA")
    print("="*60)
    
    try:
        dados = request.get_json()
        print(f"📦 Dados brutos recebidos: {dados}")
        
        email = dados.get('email', '').strip().lower() if dados else ''
        print(f"📧 Email extraído: '{email}'")
        
        # Validações
        if not email:
            print("❌ Email vazio")
            return jsonify({'sucesso': False, 'mensagem': 'Informe um email.'}), 400
        
        if not validar_email(email):
            print("❌ Email inválido")
            return jsonify({'sucesso': False, 'mensagem': 'Email inválido.'}), 400
        
        if email_existe(email):
            print(f"❌ Email '{email}' já cadastrado")
            return jsonify({'sucesso': False, 'mensagem': 'Email já cadastrado.'}), 400
        
        print("✅ Email validado e disponível")
        
        # Gerar senha
        senha = gerar_senha_aleatoria()
        print(f"🔑 Senha gerada: {senha}")
        
        # Salvar no banco
        user_id = salvar_usuario(email, senha)
        print(f"📊 Resultado salvar_usuario: user_id={user_id}")
        
        if not user_id:
            print("❌ Falha ao salvar usuário no banco")
            return jsonify({'sucesso': False, 'mensagem': 'Erro ao salvar cadastro.'}), 500
        
        print(f"✅ Usuário salvo com ID: {user_id}")
        
        # Enviar email
        try:
            assunto = "✅ Cadastro Realizado - Sistema"
            mensagem_email = f"""
            <html><body>
            <h2>Cadastro Realizado com Sucesso!</h2>
            <p><strong>Email:</strong> {email}</p>
            <p><strong>Senha:</strong> <strong>{senha}</strong></p>
            <p>Acesse o sistema: https://envia-senha-email.onrender.com/login</p>
            <p><small>Guarde estas informações em local seguro.</small></p>
            </body></html>
            """
            
            if enviar_email(email, assunto, mensagem_email):
                print("✅ Email enviado com sucesso")
                mensagem_resposta = f'Cadastro realizado! Email com senha enviado para {email}'
            else:
                print("⚠️ Email não enviado (erro SMTP)")
                mensagem_resposta = f'Cadastro realizado! Sua senha é: {senha} (Guarde esta senha!)'
                
        except Exception as email_error:
            print(f"⚠️ Erro no envio de email: {email_error}")
            mensagem_resposta = f'Cadastro realizado! Sua senha é: {senha} (Guarde esta senha!)'
        
        print("🎉 Cadastro concluído com sucesso!")
        return jsonify({
            'sucesso': True,
            'mensagem': mensagem_resposta
        })
        
    except Exception as e:
        print(f"\n❌❌❌ ERRO CRÍTICO em /cadastrar ❌❌❌")
        print(f"Tipo: {type(e).__name__}")
        print(f"Mensagem: {str(e)}")
        import traceback
        traceback.print_exc()
        print("="*60)
        
        return jsonify({
            'sucesso': False, 
            'mensagem': 'Erro interno do servidor.'
        }), 500

@app.route('/login')
def login():
    """Página de login"""
    if 'usuario_id' in session:
        return redirect('/sistema')
    return render_template('login.html')

@app.route('/logar', methods=['POST'])
def logar():
    """Processa login"""
    try:
        dados = request.get_json()
        email = dados.get('email', '').strip().lower()
        senha = dados.get('senha', '')
        
        print(f"🔐 Tentativa de login para: {email}")
        
        if not email or not senha:
            return jsonify({'sucesso': False, 'mensagem': 'Preencha todos os campos.'}), 400
        
        usuario = verificar_credenciais(email, senha)
        
        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_email'] = usuario['email']
            session.permanent = True
            
            print(f"✅ Login bem-sucedido para usuário ID: {usuario['id']}")
            
            return jsonify({
                'sucesso': True,
                'mensagem': 'Login realizado com sucesso!',
                'redirect': '/sistema'
            })
        else:
            print(f"❌ Login falhou para: {email}")
            return jsonify({'sucesso': False, 'mensagem': 'Email ou senha incorretos.'}), 401
            
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno.'}), 500

# ============================================
# ROTAS PROTEGIDAS (requerem login)
# ============================================

@app.route('/sistema')
@login_required
def sistema():
    """Página após login"""
    return render_template('sistema.html', 
                         email=session.get('usuario_email', ''),
                         usuario_id=session.get('usuario_id', ''))

@app.route('/trocar-senha')
@login_required
def trocar_senha():
    """Página para trocar senha"""
    return render_template('trocar_senha.html', 
                         email=session.get('usuario_email', ''))

@app.route('/atualizar-senha', methods=['POST'])
@login_required
def atualizar_senha():
    """Processa troca de senha"""
    try:
        dados = request.get_json()
        nova_senha = dados.get('nova_senha', '')
        confirmar_senha = dados.get('confirmar_senha', '')
        
        if not nova_senha or not confirmar_senha:
            return jsonify({'sucesso': False, 'mensagem': 'Preencha todos os campos.'}), 400
        
        if nova_senha != confirmar_senha:
            return jsonify({'sucesso': False, 'mensagem': 'As senhas não coincidem.'}), 400
        
        if len(nova_senha) < 6:
            return jsonify({'sucesso': False, 'mensagem': 'Senha deve ter pelo menos 6 caracteres.'}), 400
        
        # Atualiza senha no banco
        conn = get_connection()
        if not conn:
            return jsonify({'sucesso': False, 'mensagem': 'Erro de conexão com banco.'}), 500
        
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE usuarios SET senha = %s WHERE id = %s",
                (nova_senha, session['usuario_id'])
            )
            conn.commit()
            cursor.close()
            return_connection(conn)
            
            # Envia email de confirmação
            try:
                assunto = "🔒 Sua senha foi alterada"
                mensagem = f"""
                <html><body>
                <h2>Senha Alterada com Sucesso!</h2>
                <p>Sua senha de acesso ao sistema foi alterada.</p>
                <p><strong>Nova senha:</strong> {nova_senha}</p>
                </body></html>
                """
                enviar_email(session['usuario_email'], assunto, mensagem)
            except:
                pass  # Não falha se não enviar email
            
            return jsonify({
                'sucesso': True,
                'mensagem': 'Senha alterada com sucesso!'
            })
            
        except Exception as e:
            print(f"❌ Erro ao atualizar senha: {e}")
            return_connection(conn)
            return jsonify({'sucesso': False, 'mensagem': 'Erro ao atualizar senha.'}), 500
            
    except Exception as e:
        print(f"❌ Erro geral em atualizar-senha: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno.'}), 500

@app.route('/logout')
def logout():
    """Logout"""
    session.clear()
    return redirect('/')

# ============================================
# ROTAS DE DIAGNÓSTICO E TESTE
# ============================================

@app.route('/health')
def health_check():
    """Health check para Render"""
    conn = get_connection()
    db_status = 'connected' if conn else 'disconnected'
    if conn:
        return_connection(conn)
    
    return jsonify({
        'status': 'healthy',
        'database': db_status,
        'service': 'envia-senha-email',
        'timestamp': 'online'
    })

@app.route('/teste-cadastro')
def teste_cadastro():
    """Página de teste do cadastro"""
    return '''
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🧪 Teste de Cadastro</h1>
        
        <h2>Teste 1: Form HTML tradicional</h2>
        <form id="form1">
            <input type="email" name="email" placeholder="Email" required>
            <button type="submit">Enviar (Form Data)</button>
        </form>
        
        <h2>Teste 2: Fetch JSON</h2>
        <button onclick="testeJSON()">Testar com JSON (teste@teste.com)</button>
        
        <h2>Teste 3: Email customizado</h2>
        <input type="email" id="emailCustom" placeholder="Digite um email">
        <button onclick="testeCustom()">Testar este email</button>
        
        <div id="resultado" style="margin-top: 20px; padding: 15px; background: #f5f5f5; border-radius: 5px;"></div>
        
        <script>
            // Teste 1: Form tradicional
            document.getElementById('form1').addEventListener('submit', async function(e) {
                e.preventDefault();
                const formData = new FormData(this);
                
                const response = await fetch('/cadastrar', {
                    method: 'POST',
                    body: formData
                });
                
                const result = await response.json();
                document.getElementById('resultado').innerHTML = 
                    `<h3>Resultado:</h3><pre>${JSON.stringify(result, null, 2)}</pre>`;
            });
            
            // Teste 2: Fetch JSON
            async function testeJSON() {
                const response = await fetch('/cadastrar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email: 'teste@teste.com'})
                });
                
                const result = await response.json();
                document.getElementById('resultado').innerHTML = 
                    `<h3>Resultado:</h3><pre>${JSON.stringify(result, null, 2)}</pre>`;
            }
            
            // Teste 3: Email customizado
            async function testeCustom() {
                const email = document.getElementById('emailCustom').value;
                if (!email) {
                    alert('Digite um email');
                    return;
                }
                
                const response = await fetch('/cadastrar', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({email: email})
                });
                
                const result = await response.json();
                document.getElementById('resultado').innerHTML = 
                    `<h3>Resultado para ${email}:</h3><pre>${JSON.stringify(result, null, 2)}</pre>`;
            }
        </script>
    </body>
    </html>
    '''

@app.route('/debug')
def debug():
    """Página de debug"""
    import sys, os
    return f"""
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🔧 Debug do Sistema</h1>
        
        <h2>Informações do Sistema</h2>
        <p><strong>Python:</strong> {sys.version}</p>
        <p><strong>Diretório:</strong> {os.getcwd()}</p>
        <p><strong>Arquivos:</strong> {', '.join(os.listdir('.'))}</p>
        
        <h2>Configurações</h2>
        <p><strong>DATABASE_URL:</strong> {'✅ Definida' if DATABASE_URL else '❌ Não definida'}</p>
        <p><strong>SMTP_USER:</strong> {'✅ Definida' if SMTP_USER else '❌ Não definida'}</p>
        <p><strong>RENDER_EXTERNAL_URL:</strong> {RENDER_EXTERNAL_URL}</p>
        
        <h2>Testes</h2>
        <ul>
            <li><a href="/health">Health Check</a></li>
            <li><a href="/teste-cadastro">Teste de Cadastro</a></li>
            <li><a href="/">Página Principal</a></li>
            <li><a href="/login">Página de Login</a></li>
        </ul>
    </body>
    </html>
    """

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == '__main__':
    # Inicializar pool de conexões
    init_connection_pool()
    
    # Verificar conexão com Neon
    if verificar_conexao_neon():
        print("\n" + "="*60)
        print("✅ SISTEMA PRONTO PARA CLOUD")
        print("="*60)
        print(f"🌐 URL: {RENDER_EXTERNAL_URL}")
        print(f"🔗 Health Check: {RENDER_EXTERNAL_URL}/health")
        print(f"🔧 Debug: {RENDER_EXTERNAL_URL}/debug")
        
        # No Render, use a porta fornecida pelo ambiente
        port = int(os.getenv('PORT', 5000))
        app.run(host='0.0.0.0', port=port, debug=False)
    else:
        print("\n❌ Não foi possível conectar ao Neon")
        print("💡 Verifique:")
        print("   1. DATABASE_URL no .env ou variáveis de ambiente")
        print("   2. Tabelas foram criadas? (execute criar_tabelas.sql no Neon)")
        print("   3. Internet está funcionando")





