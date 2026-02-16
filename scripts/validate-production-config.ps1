# ══════════════════════════════════════════════════════════════════════════════
# Script de Validación de Configuración de Producción - SATC
# ══════════════════════════════════════════════════════════════════════════════
# Autor: Equipo de Seguridad SATC
# Versión: 2.0
# Fecha: 14 de febrero de 2026
# ══════════════════════════════════════════════════════════════════════════════

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "     VALIDACION DE CONFIGURACION DE PRODUCCION - SATC         " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

$ErrorCount = 0
$WarningCount = 0

# ──────────────────────────────────────────────────────────────────────────────
# FUNCIONES AUXILIARES
# ──────────────────────────────────────────────────────────────────────────────

function Show-Result {
    param(
        [string]$Test,
        [bool]$Passed,
        [string]$Message = ""
    )
    
    if ($Passed) {
        Write-Host "  [OK] " -ForegroundColor Green -NoNewline
        Write-Host "$Test" -ForegroundColor White
        if ($Message) {
            Write-Host "       -> $Message" -ForegroundColor Gray
        }
    } else {
        Write-Host "  [ERROR] " -ForegroundColor Red -NoNewline
        Write-Host "$Test" -ForegroundColor White
        if ($Message) {
            Write-Host "          -> $Message" -ForegroundColor Yellow
        }
        $script:ErrorCount++
    }
}

function Show-Warning {
    param(
        [string]$Test,
        [string]$Message
    )
    
    Write-Host "  [WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host "$Test" -ForegroundColor White
    Write-Host "         -> $Message" -ForegroundColor Yellow
    $script:WarningCount++
}

# ──────────────────────────────────────────────────────────────────────────────
# 1. VALIDAR ARCHIVOS DE CÓDIGO
# ──────────────────────────────────────────────────────────────────────────────

Write-Host "`n[1] VALIDACIÓN DE CÓDIGO" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

# Verificar que JWE esté importado en auth.py
$authFile = "app-users\routes\auth.py"
if (Test-Path $authFile) {
    $content = Get-Content $authFile -Raw
    
    # Verificar import de jwe
    if ($content -match "from jose import jwt, jwe") {
        Show-Result "Import de JWE en auth.py" $true "JWE correctamente importado"
    } else {
        Show-Result "Import de JWE en auth.py" $false "Falta import de jwe"
    }
    
    # Verificar uso de jwe.encrypt
    if ($content -match "jwe\.encrypt\(") {
        Show-Result "Encriptación JWE implementada" $true "jwe.encrypt() encontrado"
    } else {
        Show-Result "Encriptación JWE implementada" $false "No se encontró jwe.encrypt()"
    }
    
    # Verificar secure=True
    if ($content -match "secure\s*=\s*True") {
        Show-Result "Cookie secure=True configurada" $true "Cookies solo HTTPS"
    } else {
        Show-Result "Cookie secure=True configurada" $false "secure=False detectado"
    }
    
    # Verificar algoritmo A256GCM
    if ($content -match "encryption\s*=\s*'A256GCM'") {
        Show-Result "Algoritmo A256GCM configurado" $true "AES-256-GCM para encriptación"
    } else {
        Show-Warning "Algoritmo A256GCM" "Verificar algoritmo de encriptación"
    }
} else {
    Show-Result "Archivo auth.py" $false "No se encuentra el archivo $authFile"
}

# Verificar que JWE esté en gateway
$gatewayFile = "api-gateway\utils\funtions.py"
if (Test-Path $gatewayFile) {
    $content = Get-Content $gatewayFile -Raw
    
    # Verificar import de jwe
    if ($content -match "from jose import jwt, jwe") {
        Show-Result "Import de JWE en gateway" $true "JWE correctamente importado"
    } else {
        Show-Result "Import de JWE en gateway" $false "Falta import de jwe en gateway"
    }
    
    # Verificar uso de jwe.decrypt
    if ($content -match "jwe\.decrypt\(") {
        Show-Result "Desencriptación JWE en gateway" $true "jwe.decrypt() encontrado"
    } else {
        Show-Result "Desencriptación JWE en gateway" $false "No se encontró jwe.decrypt()"
    }
} else {
    Show-Result "Archivo funtions.py (gateway)" $false "No se encuentra el archivo $gatewayFile"
}

