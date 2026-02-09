#!/usr/bin/env bash
# Build script para Render

set -o errexit

# Instala as dependências
pip install --upgrade pip
pip install -r requirements.txt
