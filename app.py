"""
SISTEMA COMPLETO REFATORADO - SEM BUGS
Versão corrigida do problema "Email já cadastrado"
"""

import os
import random
import string
import re
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import psycopg2
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import ssl

print("=" * 60)
print("SISTEMA COMPLETO REFATORADO - VERSÃO CORRIGIDA")
print("=" * 60)

# ============================================
# CONFIGURAÇÕES
# ============================================

# POSTGRESQL
POSTGRES_HOST = "localhost"
POSTGRES_DB = "postgres"
POSTGRES_USER = "postgres"
POSTGRES_PASS = "1234"
POSTGRES_PORT = "5432"

# SMTP
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "brunorochasenacal01@gmail.com"
SMTP_PASS = "gesl rgfa sppp ociq"

# ============================================
# INICIALIZAÇÃO FLASK
# ============================================

app = Flask(__name__)
app.secret_key = "sistema-completo-seguro-2024-refatorado"
app.config['PERMANENT_SESSION_LIFETIME'] = 1800

# ============================================
# FUNÇÕES DO BANCO DE DADOS - CORRIGIDAS
# ============================================

def conectar_banco():
    """Conecta ao PostgreSQL"""
    try:
        conn = psycopg2.connect(
            host=POSTGRES_HOST,
            database=POSTGRES_DB,
            user=POSTGRES_USER,
            password=POSTGRES_PASS,
            port=POSTGRES_PORT
        )
        return conn
    except Exception as e:
        print(f"❌ Erro PostgreSQL: {e}")
        return None

def verificar_conexao():
    """Verifica se pode conectar e se tabelas existem - CORRIGIDO"""
    print("\n🔍 VERIFICAÇÃO DE CONEXÃO INICIADA...")
    
    conn = conectar_banco()
    if not conn:
        print("❌ FALHA: Não foi possível conectar ao PostgreSQL")
        print("   Verifique as configurações no código:")
        print(f"   - Host: {POSTGRES_HOST}")
        print(f"   - Banco: {POSTGRES_DB}")
        print(f"   - Usuário: {POSTGRES_USER}")
        print(f"   - Porta: {POSTGRES_PORT}")
        return False
    
    try:
        cursor = conn.cursor()
        
        # 1. Verificar tabela usuarios
        print("\n📊 VERIFICANDO TABELA 'usuarios'...")
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'usuarios'
            );
        """)
        tabela_usuarios = cursor.fetchone()[0]
        
        if not tabela_usuarios:
            print("❌ ERRO: Tabela 'usuarios' NÃO existe!")
            print("   Execute primeiro: psql -U postgres -d postgres -f criar_tabelas.sql")
            cursor.close()
            conn.close()
            return False
        
        print("✅ Tabela 'usuarios' encontrada")
        
        # 2. Verificar colunas da tabela usuarios
        print("\n🔎 VERIFICANDO COLUNAS DA TABELA 'usuarios'...")
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'usuarios'
            ORDER BY ordinal_position;
        """)
        colunas = cursor.fetchall()
        
        print("   Colunas encontradas:")
        for coluna in colunas:
            print(f"   - {coluna[0]} ({coluna[1]})")
        
        # 3. Listar todos os usuários
        print("\n👥 LISTANDO USUÁRIOS CADASTRADOS...")
        try:
            cursor.execute("SELECT id, email, created_at FROM usuarios ORDER BY id")
            usuarios = cursor.fetchall()
            
            if usuarios:
                print(f"   Total: {len(usuarios)} usuário(s)")
                for usuario in usuarios:
                    print(f"   → ID: {usuario[0]}, Email: '{usuario[1]}', Criado: {usuario[2]}")
            else:
                print("   ℹ️  Nenhum usuário cadastrado ainda")
                
        except Exception as e:
            print(f"   ⚠️  Erro ao listar usuários: {e}")
        
        cursor.close()
        conn.close()
        
        print("\n✅ VERIFICAÇÃO CONCLUÍDA COM SUCESSO")
        return True
        
    except Exception as e:
        print(f"❌ ERRO na verificação: {e}")
        return False

