# Script para probar la conexion a PostgreSQL
# Util para verificar credenciales antes de ejecutar recreate_all_databases.ps1

$PG_HOST = "localhost"
$PG_PORT = "5432"
$PG_USER = "postgres"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "Test de Conexion PostgreSQL" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Buscar psql
$psqlPath = Get-Command psql -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Source

if (-not $psqlPath) {
    $possiblePaths = @(
        "C:\Program Files\PostgreSQL\17\bin\psql.exe",
        "C:\Program Files\PostgreSQL\16\bin\psql.exe",
        "C:\Program Files\PostgreSQL\15\bin\psql.exe"
    )
    
    foreach ($path in $possiblePaths) {
        if (Test-Path $path) {
            $psqlPath = $path
            break
        }
    }
}

if (-not $psqlPath) {
    Write-Host "ERROR: No se encontro psql.exe" -ForegroundColor Red
    exit 1
}

Write-Host "PostgreSQL encontrado en: $psqlPath" -ForegroundColor Green
Write-Host ""

# Solicitar contraseña
$PG_PASSWORD = Read-Host "Ingrese la contrasena de PostgreSQL para el usuario '$PG_USER'" -AsSecureString
$BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($PG_PASSWORD)
$PG_PASSWORD_PLAIN = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
$env:PGPASSWORD = $PG_PASSWORD_PLAIN

Write-Host ""
Write-Host "Probando conexion..." -ForegroundColor Yellow

# Probar conexión simple
$result = & $psqlPath -h $PG_HOST -p $PG_PORT -U $PG_USER -d postgres -c "SELECT version();" 2>&1

$env:PGPASSWORD = $null

if ($LASTEXITCODE -eq 0) {
    Write-Host ""
    Write-Host "CONEXION EXITOSA!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Version de PostgreSQL:" -ForegroundColor Cyan
    Write-Host $result -ForegroundColor White
    Write-Host ""
    Write-Host "Ahora puede ejecutar: .\recreate_all_databases.ps1" -ForegroundColor Cyan
} else {
    Write-Host ""
    Write-Host "ERROR DE CONEXION" -ForegroundColor Red
    Write-Host ""
    Write-Host $result -ForegroundColor Yellow
    Write-Host ""
    
    if ($result -match "autentificaci[oó]n|authentication|password") {
        Write-Host "SOLUCION:" -ForegroundColor Cyan
        Write-Host "1. Verifique la contrasena del usuario postgres" -ForegroundColor White
        Write-Host "2. O modifique temporalmente la autenticacion:" -ForegroundColor White
        Write-Host "   - Edite: C:\Program Files\PostgreSQL\17\data\pg_hba.conf" -ForegroundColor Yellow
        Write-Host "   - Cambie 'scram-sha-256' por 'trust' para localhost" -ForegroundColor Yellow
        Write-Host "   - Reinicie: Restart-Service postgresql-x64-17" -ForegroundColor Yellow
        Write-Host ""
    }
}
