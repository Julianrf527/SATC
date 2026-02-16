# ====================================
# SATC - Script de Restauración de Backups
# ====================================
# Restaura bases de datos PostgreSQL y archivos MinIO
# desde backups comprimidos
# ====================================
# Uso: .\restore-backup.ps1 -BackupDate "20260214_153000"
#      .\restore-backup.ps1 -BackupDate "20260214_153000" -RestoreDB -RestoreMinIO
# ====================================

param(
    [Parameter(Mandatory=$true)]
    [string]$BackupDate,
    
    [switch]$RestoreDB = $false,
    [switch]$RestoreMinIO = $false,
    [switch]$Force = $false
)

$ErrorActionPreference = "Stop"

$BackupDir = ".\backups"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "SATC - Restauración de Backups" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Si no se especifica qué restaurar, preguntar
if (-not $RestoreDB -and -not $RestoreMinIO) {
    Write-Host "`n¿Qué deseas restaurar?" -ForegroundColor Yellow
    Write-Host "1. Solo Bases de Datos" -ForegroundColor White
    Write-Host "2. Solo Archivos MinIO" -ForegroundColor White
    Write-Host "3. Todo (BD + MinIO)" -ForegroundColor White
    Write-Host "4. Cancelar" -ForegroundColor White
    
    $choice = Read-Host "`nSelecciona una opción (1-4)"
    
    switch ($choice) {
        "1" { $RestoreDB = $true }
        "2" { $RestoreMinIO = $true }
        "3" { 
            $RestoreDB = $true
            $RestoreMinIO = $true
        }
        "4" { 
            Write-Host "Operación cancelada" -ForegroundColor Yellow
            exit 0
        }
        default {
            Write-Host "Opción inválida" -ForegroundColor Red
            exit 1
        }
    }
}

# Validar que Docker está corriendo
try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Host "✗ Docker no está corriendo. Abortando restauración." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "✗ Error al verificar Docker: $_" -ForegroundColor Red
    exit 1
}

# Advertencia
if (-not $Force) {
    Write-Host "`n⚠ ADVERTENCIA: Esta operación sobrescribirá los datos actuales." -ForegroundColor Yellow
    Write-Host "¿Estás seguro de continuar? (S/N): " -ForegroundColor Yellow -NoNewline
    $confirm = Read-Host
    
    if ($confirm -notmatch "^[Ss]$") {
        Write-Host "Operación cancelada por el usuario" -ForegroundColor Yellow
        exit 0
    }
}

$successCount = 0
$failCount = 0

# ==========================================
# RESTAURAR BASES DE DATOS
# ==========================================
if ($RestoreDB) {
    Write-Host "`n[1/2] Restaurando Bases de Datos..." -ForegroundColor Yellow
    
    # Restaurar user_db
    $userDbBackup = "$BackupDir\postgres-users\user_db_$BackupDate.zip"
    if (Test-Path $userDbBackup) {
        Write-Host "  → Restaurando user_db..." -ForegroundColor Cyan
        try {
            # Descomprimir
            Expand-Archive -Path $userDbBackup -DestinationPath "$BackupDir\temp" -Force
            
            # Eliminar base de datos actual
            docker exec satc-postgres-users psql -U postgres -c "DROP DATABASE IF EXISTS user_db;"
            docker exec satc-postgres-users psql -U postgres -c "CREATE DATABASE user_db;"
            
            # Restaurar desde backup
            Get-Content "$BackupDir\temp\user_db_$BackupDate.sql" | docker exec -i satc-postgres-users psql -U postgres -d user_db
            
            # Limpiar temporal
            Remove-Item -Recurse -Force "$BackupDir\temp"
            
            Write-Host "  ✓ user_db restaurada exitosamente" -ForegroundColor Green
            $successCount++
        } catch {
            Write-Host "  ✗ Error al restaurar user_db: $_" -ForegroundColor Red
            $failCount++
        }
    } else {
        Write-Host "  ✗ Backup no encontrado: $userDbBackup" -ForegroundColor Red
        $failCount++
    }
    
    # Restaurar expedientes_db
    $sanctioningDbBackup = "$BackupDir\postgres-sanctioning\expedientes_db_$BackupDate.zip"
    if (Test-Path $sanctioningDbBackup) {
        Write-Host "  → Restaurando expedientes_db..." -ForegroundColor Cyan
        try {
            Expand-Archive -Path $sanctioningDbBackup -DestinationPath "$BackupDir\temp" -Force
            
            docker exec satc-postgres-sanctioning psql -U postgres -c "DROP DATABASE IF EXISTS expedientes_db;"
            docker exec satc-postgres-sanctioning psql -U postgres -c "CREATE DATABASE expedientes_db;"
            
            Get-Content "$BackupDir\temp\expedientes_db_$BackupDate.sql" | docker exec -i satc-postgres-sanctioning psql -U postgres -d expedientes_db
            
            Remove-Item -Recurse -Force "$BackupDir\temp"
            
            Write-Host "  ✓ expedientes_db restaurada exitosamente" -ForegroundColor Green
            $successCount++
        } catch {
            Write-Host "  ✗ Error al restaurar expedientes_db: $_" -ForegroundColor Red
            $failCount++
        }
    } else {
        Write-Host "  ✗ Backup no encontrado: $sanctioningDbBackup" -ForegroundColor Red
        $failCount++
    }
    
    # Restaurar documentos_db
    $docsDbBackup = "$BackupDir\postgres-docs\documentos_db_$BackupDate.zip"
    if (Test-Path $docsDbBackup) {
        Write-Host "  → Restaurando documentos_db..." -ForegroundColor Cyan
        try {
            Expand-Archive -Path $docsDbBackup -DestinationPath "$BackupDir\temp" -Force
            
            docker exec satc-postgres-docs psql -U postgres -c "DROP DATABASE IF EXISTS documentos_db;"
            docker exec satc-postgres-docs psql -U postgres -c "CREATE DATABASE documentos_db;"
            
            Get-Content "$BackupDir\temp\documentos_db_$BackupDate.sql" | docker exec -i satc-postgres-docs psql -U postgres -d documentos_db
            
            Remove-Item -Recurse -Force "$BackupDir\temp"
            
            Write-Host "  ✓ documentos_db restaurada exitosamente" -ForegroundColor Green
            $successCount++
        } catch {
            Write-Host "  ✗ Error al restaurar documentos_db: $_" -ForegroundColor Red
            $failCount++
        }
    } else {
        Write-Host "  ✗ Backup no encontrado: $docsDbBackup" -ForegroundColor Red
        $failCount++
    }
}