# ============================================
# FUNÇÕES DE AUTENTICAÇÃO - CORRIGIDAS
# ============================================

def verificar_credenciais(email, senha):
    """Verifica se email e senha estão corretos - CORRIGIDO"""
    print(f"\n🔐 VERIFICANDO CREDENCIAIS para: {email}")
    
    conn = conectar_banco()
    if not conn:
        return None
    
    try:
        cursor = conn.cursor()
        
        # Query SEM a coluna 'ativo' (que não existe)
        cursor.execute(
            "SELECT id, email FROM usuarios WHERE email = %s AND senha = %s",
            (email, senha)
        )
        usuario = cursor.fetchone()
        
        if usuario:
            print(f"✅ Login válido para usuário ID: {usuario[0]}")
            try:
                cursor.execute(
                    "UPDATE usuarios SET ultimo_login = CURRENT_TIMESTAMP WHERE id = %s",
                    (usuario[0],)
                )
                conn.commit()
                print(f"✅ Último login atualizado para ID: {usuario[0]}")
            except Exception as update_error:
                print(f"⚠️  Não foi possível atualizar último login: {update_error}")
                # Não falha se não conseguir atualizar o timestamp
                conn.rollback()
        else:
            print(f"❌ Credenciais inválidas para: {email}")
        
        cursor.close()
        conn.close()
        
        if usuario:
            return {'id': usuario[0], 'email': usuario[1]}
        return None
        
    except Exception as e:
        print(f"❌ ERRO em verificar_credenciais: {e}")
        return None

def email_existe(email):
    """Verifica se email já está cadastrado - CORRIGIDO"""
    email = email.strip().lower()
    print(f"\n📧 VERIFICANDO SE EMAIL EXISTE: '{email}'")
    
    conn = conectar_banco()
    if not conn:
        print("❌ Falha na conexão com banco")
        return False
    
    try:
        cursor = conn.cursor()
        
        # Listar TODOS os emails primeiro para debug
        cursor.execute("SELECT email FROM usuarios")
        todos_emails = [row[0].lower() for row in cursor.fetchall()]
        
        print(f"   📊 Emails no banco: {todos_emails}")
        
        # Verificação CASE-INSENSITIVE (corrige o bug principal)
        cursor.execute("SELECT id FROM usuarios WHERE LOWER(email) = LOWER(%s)", (email,))
        resultado = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        if resultado:
            print(f"   ❌ EMAIL JÁ CADASTRADO! ID: {resultado[0]}")
            return True
        else:
            print(f"   ✅ Email NÃO cadastrado ainda")
            return False
            
    except Exception as e:
        print(f"❌ ERRO em email_existe: {e}")
        return False



def salvar_usuario(email, senha):
    """Salva novo usuário - VERSÃO SIMPLIFICADA E CORRETA"""
    print(f"\n💾 SALVANDO NOVO USUÁRIO: {email}")
    
    conn = conectar_banco()
    if not conn:
        print("❌ Falha na conexão com banco")
        return None
    
    try:
        cursor = conn.cursor()
        
        print(f"   🛠️  Executando INSERT para: {email}")
        
        # Método 1: Tentar com RETURNING
        try:
            cursor.execute(
                """INSERT INTO usuarios (email, senha) 
                   VALUES (%s, %s) RETURNING id""",
                (email.lower(), senha)
            )
            
            resultado = cursor.fetchone()
            if resultado:
                user_id = resultado[0]
                conn.commit()
                print(f"   ✅ INSERT com RETURNING - ID: {user_id}")
                cursor.close()
                conn.close()
                return user_id
                
        except Exception as e1:
            print(f"   ⚠️  Método 1 falhou: {e1}")
            conn.rollback()
        
        # Método 2: Inserir e depois buscar
        print("   🔄 Tentando método alternativo...")
        try:
            cursor.execute(
                """INSERT INTO usuarios (email, senha) 
                   VALUES (%s, %s)""",
                (email.lower(), senha)
            )
            conn.commit()
            print(f"   ✅ INSERT executado (sem RETURNING)")
            
            # Buscar o ID inserido
            cursor.execute(
                "SELECT id FROM usuarios WHERE email = %s ORDER BY id DESC LIMIT 1",
                (email.lower(),)
            )
            resultado = cursor.fetchone()
            
            if resultado:
                user_id = resultado[0]
                print(f"   🔍 ID encontrado após insert: {user_id}")
                cursor.close()
                conn.close()
                return user_id
            else:
                print("   ⚠️  Não encontrou ID após insert")
                
        except Exception as e2:
            print(f"   ❌ Método 2 também falhou: {e2}")
            conn.rollback()
        
        cursor.close()
        conn.close()
        return None
        
    except Exception as e:
        print(f"❌ ERRO GERAL em salvar_usuario: {e}")
        return None



