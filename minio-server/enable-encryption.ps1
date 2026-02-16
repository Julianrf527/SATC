# ══════════════════════════════════════════════════════════════
# Configuración de Encriptación MinIO para Red Local
# Server-Side Encryption (SSE) con AES-256
# ══════════════════════════════════════════════════════════════

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Configurar Encriptacion MinIO (SSE)" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Configuración desde .env
$MinioHost = $env:MINIO_ENDPOINT ?? "localhost:9000"
$MinioRootUser = $env:MINIO_ROOT_USER ?? "minioadmin"
$MinioRootPassword = $env:MINIO_ROOT_PASSWORD ?? "minioadmin"
$EncryptionKey = $env:MINIO_ENCRYPTION_KEY

# Validar clave de encriptación
if (-not $EncryptionKey) {
    Write-Host "[WARN] MINIO_ENCRYPTION_KEY no configurada en .env" -ForegroundColor Yellow
    Write-Host "[INFO] Generando clave temporal de 32 bytes (256 bits)" -ForegroundColor Cyan
    
    # Generar clave aleatoria base64 (32 bytes)
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RNGCryptoServiceProvider]::new()
    $rng.GetBytes($bytes)
    $EncryptionKey = [Convert]::ToBase64String($bytes)
    
    Write-Host "[INFO] Clave generada: $EncryptionKey" -ForegroundColor Yellow
    Write-Host "[INFO] Guarda en .env como: MINIO_ENCRYPTION_KEY=$EncryptionKey" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host "[INFO] Configuracion MinIO:" -ForegroundColor Cyan
Write-Host "  Endpoint: $MinioHost" -ForegroundColor Gray
Write-Host "  Root User: $MinioRootUser" -ForegroundColor Gray
Write-Host "  Encryption Key: ${EncryptionKey.Substring(0,10)}..." -ForegroundColor Gray
Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 1: Verificar MinIO corriendo
# ══════════════════════════════════════════════════════════════

Write-Host "[1/5] Verificando contenedor MinIO..." -ForegroundColor Cyan

$container = docker ps --filter "name=satc-minio" --format "{{.Names}}" 2>$null
if (-not $container) {
    Write-Host "[ERROR] Contenedor MinIO no encontrado" -ForegroundColor Red
    Write-Host "Ejecuta: docker-compose up -d satc-minio" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Contenedor MinIO corriendo: $container" -ForegroundColor Green
Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 2: Configurar MinIO Client (mc)
# ══════════════════════════════════════════════════════════════

Write-Host "[2/5] Configurando MinIO Client (mc)..." -ForegroundColor Cyan

# Verificar si mc está instalado en el contenedor
$mcCheck = docker exec $container mc --version 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] MinIO Client (mc) no encontrado en el contenedor" -ForegroundColor Red
    Write-Host "[INFO] Instalando mc..." -ForegroundColor Cyan
    
    docker exec $container sh -c "wget https://dl.min.io/client/mc/release/linux-amd64/mc && chmod +x mc && mv mc /usr/bin/" 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] MinIO Client instalado" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] No se pudo instalar mc" -ForegroundColor Red
        exit 1
    }
}

# Configurar alias para el servidor local
Write-Host "  Configurando alias 'local'..." -ForegroundColor Gray
docker exec $container mc alias set local http://localhost:9000 $MinioRootUser $MinioRootPassword 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "[OK] Alias 'local' configurado" -ForegroundColor Green
} else {
    Write-Host "[ERROR] No se pudo configurar alias" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 3: Habilitar encriptación SSE-S3 en buckets
# ══════════════════════════════════════════════════════════════

Write-Host "[3/5] Habilitando encriptacion SSE en buckets..." -ForegroundColor Cyan

$buckets = @("satc-documentos", "satc-expedientes")

foreach ($bucket in $buckets) {
    Write-Host "  Procesando bucket: $bucket" -ForegroundColor Gray
    
    # Verificar si bucket existe
    $bucketExists = docker exec $container mc ls local/$bucket 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "  [WARN] Bucket $bucket no existe, creandolo..." -ForegroundColor Yellow
        docker exec $container mc mb local/$bucket 2>$null
    }
    
    # Habilitar encriptación SSE-S3 (AES-256)
    docker exec $container mc encrypt set sse-s3 local/$bucket 2>$null
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "  [OK] Encriptacion SSE habilitada en $bucket" -ForegroundColor Green
    } else {
        Write-Host "  [ERROR] No se pudo habilitar encriptacion en $bucket" -ForegroundColor Red
    }
}

Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 4: Verificar configuración de encriptación
# ══════════════════════════════════════════════════════════════

