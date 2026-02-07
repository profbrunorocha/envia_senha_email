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

print("=" * 60)
print("🚀 SISTEMA COMPLETO - VERSÃO CLOUD")
print("=" * 60)

# ============================================
# CONFIGURAÇÕES DE AMBIENTE
# ============================================

load_dotenv()  # Carrega variáveis do .env

# Configurações do Neon (PostgreSQL Cloud)
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://neondb_owner:npg_pLaUwI7O6iHC@ep-falling-tree-aiqb3bkq-pooler.c-4.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require')
# Formato: postgresql://usuario:senha@host.neon.tech/nome_banco

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
# FUNÇÕES PRINCIPAIS (mantenha suas funções atualizadas)
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

# ... mantenha as outras funções (verificar_credenciais, etc.)

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
# ROTAS (mantenha suas rotas)
# ============================================

@app.route('/')
def index():
    """Página inicial"""
    return render_template('index.html')


@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    print("\n" + "="*60)
    print("📝 ROTA /cadastrar ACESSADA!")
    print("="*60)
    
    try:
        # Log do que está chegando
        print(f"📦 Request data: {request.get_data()}")
        
        dados = request.get_json()
        if dados:
            print(f"📧 Email recebido: {dados.get('email')}")
        else:
            print("⚠️  Nenhum JSON recebido")
            
        # Resto do seu código...
        
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno.'}), 500

@app.route('/health')
def health_check():
    """Health check para Render"""
    return jsonify({
        'status': 'healthy',
        'database': 'connected' if DATABASE_URL else 'disconnected'
    })

# ... suas outras rotas aqui ...

# ============================================
# CONFIGURAÇÃO PARA PRODUÇÃO
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
        
        # No Render, use a porta fornecida pelo ambiente
        port = int(os.getenv('PORT', 5000))
        app.run(host='0.0.0.0', port=port)
    else:
        print("\n❌ Não foi possível conectar ao Neon")
        print("💡 Verifique:")
        print("   1. DATABASE_URL no .env")
        print("   2. Conexão com internet")
        print("   3. Credenciais do Neon")

