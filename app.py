"""
SISTEMA COMPLETO - VERSÃO CLOUD READY
Para Render + Neon + Resend
"""

import os
import random
import string
import re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import psycopg2
from psycopg2.pool import SimpleConnectionPool
from functools import wraps
from dotenv import load_dotenv
from flask_cors import CORS
from datetime import datetime

print("=" * 60)
print("🚀 SISTEMA COMPLETO - VERSÃO CLOUD")
print("=" * 60)

# ============================================
# CONFIGURAÇÕES DE AMBIENTE
# ============================================

load_dotenv()  # Carrega variáveis do .env

# Tentar importar Resend
try:
    import resend
    RESEND_AVAILABLE = True
except ImportError:
    RESEND_AVAILABLE = False
    print("⚠️ Biblioteca 'resend' não instalada")

# ========= CONFIGURAÇÕES DO BANCO =========
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npq_PlaAuI7O6iHC@ep-falling-tree-aibqbkg-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslMode=require&channel_binding=require')

# ========= CONFIGURAÇÕES DO RENDERER =========
RENDER_EXTERNAL_URL = os.getenv('RENDER_EXTERNAL_URL', 'http://localhost:5000')

# ========= CONFIGURAÇÕES DA APLICAÇÃO =========
SECRET_KEY = os.getenv('SECRET_KEY', 'sistema-completo-seguro-cloud-2024')

# ========= CONFIGURAÇÕES DE E-MAIL =========
ENABLE_EMAILS = os.getenv('ENABLE_EMAILS', 'false').lower() == 'true'
RESEND_API_KEY = os.getenv('RESEND_API_KEY')

# Configurar Resend se disponível
if RESEND_API_KEY and RESEND_AVAILABLE:
    resend.api_key = RESEND_API_KEY
    print("✅ Resend configurado")
elif ENABLE_EMAILS and not RESEND_API_KEY:
    print("⚠️ Resend não configurado")

# ⭐⭐ SEMPRE definir as variáveis SMTP (mesmo se não usadas) ⭐⭐
SMTP_HOST = os.getenv('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', SMTP_USER)

# DEBUG: Mostrar status
print(f"\n🔧 CONFIGURAÇÃO DE EMAIL:")
print(f"   ENABLE_EMAILS: {ENABLE_EMAILS}")
print(f"   RESEND_API_KEY: {'✅ Definida' if RESEND_API_KEY else '❌ Não definida'}")
print(f"   SMTP_HOST: {SMTP_HOST}")
print(f"   SMTP_USER: {SMTP_USER}")
print(f"   SMTP_PASS: {'✅ Definida' if SMTP_PASS else '❌ Não definida'}")

# Verificar se todas as credenciais estão presentes quando ENABLE_EMAILS=true
if ENABLE_EMAILS:
    if not RESEND_API_KEY and not all([SMTP_USER, SMTP_PASS]):
        print("⚠️ ATENÇÃO: Nenhum método de email configurado!")
        print("   Configure RESEND_API_KEY ou SMTP_USER/SMTP_PASS")
    elif RESEND_API_KEY:
        print("✅ Resend configurado - emails serão enviados via Resend")
    elif SMTP_USER and SMTP_PASS:
        print("✅ SMTP configurado - tentará enviar via SMTP")

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

