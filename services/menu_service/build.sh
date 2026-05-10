#!/usr/bin/env bash
# build.sh — script de build para Render
# Render lo ejecuta automáticamente en cada deploy

set -o errexit  # salir si hay error

pip install --upgrade pip
pip install -r requirements.txt

# Recolectar archivos estáticos
python manage.py collectstatic --no-input

# Ejecutar migraciones
python manage.py migrate --no-input