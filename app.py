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







import os

# ========= CONFIGURAÇÕES DO BANCO =========
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npq_PlaAuI7O6iHC@ep-falling-tree-aibqbkg-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslMode=require&channel_binding=require')

# ========= CONFIGURAÇÕES DO RENDERER =========
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:5000')

# ========= CONFIGURAÇÕES DA APLICAÇÃO =========
SECRET_KEY = os.getenv('SECRET_KEY', 'sistema-completo-seguro-cloud-2024')

# ========= CONFIGURAÇÕES DE E-MAIL =========
ENABLE_EMAILS = os.getenv('ENABLE_EMAILS', 'false').lower() == 'true'

# ⭐⭐ SEMPRE definir as variáveis SMTP (mesmo se não usadas) ⭐⭐
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', SMTP_USER)

# DEBUG: Mostrar status
print(f"\n🔧 CONFIGURAÇÃO DE EMAIL:")
print(f"   ENABLE_EMAILS: {ENABLE_EMAILS}")
print(f"   SMTP_HOST: {SMTP_HOST}")
print(f"   SMTP_USER: {SMTP_USER}")
print(f"   SMTP_PASS: {'✅ Definida' if SMTP_PASS else '❌ Não definida'}")

# Verificar se todas as credenciais estão presentes quando ENABLE_EMAILS=true
if ENABLE_EMAILS:
    if not all([SMTP_USER, SMTP_PASS]):
        print("⚠️ ATENÇÃO: SMTP_USER ou SMTP_PASS não configurados!")
        print("⚠️ E-mails NÃO serão enviados mesmo com ENABLE_EMAILS=true")
    else:
        print("✅ Credenciais SMTP configuradas corretamente")

# ========= FIM DAS CONFIGURAÇÕES =========






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