def enviar_email_smtp(destinatario, assunto, corpo_html):
    """Função SMTP como fallback"""
    
    print(f"🔧 Tentando SMTP como fallback...")
    
    # Verificar se variáveis SMTP estão disponíveis
    if 'SMTP_HOST' not in globals() or not SMTP_HOST:
        print("❌ SMTP_HOST não configurado")
        return False
    
    if not SMTP_USER or not SMTP_PASS:
        print("❌ Credenciais SMTP incompletas")
        return False
    
    try:
        import smtplib
        import ssl
        import socket
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        print(f"🔗 Conectando a {SMTP_HOST}:{SMTP_PORT}...")
        
        # Configurar timeout
        socket.setdefaulttimeout(30)
        
        # Criar mensagem
        msg = MIMEMultipart('alternative')
        msg['From'] = SMTP_USER
        msg['To'] = destinatario
        msg['Subject'] = assunto
        msg.attach(MIMEText(corpo_html, 'html'))
        
        # Tentar conexão com STARTTLS (porta 587)
        if SMTP_PORT == 587:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
            server.starttls(context=ssl.create_default_context())
        
        # Tentar conexão com SSL (porta 465)
        elif SMTP_PORT == 465:
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, context=context, timeout=30)
        
        # Outra porta
        else:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30)
        
        # Login e envio
        server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email enviado via SMTP para {destinatario}")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Erro de autenticação SMTP: {e}")
        print("💡 Gere nova senha de app: https://myaccount.google.com/apppasswords")
        return False
        
    except (socket.timeout, smtplib.SMTPServerDisconnected) as e:
        print(f"⏰ Timeout/Desconexão SMTP: {e}")
        print("💡 O Render Free Tier pode bloquear SMTP")
        return False
        
    except Exception as e:
        print(f"⚠️ Erro SMTP: {type(e).__name__}: {e}")
        return False

def enviar_email(destinatario, assunto, corpo_html):
    """Envia email usando Resend (prioridade) ou SMTP como fallback"""
    
    if not ENABLE_EMAILS:
        print("❌ E-mails desativados (ENABLE_EMAILS=false)")
        return False
    
    print(f"\n{'='*60}")
    print(f"📧 INICIANDO ENVIO PARA: {destinatario}")
    print(f"📝 ASSUNTO: {assunto}")
    print(f"{'='*60}")
    
    # MÉTODO 1: Usar Resend (recomendado para Render)
    if RESEND_API_KEY and RESEND_AVAILABLE:
        try:
            print("🔧 Usando Resend API...")
            
            params = {
                "from": "Sistema de Cadastro <onboarding@resend.dev>",
                "to": destinatario,
                "subject": assunto,
                "html": corpo_html,
                "headers": {
                    "X-Application": "Sistema-Cadastro",
                    "X-User-Email": destinatario
                }
            }
            
            # Enviar email via Resend
            response = resend.Emails.send(params)
            
            print(f"✅ Email enviado via Resend!")
            print(f"   ID: {response.get('id', 'N/A')}")
            print(f"   De: {params['from']}")
            print(f"   Para: {destinatario}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro no Resend: {type(e).__name__}: {str(e)[:100]}")
            print("🔄 Tentando SMTP como fallback...")
            
            # Tenta SMTP como fallback
            return enviar_email_smtp(destinatario, assunto, corpo_html)
    
    # MÉTODO 2: SMTP tradicional (se Resend não disponível)
    elif 'SMTP_USER' in globals() and SMTP_USER and SMTP_PASS:
        print("🔧 Resend não disponível, usando SMTP...")
        return enviar_email_smtp(destinatario, assunto, corpo_html)
    
    # NENHUM MÉTODO DISPONÍVEL
    else:
        print("❌ Nenhum método de email configurado")
        print("💡 Configure:")
        print("   1. RESEND_API_KEY (recomendado para Render)")
        print("   OU")
        print("   2. SMTP_USER e SMTP_PASS")
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

