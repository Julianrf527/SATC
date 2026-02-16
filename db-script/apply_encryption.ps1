# ══════════════════════════════════════════════════════════════
# Script: Aplicar Encriptación de Bases de Datos PostgreSQL
# Propósito: Habilitar pgcrypto y encriptar datos sensibles
# ══════════════════════════════════════════════════════════════

param(
    [string]$PostgresPassword = $env:POSTGRES_PASSWORD,
    [string]$EncryptionKey = $env:ENCRYPTION_KEY,
    [switch]$DryRun = $false
)

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Aplicar Encriptacion PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Validar parámetros
if (-not $PostgresPassword) {
    Write-Host "[ERROR] POSTGRES_PASSWORD no configurado" -ForegroundColor Red
    Write-Host "Usa: `$env:POSTGRES_PASSWORD='tu_password' o pasa -PostgresPassword" -ForegroundColor Yellow
    exit 1
}

if (-not $EncryptionKey) {
    Write-Host "[WARN] ENCRYPTIONKEY no configurado" -ForegroundColor Yellow
    Write-Host "Generando clave temporal (NO usar en producción)" -ForegroundColor Yellow
    $EncryptionKey = -join ((65..90) + (97..122) + (48..57) | Get-Random -Count 32 | ForEach-Object {[char]$_})
    Write-Host "[INFO] Clave generada: $EncryptionKey" -ForegroundColor Yellow
    Write-Host "[INFO] Guarda esta clave en .env como ENCRYPTION_KEY=$EncryptionKey" -ForegroundColor Yellow
}

# Configuración
$PostgresHost = $env:POSTGRES_HOST ?? "localhost"
$PostgresPort = $env:POSTGRES_PORT ?? "5432"
$PostgresUser = $env:POSTGRES_USER ?? "postgres"

Write-Host "[INFO] Configuracion:" -ForegroundColor Cyan
Write-Host "  Host: $PostgresHost" -ForegroundColor Gray
Write-Host "  Port: $PostgresPort" -ForegroundColor Gray
Write-Host "  User: $PostgresUser" -ForegroundColor Gray
Write-Host "  Encryption Key: ${EncryptionKey.Substring(0,8)}..." -ForegroundColor Gray
Write-Host ""

if ($DryRun) {
    Write-Host "[DRYRUN] Modo simulacion activado" -ForegroundColor Yellow
    Write-Host ""
}

# Función auxiliar para ejecutar SQL
function Invoke-PostgreSQL {
    param(
        [string]$Database,
        [string]$Command
    )
    
    $env:PGPASSWORD = $PostgresPassword
    
    if ($DryRun) {
        Write-Host "[DRYRUN] Ejecutaria en $Database" -ForegroundColor Yellow
        Write-Host $Command -ForegroundColor DarkGray
        return $true
    }
    
    try {
        $result = docker exec satc-postgres-users psql -U $PostgresUser -d $Database -c $Command 2>&1
        if ($LASTEXITCODE -ne 0) {
            Write-Host "[ERROR] $result" -ForegroundColor Red
            return $false
        }
        return $true
    } catch {
        Write-Host "[ERROR] $_" -ForegroundColor Red
        return $false
    }
}

# ══════════════════════════════════════════════════════════════
# PASO 1: Verificar contenedor PostgreSQL corriendo
# ══════════════════════════════════════════════════════════════

Write-Host "[1/6] Verificando contenedor PostgreSQL..." -ForegroundColor Cyan

$container = docker ps --filter "name=satc-postgres" --format "{{.Names}}" 2>$null
if (-not $container) {
    Write-Host "[ERROR] Contenedor PostgreSQL no encontrado" -ForegroundColor Red
    Write-Host "Ejecuta: docker-compose up -d satc-postgres-users" -ForegroundColor Yellow
    exit 1
}

Write-Host "[OK] Contenedor PostgreSQL corriendo: $container" -ForegroundColor Green
Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 2: Habilitar extensión pgcrypto en cada base de datos
# ══════════════════════════════════════════════════════════════

Write-Host "[2/6] Habilitando extension pgcrypto..." -ForegroundColor Cyan

$databases = @("user_db", "expedientes_db", "documentos_db")
$successCount = 0

foreach ($db in $databases) {
    Write-Host "  Procesando: $db..." -ForegroundColor Gray
    
    $result = Invoke-PostgreSQL -Database $db -Command "CREATE EXTENSION IF NOT EXISTS pgcrypto;"
    
    if ($result) {
        Write-Host "  [OK] pgcrypto habilitado en $db" -ForegroundColor Green
        $successCount++
    } else {
        Write-Host "  [ERROR] Fallo en $db" -ForegroundColor Red
    }
}