# ──────────────────────────────────────────────────────────────────────────────
# 2. VALIDAR VARIABLES DE ENTORNO
# ──────────────────────────────────────────────────────────────────────────────

Write-Host "`n[2] VARIABLES DE ENTORNO" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

# Verificar que existe .env.production.example
if (Test-Path ".env.production.example") {
    Show-Result "Archivo .env.production.example" $true "Archivo de ejemplo creado"
} else {
    Show-Result "Archivo .env.production.example" $false "Falta archivo de configuración"
}

# Verificar .env actual (si existe)
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    
    # Verificar si hay claves por cambiar
    if ($envContent -match "CAMBIAR") {
        Show-Warning "Claves secretas en .env" "HAY CLAVES POR CAMBIAR - Ejecutar: openssl rand -hex 32"
    } else {
        Show-Result "Claves secretas actualizadas" $true "No se encontraron placeholders 'CAMBIAR'"
    }
    
    # Verificar CORS_ORIGINS
    if ($envContent -match "CORS_ORIGINS=.*localhost") {
        Show-Warning "CORS_ORIGINS" "Configurado para localhost (cambiar en producción)"
    } elseif ($envContent -match "CORS_ORIGINS=https://") {
        Show-Result "CORS_ORIGINS configurado" $true "Configurado para HTTPS"
    }
} else {
    Show-Warning "Archivo .env" "No existe archivo .env (crear desde .env.production.example)"
}

# ──────────────────────────────────────────────────────────────────────────────
# 3. VALIDAR CONTENEDORES DOCKER
# ──────────────────────────────────────────────────────────────────────────────

Write-Host "`n[3] CONTENEDORES DOCKER" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

$containers = @(
    "satc-app-users",
    "satc-app-sanctioning", 
    "satc-app-docs",
    "satc-api-gateway",
    "satc-redis",
    "satc-postgres-users",
    "clamav"
)

