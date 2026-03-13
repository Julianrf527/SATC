# ====================================================
# SATC - Build & Push a Registry Privado
# Uso: .\deploy\build-and-push.ps1
#
# Requisitos:
#   - Docker Desktop corriendo
#   - Haber hecho login al registry:
#       docker login ghcr.io -u TU_USUARIO
# ====================================================

param(
    [string]$Version   = "latest",
    [string]$ServerUrl = ""          # IP o dominio del servidor Ubuntu, ej: 192.168.1.100
)

# ── CONFIGURACIÓN ─────────────────────────────────────────────
# Cambia esto con tu usuario de GitHub (para GHCR) o Docker Hub
$Registry  = "ghcr.io/julianrf527"

# Si no pasaste ServerUrl como parámetro, pregunta aquí
if (-not $ServerUrl) {
    $ServerUrl = Read-Host "IP o dominio del servidor Ubuntu (ej: 192.168.1.100)"
}
# ──────────────────────────────────────────────────────────────

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  SATC Deploy — Build & Push" -ForegroundColor Cyan
Write-Host "  Registry : $Registry" -ForegroundColor Cyan
Write-Host "  Version  : $Version" -ForegroundColor Cyan
Write-Host "  Servidor : $ServerUrl" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# Mapa: nombre-imagen => contexto de build
$Services = [ordered]@{
    "satc-gateway"     = @{ Context = "$Root\api-gateway";      Args = @() }
    "satc-users"       = @{ Context = "$Root\app-users";        Args = @() }
    "satc-sanctioning" = @{ Context = "$Root\app-sancionatoria"; Args = @() }
    "satc-docs"        = @{ Context = "$Root\app-docs";         Args = @() }
    "satc-frontend"    = @{ Context = "$Root\frontend";         Args = @("--build-arg", "VITE_API_URL=http://$ServerUrl`:8000") }
}

# ── BUILD ─────────────────────────────────────────────────────
Write-Host "[ 1/2 ] Construyendo imágenes..." -ForegroundColor Yellow
foreach ($name in $Services.Keys) {
    $svc  = $Services[$name]
    $tag  = "$Registry/${name}:$Version"
    Write-Host "  → Building $tag" -ForegroundColor Gray

    $buildArgs = @("build", "-t", $tag) + $svc.Args + @($svc.Context)
    docker @buildArgs
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Falló el build de $name" -ForegroundColor Red
        exit 1
    }
    Write-Host "    ✓ $name" -ForegroundColor Green
}

# ── PUSH ──────────────────────────────────────────────────────
Write-Host ""
Write-Host "[ 2/2 ] Subiendo imágenes al registry..." -ForegroundColor Yellow
foreach ($name in $Services.Keys) {
    $tag = "$Registry/${name}:$Version"
    Write-Host "  → Pushing $tag" -ForegroundColor Gray
    docker push $tag
    if ($LASTEXITCODE -ne 0) {
        Write-Host "ERROR: Falló el push de $name" -ForegroundColor Red
        exit 1
    }
    Write-Host "    ✓ $name" -ForegroundColor Green
}

# ── EMPAQUETAR ARCHIVOS DE CONFIGURACIÓN ─────────────────────
# Crea un zip con todo lo que necesita el servidor Ubuntu
# (sin código fuente — solo configs, SQL, nginx, scripts)
Write-Host ""
Write-Host "[ + ] Empaquetando archivos de configuración para el servidor..." -ForegroundColor Yellow

$PkgDir  = "$Root\deploy\satc-server-package"
$ZipPath = "$Root\deploy\satc-server-package.zip"

if (Test-Path $PkgDir)  { Remove-Item $PkgDir  -Recurse -Force }
if (Test-Path $ZipPath) { Remove-Item $ZipPath -Force }
New-Item -ItemType Directory -Path $PkgDir | Out-Null