Write-Host ""
Write-Host "[INFO] Extensiones habilitadas: $successCount/$($databases.Count)" -ForegroundColor Cyan
Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 3: Aplicar script de migración SQL
# ══════════════════════════════════════════════════════════════

Write-Host "[3/6] Aplicando script de migracion SQL..." -ForegroundColor Cyan

$sqlFile = "db-script/enable_encryption.sql"

if (-not (Test-Path $sqlFile)) {
    Write-Host "[ERROR] Archivo $sqlFile no encontrado" -ForegroundColor Red
    exit 1
}

if (-not $DryRun) {
    Write-Host "  Ejecutando: $sqlFile" -ForegroundColor Gray
    
    $env:PGPASSWORD = $PostgresPassword
    docker exec -i satc-postgres-users psql -U $PostgresUser < $sqlFile
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host "[OK] Script de migracion aplicado" -ForegroundColor Green
    } else {
        Write-Host "[WARN] Script ejecutado con advertencias" -ForegroundColor Yellow
    }
} else {
    Write-Host "[DRYRUN] Saltando ejecucion de $sqlFile" -ForegroundColor Yellow
}

Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 4: Verificar instalación
# ══════════════════════════════════════════════════════════════

Write-Host "[4/6] Verificando instalacion..." -ForegroundColor Cyan

# Test básico de encriptación
$testSQL = @"
DO `$`$
DECLARE
    test_text TEXT := 'Test de encriptacion';
    test_key TEXT := '$EncryptionKey';
    encrypted bytea;
    decrypted TEXT;
BEGIN
    encrypted := pgp_sym_encrypt(test_text, test_key);
    decrypted := pgp_sym_decrypt(encrypted, test_key);
    
    IF decrypted = test_text THEN
        RAISE NOTICE 'Test: EXITOSO';
    ELSE
        RAISE EXCEPTION 'Test: FALLIDO';
    END IF;
END `$`$;
"@

if (-not $DryRun) {
    $result = Invoke-PostgreSQL -Database "user_db" -Command $testSQL
    
    if ($result) {
        Write-Host "[OK] Test de encriptacion exitoso" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] Test de encriptacion fallido" -ForegroundColor Red
    }
} else {
    Write-Host "[DRYRUN] Saltando test de encriptacion" -ForegroundColor Yellow
}

Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 5: Mostrar estado de columnas encriptadas
# ══════════════════════════════════════════════════════════════

Write-Host "[5/6] Estado de columnas encriptadas:" -ForegroundColor Cyan

$checkColumnsSQL = @"
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'usuarios' 
AND column_name LIKE '%encrypted%'
ORDER BY column_name;
"@

if (-not $DryRun) {
    Write-Host ""
    docker exec satc-postgres-users psql -U $PostgresUser -d user_db -c $checkColumnsSQL
} else {
    Write-Host "[DRYRUN] Listaria columnas encriptadas" -ForegroundColor Yellow
}

Write-Host ""

# ══════════════════════════════════════════════════════════════
# PASO 6: Resumen y próximos pasos
# ══════════════════════════════════════════════════════════════

Write-Host "[6/6] Resumen" -ForegroundColor Cyan
Write-Host ""

if ($DryRun) {
    Write-Host "[INFO] Esta fue una simulacion (--DryRun)" -ForegroundColor Yellow
    Write-Host "[INFO] Ejecuta sin -DryRun para aplicar cambios" -ForegroundColor Yellow
} else {
    Write-Host "[OK] Encriptacion habilitada en PostgreSQL" -ForegroundColor Green
}

Write-Host ""
Write-Host "Proximos pasos:" -ForegroundColor Cyan
Write-Host "  1. Guardar ENCRYPTION_KEY en .env:" -ForegroundColor White
Write-Host "     ENCRYPTION_KEY=$EncryptionKey" -ForegroundColor Gray
Write-Host ""
Write-Host "  2. Migrar datos existentes (MANUAL):" -ForegroundColor White
Write-Host "     Editar db-script/enable_encryption.sql" -ForegroundColor Gray
Write-Host "     Descomentar seccion 'MIGRACION DE DATOS EXISTENTES'" -ForegroundColor Gray
Write-Host "     Reemplazar 'TU_CLAVE_SECRETA_256_BITS' con ENCRYPTION_KEY" -ForegroundColor Gray
Write-Host ""
Write-Host "  3. Actualizar modelos Python para usar encriptacion:" -ForegroundColor White
Write-Host "     Ver: app-users/db/models/usuario.py" -ForegroundColor Gray
Write-Host ""
Write-Host "  4. Rebuild contenedores:" -ForegroundColor White
Write-Host "     docker-compose build app-users" -ForegroundColor Gray
Write-Host "     docker-compose up -d" -ForegroundColor Gray
Write-Host ""

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Para red local: Encriptacion protege contra acceso fisico no autorizado" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan
