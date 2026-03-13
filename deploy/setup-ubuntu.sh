#!/bin/bash
# ====================================================
# SATC - Setup inicial en servidor Ubuntu
# ====================================================
# Uso (primera vez):
#   chmod +x setup-ubuntu.sh
#   ./setup-ubuntu.sh
#
# Para actualizar después:
#   ./setup-ubuntu.sh --update
# ====================================================

set -e

MODE=${1:-"--install"}
SATC_DIR="$(cd "$(dirname "$0")" && pwd)"

# Colores
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; CYAN='\033[0;36m'; NC='\033[0m'
ok()   { echo -e "${GREEN}  ✓ $1${NC}"; }
info() { echo -e "${CYAN}  → $1${NC}"; }
warn() { echo -e "${YELLOW}  ⚠ $1${NC}"; }
fail() { echo -e "${RED}  ✗ $1${NC}"; exit 1; }

echo ""
echo -e "${CYAN}=============================================${NC}"
echo -e "${CYAN}  SATC — Instalación en Ubuntu${NC}"
echo -e "${CYAN}  Directorio: $SATC_DIR${NC}"
echo -e "${CYAN}=============================================${NC}"
echo ""

# ── VERIFICAR REQUISITOS ──────────────────────────────────────
info "Verificando requisitos..."
command -v docker        >/dev/null 2>&1 || fail "Docker no está instalado. Instala con: curl -fsSL https://get.docker.com | sh"
docker compose version   >/dev/null 2>&1 || fail "Docker Compose plugin no encontrado."
ok "Docker $(docker --version | awk '{print $3}' | tr -d ',')"
ok "Docker Compose $(docker compose version --short)"

# ── VERIFICAR .env ────────────────────────────────────────────
info "Verificando configuración..."
if [ ! -f "$SATC_DIR/.env" ]; then
    if [ -f "$SATC_DIR/.env.example" ]; then
        warn ".env no encontrado. Copiando .env.example → .env"
        cp "$SATC_DIR/.env.example" "$SATC_DIR/.env"
        echo ""
        echo -e "${YELLOW}  IMPORTANTE: Edita el archivo .env con tus contraseñas reales:${NC}"
        echo -e "${YELLOW}  nano $SATC_DIR/.env${NC}"
        echo ""
        read -p "  ¿Ya editaste el .env? (s/N): " confirm
        [[ "$confirm" =~ ^[sS]$ ]] || { warn "Edita el .env primero y vuelve a ejecutar."; exit 0; }
    else
        fail "No existe .env ni .env.example. Crea el archivo .env con las variables requeridas."
    fi
fi

# Verificar que las variables críticas no sean los valores de ejemplo
source "$SATC_DIR/.env"
critical_vars=("POSTGRES_PASSWORD" "SECRET_KEY" "SECRET_KEY_GATEWAY" "SECRET_GATEWAY" "REGISTRY")
for var in "${critical_vars[@]}"; do
    val="${!var}"
    if [ -z "$val" ]; then
        fail "Variable $var está vacía en .env"
    fi
    if [[ "$val" == *"CAMBIAR"* ]]; then
        fail "Variable $var aún tiene valor de ejemplo ('$val'). Cámbiala en .env"
    fi
done
ok ".env validado"

# ── CREAR DIRECTORIOS NECESARIOS ──────────────────────────────
info "Creando estructura de directorios..."
mkdir -p "$SATC_DIR/backups/postgres-users"
mkdir -p "$SATC_DIR/backups/postgres-sanctioning"
mkdir -p "$SATC_DIR/backups/postgres-docs"
mkdir -p "$SATC_DIR/backups/minio"
ok "Directorios creados"

# ── PERMISOS DEL .env ─────────────────────────────────────────
chmod 600 "$SATC_DIR/.env"
ok ".env protegido (chmod 600)"

# ── LOGIN AL REGISTRY ─────────────────────────────────────────
if [ "$MODE" = "--install" ]; then
    source "$SATC_DIR/.env"
    echo ""
    info "Autenticando en el registry ($REGISTRY)..."
    echo -e "${YELLOW}  Necesitas un token de acceso (lectura) de GitHub/Docker Hub${NC}"
    read -p "  GitHub username o Docker Hub user: " REG_USER
    read -s -p "  Token/Password del registry: " REG_PASS
    echo ""
    echo "$REG_PASS" | docker login "${REGISTRY%%/*}" -u "$REG_USER" --password-stdin
    ok "Autenticado en ${REGISTRY%%/*}"
fi

# ── PULL DE IMÁGENES ──────────────────────────────────────────
echo ""
info "Descargando imágenes desde el registry..."
source "$SATC_DIR/.env"
docker compose -f "$SATC_DIR/docker-compose.yml" pull \
    app-users app-sanctioning app-docs api-gateway frontend
ok "Imágenes descargadas"

# ── LEVANTAR SERVICIOS ────────────────────────────────────────
echo ""
if [ "$MODE" = "--update" ]; then
    info "Actualizando servicios (sin downtime de infra)..."
    docker compose -f "$SATC_DIR/docker-compose.yml" up -d \
        app-users app-sanctioning app-docs api-gateway frontend
else
    info "Levantando todos los servicios..."
    docker compose -f "$SATC_DIR/docker-compose.yml" up -d
fi

# ── ESPERAR QUE ESTÉN HEALTHY ─────────────────────────────────
echo ""
info "Esperando que los servicios estén sanos (puede tardar ~3 min por ClamAV)..."
MAX_WAIT=300
ELAPSED=0
INTERVAL=10

while [ $ELAPSED -lt $MAX_WAIT ]; do
    UNHEALTHY=$(docker compose -f "$SATC_DIR/docker-compose.yml" ps --format json 2>/dev/null \
        | grep -c '"Health":"unhealthy"' || true)
    STARTING=$(docker compose -f "$SATC_DIR/docker-compose.yml" ps --format json 2>/dev/null \
        | grep -c '"Health":"starting"' || true)

    if [ "$STARTING" -eq "0" ] && [ "$UNHEALTHY" -eq "0" ]; then
        break
    fi

    echo -e "    Esperando... ($ELAPSED s) — $STARTING iniciando, $UNHEALTHY no sanos"
    sleep $INTERVAL
    ELAPSED=$((ELAPSED + INTERVAL))
done

# ── ESTADO FINAL ──────────────────────────────────────────────
echo ""
echo -e "${CYAN}  Estado de los servicios:${NC}"
docker compose -f "$SATC_DIR/docker-compose.yml" ps --format "table {{.Name}}\t{{.Status}}"

echo ""
source "$SATC_DIR/.env"
SERVER_IP=$(hostname -I | awk '{print $1}')
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN}  ✓ SATC desplegado correctamente${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo -e "  Frontend  : ${CYAN}http://$SERVER_IP${NC}"
echo -e "  API       : ${CYAN}http://$SERVER_IP:8000${NC}"
echo -e "  MinIO     : ${CYAN}http://$SERVER_IP:9001${NC}"
echo ""
echo -e "  Versión   : ${VERSION:-latest}"
echo -e "  Registry  : $REGISTRY"
echo ""
echo -e "  Para ver logs:    docker compose logs -f api-gateway"
echo -e "  Para actualizar:  ./setup-ubuntu.sh --update"
echo ""