def trocar_senha(usuario_id, nova_senha):
    """Troca a senha do usuário - CORRIGIDO"""
    print(f"\n🔐 TROCANDO SENHA para usuário ID: {usuario_id}")
    
    conn = conectar_banco()
    if not conn:
        return False
    
    try:
        cursor = conn.cursor()
        
        # Atualiza senha
        cursor.execute(
            "UPDATE usuarios SET senha = %s WHERE id = %s",
            (nova_senha, usuario_id)
        )
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print(f"✅ Senha alterada com sucesso para usuário ID: {usuario_id}")
        return True
        
    except Exception as e:
        print(f"❌ ERRO ao trocar senha: {e}")
        return False

# ============================================
# FUNÇÕES AUXILIARES
# ============================================

def gerar_senha_aleatoria(tamanho=12):
    """Gera senha aleatória"""
    caracteres = string.ascii_letters + string.digits + "!@#$%&*"
    senha = ''.join(random.choice(caracteres) for _ in range(tamanho))
    return senha

def validar_email(email):
    """Valida formato do email"""
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(padrao, email) is not None

# ============================================
# FUNÇÃO ENVIAR EMAIL
# ============================================

def enviar_email(destinatario, assunto, mensagem):
    """Envia email"""
    try:
        print(f"\n📤 ENVIANDO EMAIL para: {destinatario}")
        
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
        print(f"❌ ERRO ao enviar email: {e}")
        return False

# ============================================
# MIDDLEWARE (verifica login)
# ============================================

def login_required(f):
    """Decorator para exigir login"""
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'usuario_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# ============================================
# ROTAS PÚBLICAS - CORRIGIDAS
# ============================================

@app.route('/')
def index():
    """Página inicial - Cadastro"""
    if 'usuario_id' in session:
        return redirect(url_for('sistema'))
    return render_template('index.html')




