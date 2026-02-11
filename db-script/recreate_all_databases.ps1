# Script PowerShell para recrear todas las bases de datos del sistema SATC
# Asegúrate de tener psql en tu PATH o ajusta la ruta completa

# Configuración
$PG_HOST = "localhost"
$PG_PORT = "5432"
$PG_USER = "postgres"
$SCRIPT_DIR = $PSScriptRoot

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "SATC - Recreacion de Bases de Datos" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Buscar psql en ubicaciones comunes
$psqlPath = $null

# Primero verificar si está en el PATH
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source

# Si no está en el PATH, buscar en ubicaciones comunes de PostgreSQL
if (-not $psqlPath) {
    Write-Host "Buscando PostgreSQL..." -ForegroundColor Yellow
    
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL\17\bin\psql.exe",
        "C:\Program Files\PostgreSQL\16\bin\psql.exe",
        "C:\Program Files\PostgreSQL\15\bin\psql.exe",
        "C:\Program Files\PostgreSQL\14\bin\psql.exe",
        "C:\Program Files\PostgreSQL\13\bin\psql.exe",
        "C:\Program Files\PostgreSQL\12\bin\psql.exe",
        "C:\Program Files (x86)\PostgreSQL\17\bin\psql.exe",
        "C:\Program Files (x86)\PostgreSQL\16\bin\psql.exe",
        "C:\Program Files (x86)\PostgreSQL\15\bin\psql.exe",
        "C:\Program Files (x86)\PostgreSQL\14\bin\psql.exe",
        "C:\Program Files (x86)\PostgreSQL\13\bin\psql.exe",
        "C:\Program Files (x86)\PostgreSQL\12\bin\psql.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $psqlPath = $path
            Write-Host "PostgreSQL encontrado en: $psqlPath" -ForegroundColor Green
            break
        }
    }
}

if (-not $psqlPath) {
    Write-Host "ERROR: No se encontro psql.exe" -ForegroundColor Red
    Write-Host ""
    Write-Host "Por favor, instale PostgreSQL o agregue psql al PATH del sistema." -ForegroundColor Yellow
    Write-Host "Ubicaciones tipicas de instalacion:" -ForegroundColor Yellow
    Write-Host "  - C:\Program Files\PostgreSQL\[version]\bin\" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "O ejecute este comando para agregar PostgreSQL al PATH:" -ForegroundColor Yellow
    Write-Host '  $env:Path += ";C:\Program Files\PostgreSQL\[version]\bin"' -ForegroundColor Cyan
    Write-Host ""
    exit 1
}

Write-Host ""

# Solicitar contraseña
$PG_PASSWORD = Read-Host "Ingrese la contrasena de PostgreSQL para el usuario '$PG_USER'" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($PG_PASSWORD)
$PG_PASSWORD_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)

# Configurar variable de entorno para la contraseña
$env:PGPASSWORD = $PG_PASSWORD_PLAIN

Write-Host ""
Write-Host "Paso 1: Eliminando y recreando bases de datos..." -ForegroundColor Yellow

# Ejecutar script de setup
$setupResult = & $psqlPath -h $PG_HOST -p $PG_PORT -U $PG_USER -d postgres -f "$SCRIPT_DIR\setup_databases.sql" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR al crear las bases de datos" -ForegroundColor Red
    Write-Host ""
    
    # Verificar si es un error de autenticación
    if ($setupResult -match "autentificaci[oó]n|authentication|password") {
        Write-Host "ERROR DE AUTENTICACION:" -ForegroundColor Yellow
        Write-Host "  - Verifique que la contrasena del usuario 'postgres' sea correcta" -ForegroundColor Yellow
        Write-Host "  - La contrasena se configuro durante la instalacion de PostgreSQL" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "Si olvido la contrasena, puede:" -ForegroundColor Cyan
        Write-Host "  1. Editar C:\Program Files\PostgreSQL\17\data\pg_hba.conf" -ForegroundColor White
        Write-Host "  2. Cambiar 'md5' o 'scram-sha-256' por 'trust' en las lineas de localhost" -ForegroundColor White
        Write-Host "  3. Reiniciar el servicio: Restart-Service postgresql-x64-17" -ForegroundColor White
        Write-Host "  4. Ejecutar este script sin contrasena" -ForegroundColor White
        Write-Host "  5. Cambiar la contrasena con: ALTER USER postgres PASSWORD 'nueva_contrasena';" -ForegroundColor White
        Write-Host "  6. Revertir pg_hba.conf a 'scram-sha-256' y reiniciar el servicio" -ForegroundColor White
        Write-Host ""
    } else {
        Write-Host $setupResult -ForegroundColor Red
    }
    
    $env:PGPASSWORD = $null
    exit 1
}

Write-Host "[OK] Bases de datos creadas exitosamente" -ForegroundColor Green
Write-Host ""

# Restaurar user_db
Write-Host "Paso 2: Restaurando user_db..." -ForegroundColor Yellow
$userDbResult = & $psqlPath -h $PG_HOST -p $PG_PORT -U $PG_USER -d user_db -f "$SCRIPT_DIR\user_db.sql" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR al restaurar user_db" -ForegroundColor Red
    Write-Host $userDbResult -ForegroundColor Red
    $env:PGPASSWORD = $null
    exit 1
}

Write-Host "[OK] user_db restaurada exitosamente" -ForegroundColor Green
Write-Host ""

# Restaurar expedientes_db
Write-Host "Paso 3: Restaurando expedientes_db..." -ForegroundColor Yellow
$expedientesDbResult = & $psqlPath -h $PG_HOST -p $PG_PORT -U $PG_USER -d expedientes_db -f "$SCRIPT_DIR\expedientes_db.sql" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR al restaurar expedientes_db" -ForegroundColor Red
    Write-Host $expedientesDbResult -ForegroundColor Red
    $env:PGPASSWORD = $null
    exit 1
}

Write-Host "[OK] expedientes_db restaurada exitosamente" -ForegroundColor Green
Write-Host ""

# Restaurar documentos_db
Write-Host "Paso 4: Restaurando documentos_db..." -ForegroundColor Yellow
$documentosDbResult = & $psqlPath -h $PG_HOST -p $PG_PORT -U $PG_USER -d documentos_db -f "$SCRIPT_DIR\documentos_db.sql" 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR al restaurar documentos_db" -ForegroundColor Red
    Write-Host $documentosDbResult -ForegroundColor Red
    $env:PGPASSWORD = $null
    exit 1
}

Write-Host "[OK] documentos_db restaurada exitosamente" -ForegroundColor Green
Write-Host ""

# Limpiar contraseña de la variable de entorno
$env:PGPASSWORD = $null

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "PROCESO COMPLETADO EXITOSAMENTE" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Las 3 bases de datos han sido recreadas:" -ForegroundColor White
Write-Host "  - user_db" -ForegroundColor White
Write-Host "  - expedientes_db" -ForegroundColor White
Write-Host "  - documentos_db" -ForegroundColor White
Write-Host ""