def salvar_usuario(nome, email, senha):
    """Salva novo usuário - Cloud"""
    conn = get_connection()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        cursor.execute(
            """INSERT INTO usuarios (nome, email, senha, criado_em) 
               VALUES (%s, %s, %s, NOW()) RETURNING id""",
            (nome, email.lower(), senha)
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
            "SELECT id, email, nome FROM usuarios WHERE email = %s AND senha = %s",
            (email.lower(), senha)
        )
        usuario = cursor.fetchone()
        
        cursor.close()
        return_connection(conn)
        
        if usuario:
            print(f"✅ Login válido para: {email}")
            return {'id': usuario[0], 'email': usuario[1], 'nome': usuario[2]}
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
    """Página inicial completa"""
    return f'''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Sistema de Cadastro</title>
        <style>
            body {{ font-family: Arial, sans-serif; padding: 20px; max-width: 600px; margin: 0 auto; line-height: 1.6; }}
            h1 {{ color: #333; }}
            .menu {{ margin: 30px 0; }}
            .btn {{ display: inline-block; padding: 12px 24px; margin: 8px; background: #007bff; color: white; 
                    text-decoration: none; border-radius: 5px; font-weight: bold; }}
            .btn:hover {{ background: #0056b3; }}
            .info-box {{ background: #f8f9fa; padding: 20px; border-radius: 8px; margin-top: 30px; border-left: 4px solid #007bff; }}
        </style>
    </head>
    <body>
        <h1>🚀 Sistema de Cadastro Cloud</h1>
        <p>Sistema completo com cadastro, login e envio de emails.</p>
        
        <div class="menu">
            <h2>📋 Menu Principal</h2>
            <a class="btn" href="/cadastro-simples">📝 Cadastro Simples</a>
            <a class="btn" href="/login">🔐 Login</a>
            <a class="btn" href="/debug">🔧 Debug</a>
        </div>
        
        <div class="menu">
            <h2>🧪 Testes Rápidos</h2>
            <a class="btn" href="/test-email-resend" style="background: #28a745;">📧 Teste Resend</a>
            <a class="btn" href="/health" style="background: #6c757d;">🩺 Health Check</a>
        </div>
        
        <div class="info-box">
            <h3>ℹ️ Informações do Sistema</h3>
            <p><strong>URL:</strong> {RENDER_EXTERNAL_URL}</p>
            <p><strong>Status:</strong> <span style="color: green;">✅ Online</span></p>
            <p><strong>Tecnologias:</strong> Render + Neon + Resend</p>
        </div>
    </body>
    </html>
    '''
