# ==========================================
# RESTAURAR ARCHIVOS MINIO
# ==========================================
if ($RestoreMinIO) {
    Write-Host "`n[2/2] Restaurando Archivos MinIO..." -ForegroundColor Yellow
    
    # Restaurar satc-expedientes
    $expedientesBackup = "$BackupDir\minio\satc-expedientes_$BackupDate.zip"
    if (Test-Path $expedientesBackup) {
        Write-Host "  → Restaurando bucket satc-expedientes..." -ForegroundColor Cyan
        try {
            # Descomprimir
            Expand-Archive -Path $expedientesBackup -DestinationPath "$BackupDir\temp" -Force
            
            # Copiar archivos al contenedor
            docker cp "$BackupDir\temp\satc-expedientes_$BackupDate" satc-minio:/data/satc-expedientes
            
            # Limpiar
            Remove-Item -Recurse -Force "$BackupDir\temp"
            
            Write-Host "  ✓ satc-expedientes restaurado exitosamente" -ForegroundColor Green
            $successCount++
        } catch {
            Write-Host "  ✗ Error al restaurar satc-expedientes: $_" -ForegroundColor Red
            $failCount++
        }
    } else {
        Write-Host "  ✗ Backup no encontrado: $expedientesBackup" -ForegroundColor Red
        $failCount++
    }
    
    # Restaurar satc-documentos
    $documentosBackup = "$BackupDir\minio\satc-documentos_$BackupDate.zip"
    if (Test-Path $documentosBackup) {
        Write-Host "  → Restaurando bucket satc-documentos..." -ForegroundColor Cyan
        try {
            Expand-Archive -Path $documentosBackup -DestinationPath "$BackupDir\temp" -Force
            
            docker cp "$BackupDir\temp\satc-documentos_$BackupDate" satc-minio:/data/satc-documentos
            
            Remove-Item -Recurse -Force "$BackupDir\temp"
            
            Write-Host "  ✓ satc-documentos restaurado exitosamente" -ForegroundColor Green
            $successCount++
        } catch {
            Write-Host "  ✗ Error al restaurar satc-documentos: $_" -ForegroundColor Red
            $failCount++
        }
    } else {
        Write-Host "  ✗ Backup no encontrado: $documentosBackup" -ForegroundColor Red
        $failCount++
    }
}

# ==========================================
# RESUMEN
# ==========================================
Write-Host "`n=========================================" -ForegroundColor Cyan
if ($failCount -eq 0) {
    Write-Host "✓ Restauración completada exitosamente" -ForegroundColor Green
    Write-Host "  Total restaurado: $successCount componentes" -ForegroundColor Cyan
} else {
    Write-Host "⚠ Restauración completada con errores" -ForegroundColor Yellow
    Write-Host "  Exitosos: $successCount" -ForegroundColor Green
    Write-Host "  Fallidos: $failCount" -ForegroundColor Red
}
Write-Host "=========================================" -ForegroundColor Cyan

# Reiniciar servicios si es necesario
if ($RestoreDB) {
    Write-Host "`n⚠ Se recomienda reiniciar los servicios de aplicación:" -ForegroundColor Yellow
    Write-Host "  docker restart satc-app-users-1 satc-app-users-2" -ForegroundColor Gray
    Write-Host "  docker restart satc-app-sanctioning satc-app-sanctioning-2" -ForegroundColor Gray
    Write-Host "  docker restart satc-app-docs" -ForegroundColor Gray
    
    Write-Host "`n¿Deseas reiniciar los servicios ahora? (S/N): " -ForegroundColor Yellow -NoNewline
    $restart = Read-Host
    
    if ($restart -match "^[Ss]$") {
        Write-Host "`nReiniciando servicios..." -ForegroundColor Cyan
        docker restart satc-app-users-1 satc-app-users-2 satc-app-sanctioning satc-app-sanctioning-2 satc-app-docs
        Write-Host "✓ Servicios reiniciados" -ForegroundColor Green
    }
}