def enviar_email(destinatario, assunto, corpo):
    """Envia email via SMTP - VERSÃO OTIMIZADA PARA RENDER"""
    
    # 1. Verificar se emails estão ativados
    if not ENABLE_EMAILS:
        print("📧 E-mails desativados (ENABLE_EMAILS=false)")
        return False
        
    # 2. Verificar credenciais
    if not SMTP_USER or not SMTP_PASS:
        print("⚠️ Credenciais SMTP não configuradas")
        return False
    
    print(f"📤 Tentando enviar email para: {destinatario}")
    
    try:
        # 3. Importações necessárias (se não estiverem no topo)
        import ssl
        import socket
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        # 4. Timeout reduzido para Render
        socket.setdefaulttimeout(15)
        
        # 5. Criar contexto SSL
        context = ssl.create_default_context()
        
        # 6. Conexão SMTP (USE SMTP_HOST, não SMTP_SERVER)
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15)
        
        try:
            server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASS)
            
            # 7. Criar mensagem (USE 'corpo', não 'mensagem')
            msg = MIMEMultipart('alternative')
            msg['From'] = SMTP_USER
            msg['To'] = destinatario
            msg['Subject'] = assunto
            
            # Se for HTML, use 'html', se for texto simples, use 'plain'
            msg.attach(MIMEText(corpo, 'html'))
            
            # 8. Enviar
            server.send_message(msg)
            
            print("✅ Email enviado com sucesso")
            return True
            
        except socket.timeout:
            print("⚠️ Timeout ao conectar/enviar pelo SMTP")
            return False
        except smtplib.SMTPAuthenticationError as e:
            print(f"❌ Erro de autenticação: {e}")
            return False
        except Exception as e:
            print(f"⚠️ Erro SMTP: {e}")  # Mostre erro completo
            return False
        finally:
            try:
                server.quit()
            except:
                pass
                
    except Exception as e:
        print(f"⚠️ Erro geral no envio: {e}")  # Mostre erro completo
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
    """Processa cadastro de novo usuário - VERSÃO SEM EMAIL NO RENDER"""
    print("\n" + "="*60)
    print("🚀 /cadastrar INICIADA - RENDER FREE TIER")
    print("="*60)
    
    try:
        dados = request.get_json()
        email = dados.get('email', '').strip().lower()
        
        # ... validações (mantenha igual) ...
        
        # Gerar senha
        senha = gerar_senha_aleatoria()
        print(f"🔑 Senha gerada: {senha}")
        
        # Salvar no banco
        user_id = salvar_usuario(email, senha)
        
        if not user_id:
            return jsonify({'sucesso': False, 'mensagem': 'Erro ao salvar cadastro.'}), 500
        
        # NO RENDER FREE TIER: NÃO TENTA ENVIAR EMAIL
        # Apenas retorna a senha para o usuário
        mensagem_resposta = f'''
        ✅ Cadastro realizado com sucesso!
        
        📧 Email: {email}
        🔑 Senha: {senha}
        
        ⚠️ IMPORTANTE:
        - Guarde esta senha! Ela não será enviada por email.
        - Faça login em: https://envia-senha-email.onrender.com/login
        '''
        
        print("🎉 Cadastro concluído (sem email no Render)")
        return jsonify({
            'sucesso': True,
            'mensagem': mensagem_resposta,
            'senha': senha,  # Opcional: envia a senha no JSON
            'email': email
        })
        
    except Exception as e:
        print(f"❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno.'}), 500








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


@app.route('/test-email')
def test_email():
    try:
        # Seu código de envio de email aqui
        return "✅ Teste de e-mail executado - verifique logs"
    except Exception as e:
        return f"❌ Erro: {str(e)}"

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
    
    # Verificar se variáveis SMTP existem
    smtp_loaded = 'SMTP_HOST' in locals() or 'SMTP_HOST' in globals()
    
    return f"""
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🔧 Debug do Sistema</h1>
        
        <h2>Informações do Sistema</h2>
        <p><strong>Python:</strong> {sys.version}</p>
        <p><strong>Diretório:</strong> {os.getcwd()}</p>
        <p><strong>Arquivos:</strong> {', '.join(sorted(os.listdir('.')))}</p>
        
        <h2>📧 Configurações de E-mail (CRÍTICO)</h2>
        <p><strong>ENABLE_EMAILS:</strong> {'✅ TRUE' if ENABLE_EMAILS else '❌ FALSE'}</p>
        <p><strong>SMTP Carregado:</strong> {'✅ SIM' if smtp_loaded else '❌ NÃO'}</p>
        <p><strong>SMTP_USER:</strong> {'✅ ' + SMTP_USER if smtp_loaded and SMTP_USER else '❌ Não carregado'}</p>
        <p><strong>SMTP_HOST:</strong> {'✅ ' + SMTP_HOST if SMTP_HOST and SMTP_HOST != 'smtp.gmail.com' else '❌ Usando default'}</p>
        
        <h2>⚙️ Outras Configurações</h2>
        <p><strong>DATABASE_URL:</strong> {'✅ Definida' if DATABASE_URL else '❌ Não definida'}</p>
        <p><strong>RENDER_EXTERNAL_URL:</strong> {RENDER_EXTERNAL_URL}</p>
        
        <h2>🧪 Testes Específicos de E-mail</h2>
        <ul>
            <li><a href="/test-email-direct">🔗 Teste Direto de E-mail</a></li>
            <li><a href="/debug-email">📧 Página Completa de Debug</a></li>
            <li><a href="/teste-cadastro">👤 Teste de Cadastro (envia email)</a></li>
        </ul>
        
        <h2>🔍 Outros Testes</h2>
        <ul>
            <li><a href="/health">🩺 Health Check</a></li>
            <li><a href="/">🏠 Página Principal</a></li>
            <li><a href="/login">🔐 Página de Login</a></li>
        </ul>
        
        <h3>🚨 Logs Imediatos (console)</h3>
        <div style="background: #f5f5f5; padding: 10px; border-radius: 5px;">
            <i>Verifique os logs no Console do Render para mensagens de erro</i>
        </div>
    </body>
    </html>
    """





@app.route('/test-email-direct')
def test_email_direct():
    """Teste DIRETO de envio de email (sem formulário)"""
    
    print(f"\n{'='*60}")
    print("🧪 TESTE DIRETO DE E-MAIL INICIADO")
    print(f"{'='*60}")
    
    resultado = enviar_email(
        destinatario="brunorochasenacal01@gmail.com",  # Seu email
        assunto="🎯 TESTE DIRETO do Sistema",
        corpo="""
        <h2>Teste Direto de E-mail</h2>
        <p>Se você recebeu esta mensagem, o sistema de e-mails está funcionando!</p>
        <p><strong>Data:</strong> """ + datetime.now().strftime("%d/%m/%Y %H:%M:%S") + """</p>
        <p><strong>Status:</strong> ✅ Sucesso</p>
        """
    )
    
    if resultado:
        return """
        <div style="text-align: center; padding: 50px;">
            <h1 style="color: green;">✅ Teste Iniciado!</h1>
            <p>O e-mail foi enviado. Verifique:</p>
            <ol style="text-align: left; max-width: 500px; margin: 20px auto;">
                <li>Sua caixa de entrada</li>
                <li>Pasta de spam/lixo eletrônico</li>
                <li>Console do Render para logs detalhados</li>
            </ol>
            <p><a href="/debug" style="color: blue;">← Voltar ao Debug</a></p>
        </div>
        """
    else:
        return """
        <div style="text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ Falha no Teste</h1>
            <p>Verifique os logs no Console do Render para ver o erro exato.</p>
            <p><a href="/debug" style="color: blue;">← Voltar ao Debug</a></p>
        </div>
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