@app.route('/cadastro-simples', methods=['GET', 'POST'])
def cadastro_simples():
    """Rota SIMPLES de cadastro que sempre funciona"""
    
    if request.method == 'GET':
        return '''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cadastro Simples</title>
            <style>
                body { font-family: Arial; padding: 20px; max-width: 500px; margin: 0 auto; }
                input, button { width: 100%; padding: 12px; margin: 10px 0; box-sizing: border-box; }
                input { border: 1px solid #ddd; border-radius: 5px; }
                button { background: #28a745; color: white; border: none; border-radius: 5px; cursor: pointer; font-size: 16px; }
                button:hover { background: #218838; }
                .success { color: green; padding: 10px; background: #d4edda; border-radius: 5px; }
                .error { color: red; padding: 10px; background: #f8d7da; border-radius: 5px; }
            </style>
        </head>
        <body>
            <h1>📝 Cadastro Simples</h1>
            <p>Formulário direto que sempre funciona:</p>
            
            <form method="POST">
                <input type="text" name="nome" placeholder="Seu nome completo" required>
                <input type="email" name="email" placeholder="Seu email" required>
                <button type="submit">✅ Cadastrar Agora</button>
            </form>
            
            <p style="margin-top: 20px;">
                <a href="/">🏠 Voltar ao início</a> | 
                <a href="/debug">🔧 Debug</a>
            </p>
        </body>
        </html>
        '''
    
    # POST - Processar cadastro
    nome = request.form.get('nome', '').strip()
    email = request.form.get('email', '').strip().lower()
    
    print(f"\n{'='*60}")
    print(f"🚀 CADASTRO SIMPLES INICIADO")
    print(f"{'='*60}")
    print(f"📝 Dados: {nome} - {email}")
    
    # Validar dados
    if not nome or not email:
        return '''
        <div style="text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ Erro</h1>
            <p>Nome e email são obrigatórios.</p>
            <p><a href="/cadastro-simples">← Tentar novamente</a></p>
        </div>
        ''', 400
    
    if not validar_email(email):
        return f'''
        <div style="text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ Email Inválido</h1>
            <p>O email "{email}" não é válido.</p>
            <p><a href="/cadastro-simples">← Tentar novamente</a></p>
        </div>
        ''', 400
    
    # Verificar se email já existe
    if email_existe(email):
        return f'''
        <div style="text-align: center; padding: 50px;">
            <h1 style="color: orange;">⚠️ Email já cadastrado</h1>
            <p>O email "{email}" já está cadastrado no sistema.</p>
            <p><a href="/login">🔐 Fazer login</a> ou <a href="/cadastro-simples">📝 Usar outro email</a></p>
        </div>
        ''', 400
    
    # Gerar senha aleatória
    senha_gerada = gerar_senha_aleatoria(12)
    
    print(f"🔑 Senha gerada: {senha_gerada}")
    
    try:
        # 1. INSERIR NO BANCO (NeonDB)
        usuario_id = salvar_usuario(nome, email, senha_gerada)
        
        if not usuario_id:
            return '''
            <div style="text-align: center; padding: 50px;">
                <h1 style="color: red;">❌ Erro no Banco</h1>
                <p>Não foi possível salvar no banco de dados.</p>
                <p><a href="/cadastro-simples">← Tentar novamente</a></p>
            </div>
            ''', 500
        
        print(f"✅ Cadastro inserido no banco. ID: {usuario_id}")
        
        # 2. ENVIAR EMAIL (com Resend ou SMTP)
        email_enviado = False
        if ENABLE_EMAILS:
            print(f"📧 Enviando email para: {email}")
            
            sucesso = enviar_email(
                destinatario=email,
                assunto=f"🎉 Cadastro Realizado - {nome}",
                corpo_html=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <style>
                        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
                        .header {{ background: #007bff; color: white; padding: 20px; text-align: center; border-radius: 10px 10px 0 0; }}
                        .content {{ padding: 30px; background: #f9f9f9; border-radius: 0 0 10px 10px; }}
                        .senha {{ font-family: monospace; font-size: 20px; background: #eee; padding: 10px; border-radius: 5px; margin: 10px 0; }}
                        .warning {{ background: #fff3cd; padding: 15px; border-radius: 5px; border-left: 4px solid #ffc107; margin: 20px 0; }}
                    </style>
                </head>
                <body>
                    <div class="header">
                        <h1>🎉 Cadastro Realizado com Sucesso!</h1>
                    </div>
                    <div class="content">
                        <h2>Olá, {nome}!</h2>
                        <p>Seu cadastro foi realizado com sucesso em nosso sistema.</p>
                        
                        <h3>📋 Seus Dados de Acesso:</h3>
                        <p><strong>Email:</strong> {email}</p>
                        <p><strong>Senha:</strong> <span class="senha">{senha_gerada}</span></p>
                        
                        <p><strong>🔗 Acesse o sistema:</strong> <a href="{RENDER_EXTERNAL_URL}/login">{RENDER_EXTERNAL_URL}/login</a></p>
                        
                        <div class="warning">
                            <p>⚠️ <strong>Importante:</strong> Guarde esta senha com segurança.</p>
                            <p>Recomendamos alterá-la após o primeiro acesso.</p>
                        </div>
                        
                        <p style="margin-top: 30px; font-size: 12px; color: #666;">
                            ID do cadastro: {usuario_id} | Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}
                        </p>
                    </div>
                </body>
                </html>
                """
            )
            
            if sucesso:
                email_enviado = True
                print("✅ Email de confirmação enviado com sucesso!")
            else:
                print("⚠️ Falha no envio do email")
        else:
            print("⚠️ ENABLE_EMAILS=false - Email não enviado")
        
        # 3. RETORNAR RESPOSTA HTML
        return f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Cadastro Concluído</title>
            <style>
                body {{ font-family: Arial; max-width: 600px; margin: 0 auto; padding: 20px; }}
                .success-box {{ background: #d4edda; color: #155724; padding: 30px; border-radius: 10px; margin: 20px 0; text-align: center; }}
                .info-box {{ background: #e7f3ff; padding: 25px; border-radius: 10px; margin: 20px 0; }}
                .senha {{ font-family: monospace; font-size: 24px; font-weight: bold; color: #dc3545; background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 10px 0; }}
                .btn {{ display: inline-block; padding: 12px 25px; margin: 10px; text-decoration: none; border-radius: 5px; font-weight: bold; }}
                .btn-primary {{ background: #28a745; color: white; }}
                .btn-secondary {{ background: #6c757d; color: white; }}
                .email-status {{ padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .email-success {{ background: #d4edda; color: #155724; }}
                .email-warning {{ background: #fff3cd; color: #856404; }}
            </style>
        </head>
        <body>
            <div class="success-box">
                <h1 style="margin: 0;">✅ Cadastro Concluído!</h1>
                <p style="font-size: 18px;">Parabéns, <strong>{nome}</strong>!</p>
            </div>
            
            <div class="info-box">
                <h2>📋 Seus Dados de Acesso:</h2>
                <p><strong>ID do usuário:</strong> {usuario_id}</p>
                <p><strong>Email cadastrado:</strong> {email}</p>
                <p><strong>Sua senha:</strong></p>
                <div class="senha">{senha_gerada}</div>
                <p style="color: #666; font-size: 14px;">⚠️ Anote esta senha! Ela não será mostrada novamente.</p>
            </div>
            
            <div class="email-status {'email-success' if email_enviado else 'email-warning'}">
                <h3>📧 Status do Email:</h3>
                <p>{"✅ Email de confirmação enviado com sucesso!" if email_enviado else "⚠️ Cadastro realizado, mas email não enviado. Verifique a senha acima."}</p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="/login" class="btn btn-primary">🔐 Fazer Login</a>
                <a href="/" class="btn btn-secondary">🏠 Voltar ao Início</a>
            </div>
            
            <p style="margin-top: 30px; font-size: 12px; color: #666; text-align: center;">
                ID: {usuario_id} | {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
            </p>
        </body>
        </html>
        '''
        
    except Exception as e:
        print(f"❌ Erro no cadastro: {e}")
        import traceback
        traceback.print_exc()
        
        return f'''
        <div style="text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ Erro no Cadastro</h1>
            <p>{str(e)}</p>
            <p><a href="/cadastro-simples">← Tentar novamente</a></p>
        </div>
        ''', 500

















        

@app.route('/cadastrar', methods=['GET', 'POST'])
def cadastrar():
    """Rota de cadastro original (mantida para compatibilidade)"""
    return redirect('/cadastro-simples')

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
            session['usuario_nome'] = usuario.get('nome', '')
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
                         nome=session.get('usuario_nome', ''),
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
            if ENABLE_EMAILS:
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
                except Exception as e:
                    print(f"⚠️ Não foi possível enviar email de confirmação: {e}")
            
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



# ... (todo o código anterior permanece igual até a linha ~840)

# ============================================
# ROTAS DE TESTE E DIAGNÓSTICO
# ============================================

@app.route('/test-email')
def test_email():
    """Teste básico de email"""
    try:
        return "✅ Teste de e-mail executado - verifique logs"
    except Exception as e:
        return f"❌ Erro: {str(e)}"

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
        <p><strong>RESEND_API_KEY:</strong> {'✅ Definida' if RESEND_API_KEY else '❌ Não definida'}</p>
        <p><strong>SMTP Carregado:</strong> {'✅ SIM' if smtp_loaded else '❌ NÃO'}</p>
        <p><strong>SMTP_USER:</strong> {'✅ ' + SMTP_USER if smtp_loaded and SMTP_USER else '❌ Não carregado'}</p>
        <p><strong>SMTP_HOST:</strong> {'✅ ' + SMTP_HOST if SMTP_HOST and SMTP_HOST != 'smtp.gmail.com' else '❌ Usando default'}</p>
        
        <h2>⚙️ Outras Configurações</h2>
        <p><strong>DATABASE_URL:</strong> {'✅ Definida' if DATABASE_URL else '❌ Não definida'}</p>
        <p><strong>RENDER_EXTERNAL_URL:</strong> {RENDER_EXTERNAL_URL}</p>
        
        <h2>🧪 Testes Específicos de E-mail</h2>
        <ul>
            <li><a href="/test-email-resend">🎯 Teste Resend</a></li>
            <li><a href="/test-email-direct">📧 Teste Direto</a></li>
            <li><a href="/cadastro-simples">👤 Cadastro Simples</a></li>
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
        corpo_html=f"""
        <h2>Teste Direto de E-mail</h2>
        <p>Se você recebeu esta mensagem, o sistema de e-mails está funcionando!</p>
        <p><strong>Data:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>
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

@app.route('/test-email-resend')
def test_email_resend():
    """Teste específico do Resend"""
    
    if not RESEND_API_KEY:
        return '''
        <div style="text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ RESEND_API_KEY não configurada</h1>
            <p>Configure a variável RESEND_API_KEY no Render Dashboard</p>
            <p><a href="/debug">🔧 Ver configurações</a></p>
        </div>
        '''
    
    try:
        # Teste DIRETO com Resend
        params = {
            "from": "Teste <onboarding@resend.dev>",
            "to": "brunorochasenacal01@gmail.com",
            "subject": "✅ Teste Resend - Sistema Funcionando",
            "html": f"""
            <h1>🎉 Teste Bem-Sucedido!</h1>
            <p>Se você está lendo esta mensagem, o <strong>Resend está integrado</strong> no seu sistema!</p>
            <p><strong>Data:</strong> {datetime.now().strftime("%d/%m/%Y %H:%M:%S")}</p>
            <p><strong>Aplicação:</strong> Sistema de Cadastro</p>
            <hr>
            <p><small>Email enviado via Resend API</small></p>
            """
        }
        
        response = resend.Emails.send(params)
        
        return f"""
        <div style="text-align: center; padding: 50px;">
            <h1 style="color: green;">✅ Teste Resend Enviado!</h1>
            <p>ID do email: <code>{response['id']}</code></p>
            <p>Verifique sua caixa de entrada em alguns segundos.</p>
            <p><a href="/debug" style="color: blue;">← Voltar ao Debug</a></p>
        </div>
        """
        
    except Exception as e:
        return f"""
        <div style="text-align: center; padding: 50px;">
            <h1 style="color: red;">❌ Erro no Resend</h1>
            <p>{str(e)}</p>
            <p><a href="/debug" style="color: blue;">← Voltar ao Debug</a></p>
        </div>
        """

# ============================================
# FUNÇÃO DE TESTE DE CONEXÃO SMTP
# ============================================

def testar_conexao_smtp():
    """Testa conexão básica com SMTP"""
    try:
        import socket
        print(f"\n🔍 TESTANDO CONEXÃO COM {SMTP_HOST}:{SMTP_PORT}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        resultado = sock.connect_ex((SMTP_HOST, SMTP_PORT))
        sock.close()
        
        if resultado == 0:
            print(f"✅ Porta {SMTP_PORT} aberta em {SMTP_HOST}")
            return True
        else:
            print(f"❌ Não foi possível conectar a {SMTP_HOST}:{SMTP_PORT}")
            print(f"💡 O Render Free Tier pode bloquear conexões SMTP")
            return False
    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        return False

# Executar teste se ENABLE_EMAILS for True
if ENABLE_EMAILS and SMTP_HOST and SMTP_PORT:
    testar_conexao_smtp()

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

