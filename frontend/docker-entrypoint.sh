#!/bin/sh

# ====================================
# Docker Entrypoint para Frontend
# ====================================
# Este script reemplaza las variables de entorno en tiempo de ejecución
# para permitir configuración dinámica sin reconstruir la imagen

set -eu

# Archivo de configuración JavaScript que contendrá las env vars
ENV_JS_FILE="/usr/share/nginx/html/env-config.js"

echo "Generando configuración de entorno en runtime..."

# Crear archivo con variables de entorno
cat <<EOF > $ENV_JS_FILE
window.ENV = {
  VITE_API_URL: "${VITE_API_URL-http://localhost:8000}"
};
EOF

echo "✓ Configuración generada:"
cat $ENV_JS_FILE

# Ejecutar nginx
exec "$@"