# Archivos a incluir (NO incluye carpetas de código fuente)
$Items = @(
    @{ Src = "$Root\deploy\docker-compose.prod.yml"; Dst = "$PkgDir\docker-compose.yml" }
    @{ Src = "$Root\db-script";                      Dst = "$PkgDir\db-script" }
    @{ Src = "$Root\nginx\nginx.conf";               Dst = "$PkgDir\nginx\nginx.conf" }
    @{ Src = "$Root\scripts\backup-all.sh";          Dst = "$PkgDir\scripts\backup-all.sh" }
    @{ Src = "$Root\scripts\setup-cron-backup.sh";   Dst = "$PkgDir\scripts\setup-cron-backup.sh" }
    @{ Src = "$Root\deploy\setup-ubuntu.sh";         Dst = "$PkgDir\setup-ubuntu.sh" }
)

foreach ($item in $Items) {
    $dstDir = Split-Path $item.Dst -Parent
    if (-not (Test-Path $dstDir)) { New-Item -ItemType Directory -Path $dstDir -Force | Out-Null }
    Copy-Item -Path $item.Src -Destination $item.Dst -Recurse -Force
}

# Generar .env de ejemplo para el servidor
@"
# =============================================
# SATC — Variables de entorno para producción
# Rellena los valores y renombra a .env
# =============================================
REGISTRY=$Registry
VERSION=$Version

# Contraseñas base de datos
POSTGRES_PASSWORD=CAMBIAR_PASSWORD_SEGURO

# Redis
REDIS_PASSWORD=CAMBIAR_PASSWORD_REDIS

# JWT — genera con: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=CAMBIAR_SECRET_KEY
SECRET_KEY_GATEWAY=CAMBIAR_SECRET_KEY_GATEWAY
SECRET_GATEWAY=CAMBIAR_SECRET_GATEWAY

# MinIO
MINIO_ROOT_USER=minioadmin
MINIO_ROOT_PASSWORD=CAMBIAR_PASSWORD_MINIO

# Email SMTP
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=tu-email@gmail.com
SMTP_PASSWORD=tu-app-password
SMTP_FROM=tu-email@gmail.com

# Frontend — URL pública del servidor
FRONTEND_API_URL=http://$ServerUrl`:8000
CORS_ORIGINS=http://$ServerUrl

# ClamAV
CLAMAV_ENABLED=true

# Cache
CACHE_TYPE=redis
CACHE_TTL=900

# Permisos
PERMISO_ROL=admin_roles y permisos
PERMISO_USER=admin_registrar usuario
GESTION_USER=admin_gestionar usuarios
USER_LOG=admin_auditoria usuarios
MAX_FILE_SIZE_MB=10
"@ | Set-Content "$PkgDir\.env.example" -Encoding UTF8

Compress-Archive -Path "$PkgDir\*" -DestinationPath $ZipPath
Remove-Item $PkgDir -Recurse -Force

Write-Host "    ✓ Paquete creado: deploy\satc-server-package.zip" -ForegroundColor Green

# ── RESUMEN ───────────────────────────────────────────────────
Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  ✓ Build y push completados" -ForegroundColor Green
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Próximos pasos en el servidor Ubuntu:" -ForegroundColor White
Write-Host ""
Write-Host "  1. Copia el paquete al servidor:" -ForegroundColor Gray
Write-Host "     scp deploy\satc-server-package.zip usuario@$ServerUrl`:/home/usuario/" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  2. En Ubuntu, descomprime y ejecuta:" -ForegroundColor Gray
Write-Host "     unzip satc-server-package.zip -d satc" -ForegroundColor DarkGray
Write-Host "     cd satc" -ForegroundColor DarkGray
Write-Host "     cp .env.example .env && nano .env   # rellena contraseñas" -ForegroundColor DarkGray
Write-Host "     chmod +x setup-ubuntu.sh && ./setup-ubuntu.sh" -ForegroundColor DarkGray
Write-Host ""
Write-Host "  Registry: $Registry" -ForegroundColor DarkGray
Write-Host "  Versión : $Version" -ForegroundColor DarkGray
Write-Host ""