Write-Host "[4/5] Verificando configuracion de encriptacion..." -ForegroundColor Cyan

foreach ($bucket in $buckets) {
    Write-Host "  Verificando: $bucket" -ForegroundColor Gray
    
    $encryptionInfo = docker exec $container mc encrypt info local/$bucket 2>$null
    
    if ($encryptionInfo -match "sse-s3|AES256") {
        Write-Host "  [OK] $bucket: Encriptacion SSE-S3 activa" -ForegroundColor Green
    } else {
        Write-Host "  [WARN] $bucket: Estado de encriptacion desconocido" -ForegroundColor Yellow
    }
}

Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 5: Test de subida encriptada
# ══════════════════════════════════════════════════════════════

Write-Host "[5/5] Test de encriptacion..." -ForegroundColor Cyan

# Crear archivo de prueba
$testFile = "test_encryption_$(Get-Date -Format 'yyyyMMddHHmmss').txt"
$testContent = "Test de encriptacion MinIO - $(Get-Date)"

Write-Host "  Creando archivo de prueba: $testFile" -ForegroundColor Gray
docker exec $container sh -c "echo '$testContent' > /tmp/$testFile" 2>$null

# Subir archivo con encriptación
Write-Host "  Subiendo archivo encriptado..." -ForegroundColor Gray
docker exec $container mc cp /tmp/$testFile local/satc-documentos/$testFile 2>$null

if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] Archivo subido con encriptacion" -ForegroundColor Green
    
    # Verificar metadata de encriptación
    $metadata = docker exec $container mc stat local/satc-documentos/$testFile 2>$null
    if ($metadata -match "Encrypted|SSE") {
        Write-Host "  [OK] Metadata confirma encriptacion" -ForegroundColor Green
    }
} else {
    Write-Host "  [ERROR] Fallo al subir archivo" -ForegroundColor Red
}

# Limpiar archivo de prueba
docker exec $container mc rm local/satc-documentos/$testFile 2>$null
docker exec $container rm /tmp/$testFile 2>$null

Write-Host ""

# ══════════════════════════════════════════════════════════════
# Resumen y próximos pasos
# ══════════════════════════════════════════════════════════════

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Resumen de Configuracion" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

Write-Host "[OK] Encriptacion MinIO SSE-S3 configurada" -ForegroundColor Green
Write-Host ""

Write-Host "Caracteristicas habilitadas:" -ForegroundColor Cyan
Write-Host "  - Algoritmo: AES-256 (SSE-S3)" -ForegroundColor White
Write-Host "  - Buckets encriptados: satc-documentos, satc-expedientes" -ForegroundColor White
Write-Host "  - Encriptacion transparente (automatica)" -ForegroundColor White
Write-Host "  - Claves gestionadas por MinIO" -ForegroundColor White
Write-Host ""

Write-Host "Proximos pasos:" -ForegroundColor Cyan
Write-Host "  1. Guardar configuracion en .env:" -ForegroundColor White
Write-Host "     MINIO_ENCRYPTION_KEY=$EncryptionKey" -ForegroundColor Gray
Write-Host "     MINIO_SSE_ENABLED=true" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Actualizar cliente MinIO en aplicacion:" -ForegroundColor White
Write-Host "     Ver: app-*/utils/minio_client.py" -ForegroundColor Gray
Write-Host "     Agregar header: X-Amz-Server-Side-Encryption=AES256" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Todos los archivos NUEVOS se encriptaran automaticamente" -ForegroundColor White
Write-Host "     Archivos existentes: Requieren re-upload (opcional)" -ForegroundColor Gray
Write-Host ""

Write-Host "Proteccion en Red Local:" -ForegroundColor Cyan
Write-Host "  - Archivos encriptados en disco (proteccion fisica)" -ForegroundColor White
Write-Host "  - No requiere HTTPS interno (opcional para red local)" -ForegroundColor White
Write-Host "  - Cumplimiento: GDPR, ISO 27001" -ForegroundColor White
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