@app.route('/cadastrar', methods=['POST'])
def cadastrar():
    """Processa cadastro de novo usuário - VERSÃO TOLERANTE"""
    print("\n" + "="*60)
    print("📝 INICIANDO PROCESSO DE CADASTRO")
    print("="*60)
    
    try:
        dados = request.get_json()
        email_original = dados.get('email', '').strip()
        email = email_original.lower()
        
        print(f"📨 Email recebido: '{email_original}'")
        
        # VALIDAÇÃO
        if not email:
            return jsonify({'sucesso': False, 'mensagem': 'Informe um email.'}), 400
        
        if not validar_email(email):
            return jsonify({'sucesso': False, 'mensagem': 'Email inválido.'}), 400
        
        # VERIFICAÇÃO DE EMAIL EXISTENTE
        if email_existe(email):
            return jsonify({'sucesso': False, 'mensagem': 'Email já cadastrado.'}), 400
        
        # GERAÇÃO DE SENHA
        senha = gerar_senha_aleatoria()
        print(f"🔑 Senha gerada: {senha}")
        
        # SALVAR NO BANCO
        user_id = salvar_usuario(email, senha)
        
        # VERIFICAR SE REALMENTE FOI SALVO (mesmo se user_id for None)
        print(f"\n🔍 VERIFICANDO SE EMAIL FOI SALVO NO BANCO...")
        conn = conectar_banco()
        if conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id FROM usuarios WHERE email = %s", (email,))
            verificado = cursor.fetchone()
            cursor.close()
            conn.close()
            
            if verificado:
                print(f"✅ CONFIRMADO: Email '{email}' está no banco! ID: {verificado[0]}")
                user_id = verificado[0]  # Usa o ID real do banco
            else:
                print(f"❌ ALERTA: Email '{email}' NÃO está no banco!")
        
        # DECISÃO: Se tem user_id ou foi verificado no banco, é sucesso
        if user_id or ('verificado' in locals() and verificado):
            print(f"\n🎉 CADASTRO REALIZADO COM SUCESSO!")
            print(f"   Email: {email}")
            print(f"   Senha: {senha}")
            print(f"   ID: {user_id or verificado[0] if 'verificado' in locals() else 'N/A'}")
            
            # Tenta enviar email (opcional)
            try:
                assunto = "✅ Cadastro Realizado"
                mensagem_email = f"""
                <html><body>
                <h2>Cadastro Realizado!</h2>
                <p><strong>Email:</strong> {email}</p>
                <p><strong>Senha:</strong> {senha}</p>
                </body></html>
                """
                
                if enviar_email(email, assunto, mensagem_email):
                    return jsonify({
                        'sucesso': True,
                        'mensagem': f'Cadastro realizado! Email com senha enviado para {email}'
                    })
                else:
                    return jsonify({
                        'sucesso': True,
                        'mensagem': f'Cadastro realizado! Sua senha é: {senha}'
                    })
            except:
                return jsonify({
                    'sucesso': True,
                    'mensagem': f'Cadastro realizado! Sua senha é: {senha}'
                })
        else:
            return jsonify({'sucesso': False, 'mensagem': 'Erro ao salvar cadastro.'}), 500
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno.'}), 500



















@app.route('/login')
def login():
    """Página de login"""
    if 'usuario_id' in session:
        return redirect(url_for('sistema'))
    return render_template('login.html')