foreach ($container in $containers) {
    $status = docker ps --filter "name=$container" --format "{{.Status}}" 2>$null
    if ($status -match "Up") {
        Show-Result "Contenedor $container" $true "Estado: $status"
    } else {
        Show-Result "Contenedor $container" $false "No está corriendo"
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 4. VALIDAR CONFIGURACIÓN DE SEGURIDAD
# ──────────────────────────────────────────────────────────────────────────────

Write-Host "`n[4] CONFIGURACIÓN DE SEGURIDAD" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

# Verificar documentación creada
if (Test-Path "Documentation\CONFIGURACION_PRODUCCION.md") {
    Show-Result "Documentación de producción" $true "CONFIGURACION_PRODUCCION.md creado"
} else {
    Show-Warning "Documentación" "Falta CONFIGURACION_PRODUCCION.md"
}

if (Test-Path "Documentation\docs base\SEGURIDAD_SATC.md") {
    Show-Result "Documento de seguridad" $true "SEGURIDAD_SATC.md creado"
} else {
    Show-Warning "Documento de seguridad" "Falta SEGURIDAD_SATC.md"
}

# Verificar python-jose[cryptography] en requirements
$reqFiles = Get-ChildItem -Path . -Recurse -Filter "requirements.txt" | Select-Object -First 1
if ($reqFiles) {
    $reqContent = Get-Content $reqFiles.FullName -Raw
    if ($reqContent -match "python-jose\[cryptography\]") {
        Show-Result "python-jose[cryptography]" $true "Librería instalada para JWE"
    } else {
        Show-Result "python-jose[cryptography]" $false "Falta instalar python-jose[cryptography]"
    }
}

# ──────────────────────────────────────────────────────────────────────────────
# 5. TESTS DE FUNCIONALIDAD (SI SISTEMA ESTÁ CORRIENDO)
# ──────────────────────────────────────────────────────────────────────────────

Write-Host "`n[5] TESTS DE FUNCIONALIDAD" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

# Verificar si el sistema está corriendo
try {
    $healthCheck = Invoke-RestMethod -Uri "http://localhost:8000/health" -Method Get -TimeoutSec 5 -ErrorAction SilentlyContinue
    if ($healthCheck) {
        Show-Result "Health check" $true "Gateway responde correctamente"
        
        # Verificar estado de cache
        if ($healthCheck.cache) {
            $cacheStatus = $healthCheck.cache.status
            if ($cacheStatus -eq "healthy") {
                Show-Result "Sistema de cache" $true "Redis funcionando"
            } else {
                Show-Warning "Sistema de cache" "Cache no disponible: $cacheStatus"
            }
        }
    }
} catch {
    Show-Warning "Sistema no disponible" "No se puede conectar a http://localhost:8000 (Sistema debe estar corriendo)"
}

# ──────────────────────────────────────────────────────────────────────────────
# 6. CHECKLIST DE DESPLIEGUE
# ──────────────────────────────────────────────────────────────────────────────

Write-Host "`n[6] CHECKLIST PRE-DEPLOYMENT" -ForegroundColor Yellow
Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Yellow

Write-Host "`nPendientes antes de desplegar en produccion:" -ForegroundColor White
Write-Host "  [ ] Cambiar SECRET_KEY_GATEWAY (openssl rand -hex 32)" -ForegroundColor Cyan
Write-Host "  [ ] Cambiar SECRET_GATEWAY (openssl rand -hex 32)" -ForegroundColor Cyan
Write-Host "  [ ] Cambiar SERVICE_SECRET_KEY (openssl rand -hex 32)" -ForegroundColor Cyan
Write-Host "  [ ] Cambiar POSTGRES_PASSWORD" -ForegroundColor Cyan
Write-Host "  [ ] Cambiar REDIS_PASSWORD" -ForegroundColor Cyan
Write-Host "  [ ] Cambiar MINIO_ROOT_PASSWORD" -ForegroundColor Cyan
Write-Host "  [ ] Configurar CORS_ORIGINS=https://satc.gov.co" -ForegroundColor Cyan
Write-Host "  [ ] Configurar MINIO_SECURE=true" -ForegroundColor Cyan
Write-Host "  [ ] Configurar BCRYPT_ROUNDS=10" -ForegroundColor Cyan
Write-Host "  [ ] Configurar DEBUG=false y ENVIRONMENT=production" -ForegroundColor Cyan
Write-Host "  [ ] Obtener certificado SSL (Let Encrypt o comercial)" -ForegroundColor Cyan
Write-Host "  [ ] Configurar NGINX con HTTPS y HSTS" -ForegroundColor Cyan
Write-Host "  [ ] Configurar backups automaticos" -ForegroundColor Cyan
Write-Host "  [ ] Ejecutar pip-audit (vulnerabilidades)" -ForegroundColor Cyan
Write-Host "  [ ] Realizar pentesting inicial" -ForegroundColor Cyan

# ──────────────────────────────────────────────────────────────────────────────
# RESUMEN FINAL
# ──────────────────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host "                    RESUMEN DE VALIDACION                      " -ForegroundColor Cyan
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""

if ($ErrorCount -eq 0 -and $WarningCount -eq 0) {
    Write-Host "  [OK] PERFECTO: Sistema configurado correctamente" -ForegroundColor Green
    Write-Host "       -> Revisar checklist pre-deployment antes de produccion" -ForegroundColor Gray
} elseif ($ErrorCount -eq 0) {
    Write-Host "  [WARN] BUENO: Sistema configurado con $WarningCount advertencias" -ForegroundColor Yellow
    Write-Host "         -> Revisar advertencias antes de desplegar" -ForegroundColor Gray
} else {
    Write-Host "  [ERROR] Se encontraron $ErrorCount errores y $WarningCount advertencias" -ForegroundColor Red
    Write-Host "          -> Corregir errores antes de continuar" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "Para mas informacion, revisar:" -ForegroundColor White
Write-Host "  - Documentation\CONFIGURACION_PRODUCCION.md" -ForegroundColor Cyan
Write-Host "  - Documentation\docs base\SEGURIDAD_SATC.md" -ForegroundColor Cyan
Write-Host "  - .env.production.example" -ForegroundColor Cyan

Write-Host ""
Write-Host "================================================================" -ForegroundColor Cyan
Write-Host ""
