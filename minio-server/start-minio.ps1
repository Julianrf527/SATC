# Script para iniciar MinIO Server
Write-Host "Iniciando MinIO Server..." -ForegroundColor Cyan
Write-Host ""
Write-Host "Dashboard: http://localhost:9001" -ForegroundColor Green
Write-Host "API: http://localhost:9000" -ForegroundColor Green
Write-Host ""
Write-Host "Usuario: minioadmin" -ForegroundColor Yellow
Write-Host "Contraseña: minioadmin" -ForegroundColor Yellow
Write-Host ""
Write-Host "Presiona Ctrl+C para detener el servidor" -ForegroundColor Magenta
Write-Host ""

$env:MINIO_ROOT_USER = "minioadmin"
$env:MINIO_ROOT_PASSWORD = "minioadmin"

& "$PSScriptRoot\minio.exe" server "$PSScriptRoot\data" --console-address ":9001"