@app.route('/logar', methods=['POST'])
def logar():
    """Processa login"""
    try:
        dados = request.get_json()
        email = dados.get('email', '').strip().lower()
        senha = dados.get('senha', '')
        
        if not email or not senha:
            return jsonify({'sucesso': False, 'mensagem': 'Preencha todos os campos.'}), 400
        
        usuario = verificar_credenciais(email, senha)
        
        if usuario:
            session['usuario_id'] = usuario['id']
            session['usuario_email'] = usuario['email']
            session.permanent = True
            
            return jsonify({
                'sucesso': True,
                'mensagem': 'Login realizado com sucesso!',
                'redirect': url_for('sistema')
            })
        else:
            return jsonify({'sucesso': False, 'mensagem': 'Email ou senha incorretos.'}), 401
            
    except Exception as e:
        print(f"❌ Erro no login: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno.'}), 500

# ============================================
# ROTAS DE DIAGNÓSTICO
# ============================================

@app.route('/debug')
def debug():
    """Página de diagnóstico do sistema"""
    conn = conectar_banco()
    
    info = {
        'conexao': conn is not None,
        'usuarios': [],
        'total_usuarios': 0
    }
    
    if conn:
        try:
            cursor = conn.cursor()
            
            # Listar usuários
            cursor.execute("SELECT id, email, created_at FROM usuarios ORDER BY id")
            info['usuarios'] = cursor.fetchall()
            info['total_usuarios'] = len(info['usuarios'])
            
            cursor.close()
            conn.close()
        except Exception as e:
            info['erro'] = str(e)
    
    return f"""
    <html>
    <body style="font-family: Arial; padding: 20px;">
        <h1>🔧 Diagnóstico do Sistema</h1>
        
        <h2>📊 Status do Banco de Dados</h2>
        <p><strong>Conexão:</strong> {'✅ OK' if info['conexao'] else '❌ FALHA'}</p>
        
        <h2>👥 Usuários Cadastrados ({info['total_usuarios']})</h2>
        <table border="1" cellpadding="10" style="border-collapse: collapse;">
            <tr style="background: #f2f2f2;">
                <th>ID</th>
                <th>Email</th>
                <th>Criado em</th>
            </tr>
            {"".join(f'<tr><td>{u[0]}</td><td>{u[1]}</td><td>{u[2]}</td></tr>' for u in info['usuarios'])}
        </table>
        
        <h2>🔗 Links</h2>
        <ul>
            <li><a href="/">Página de Cadastro</a></li>
            <li><a href="/login">Página de Login</a></li>
        </ul>
        
        <h2>🧪 Teste Rápido</h2>
        <button onclick="testarCadastro()">Testar Cadastro (teste@exemplo.com)</button>
        <script>
            async function testarCadastro() {{
                const response = await fetch('/cadastrar', {{
                    method: 'POST',
                    headers: {{'Content-Type': 'application/json'}},
                    body: JSON.stringify({{email: 'teste@exemplo.com'}})
                }});
                const result = await response.json();
                alert(result.mensagem);
                location.reload();
            }}
        </script>
    </body>
    </html>
    """

# ============================================
# ROTAS PROTEGIDAS
# ============================================

@app.route('/sistema')
@login_required
def sistema():
    """Sistema principal (após login)"""
    return render_template('sistema.html', 
                         email=session.get('usuario_email'),
                         usuario_id=session.get('usuario_id'))

@app.route('/trocar-senha')
@login_required
def pagina_trocar_senha():
    """Página para trocar senha"""
    return render_template('trocar_senha.html')

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
        
        if trocar_senha(session['usuario_id'], nova_senha):
            # Envia email de notificação
            assunto = "🔒 Sua senha foi alterada"
            mensagem = f"""
            <html>
            <body>
                <h2>✅ Senha Alterada com Sucesso!</h2>
                <p>Sua senha de acesso ao sistema foi alterada em {session['usuario_email']}.</p>
                <p><strong>Nova senha:</strong> {nova_senha}</p>
                <p><small>Se não foi você quem alterou a senha, entre em contato imediatamente.</small></p>
            </body>
            </html>
            """
            
            enviar_email(session['usuario_email'], assunto, mensagem)
            
            return jsonify({
                'sucesso': True,
                'mensagem': 'Senha alterada com sucesso! Um email foi enviado com confirmação.'
            })
        else:
            return jsonify({'sucesso': False, 'mensagem': 'Erro ao alterar senha.'}), 500
            
    except Exception as e:
        print(f"❌ Erro ao trocar senha: {e}")
        return jsonify({'sucesso': False, 'mensagem': 'Erro interno.'}), 500

@app.route('/logout')
def logout():
    """Logout do sistema"""
    session.clear()
    return redirect(url_for('index'))

# ============================================
# INICIALIZAÇÃO
# ============================================

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🚀 SISTEMA COMPLETO REFATORADO - INICIANDO")
    print("="*60)
    
    print("\n⚙️  CONFIGURAÇÕES:")
    print(f"   📦 PostgreSQL: {POSTGRES_USER}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}")
    print(f"   📧 SMTP: {SMTP_USER}")
    
    if verificar_conexao():
        print("\n" + "="*60)
        print("✅ SISTEMA PRONTO PARA USO!")
        print("="*60)
        print("\n🌐 URLs IMPORTANTES:")
        print("   • Cadastro:     http://localhost:5000")
        print("   • Login:        http://localhost:5000/login")
        print("   • Diagnóstico:  http://localhost:5000/debug")
        print("\n📝 LOGS DO SISTEMA (aparecerão abaixo):")
        print("="*60 + "\n")
        
        app.run(host='0.0.0.0', port=5000, debug=True)
    else:
        print("\n" + "="*60)
        print("❌ FALHA NA INICIALIZAÇÃO")
        print("="*60)
        print("\n⚠️  Verifique:")
        print("   1. O PostgreSQL está rodando?")
        print("   2. As credenciais estão corretas?")
        print("   3. As tabelas foram criadas?")
        print("\n💡 Execute: psql -U postgres -d postgres -f criar_tabelas.sql")