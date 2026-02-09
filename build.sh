#!/usr/bin/env bash
# Build script para Render

set -o errexit

# Instala as dependências
pip install --upgrade pip
pip install -r requirements.txt

# Cria as tabelas no banco de dados
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('✅ Banco de dados inicializado')"
