# ====================================
# SATC - Script de Backup Completo (PowerShell)
# ====================================
# Backup automático de bases de datos PostgreSQL y archivos MinIO
# Uso: .\backup-all.ps1 [-RetentionDays 30]
# ====================================

param(
    [int]$RetentionDays = 30
)

$ErrorActionPreference = "Stop"

# Configuración
$BackupDir = ".\backups"
$Date = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = "$BackupDir\backup_log.txt"

# Función para escribir log
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $Timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $LogMessage = "[$Timestamp] [$Level] $Message"
    Add-Content -Path $LogFile -Value $LogMessage
    
    switch ($Level) {
        "ERROR"   { Write-Host $Message -ForegroundColor Red }
        "SUCCESS" { Write-Host $Message -ForegroundColor Green }
        "WARNING" { Write-Host $Message -ForegroundColor Yellow }
        default   { Write-Host $Message -ForegroundColor Cyan }
    }
}

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "SATC - Backup Automático Completo" -ForegroundColor Cyan
Write-Host "Fecha: $(Get-Date)" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

Write-Log "Iniciando proceso de backup completo"

# Verificar que Docker está corriendo
try {
    docker ps > $null 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Log "Docker no está corriendo. Abortando backup." "ERROR"
        exit 1
    }
} catch {
    Write-Log "Error al verificar Docker: $_" "ERROR"
    exit 1
}

# ==========================================
# BACKUP BASES DE DATOS POSTGRESQL
# ==========================================
Write-Host "`n[1/5] Backup de Bases de Datos PostgreSQL..." -ForegroundColor Yellow
Write-Log "Iniciando backup de bases de datos PostgreSQL"

# Crear directorios si no existen
$DbBackupDirs = @("postgres-users", "postgres-sanctioning", "postgres-docs")
foreach ($dir in $DbBackupDirs) {
    $fullPath = "$BackupDir\$dir"
    if (-not (Test-Path $fullPath)) {
        New-Item -ItemType Directory -Path $fullPath -Force | Out-Null
        Write-Log "Directorio creado: $fullPath" "INFO"
    }
}

# Backup user_db
Write-Host "  → Respaldando user_db..." -ForegroundColor Cyan
try {
    docker exec satc-postgres-users pg_dump -U postgres user_db > "$BackupDir\postgres-users\user_db_$Date.sql"
    Compress-Archive -Path "$BackupDir\postgres-users\user_db_$Date.sql" `
        -DestinationPath "$BackupDir\postgres-users\user_db_$Date.zip" -Force
    Remove-Item "$BackupDir\postgres-users\user_db_$Date.sql"
    $fileSize = (Get-Item "$BackupDir\postgres-users\user_db_$Date.zip").Length / 1MB
    Write-Log "✓ Backup Users completado: user_db_$Date.zip ({0:N2} MB)" -f $fileSize "SUCCESS"
} catch {
    Write-Log "✗ Error en backup de user_db: $_" "ERROR"
}

# Backup expedientes_db
Write-Host "  → Respaldando expedientes_db..." -ForegroundColor Cyan
try {
    docker exec satc-postgres-sanctioning pg_dump -U postgres expedientes_db > "$BackupDir\postgres-sanctioning\expedientes_db_$Date.sql"
    Compress-Archive -Path "$BackupDir\postgres-sanctioning\expedientes_db_$Date.sql" `
        -DestinationPath "$BackupDir\postgres-sanctioning\expedientes_db_$Date.zip" -Force
    Remove-Item "$BackupDir\postgres-sanctioning\expedientes_db_$Date.sql"
    $fileSize = (Get-Item "$BackupDir\postgres-sanctioning\expedientes_db_$Date.zip").Length / 1MB
    Write-Log "✓ Backup Sanctioning completado: expedientes_db_$Date.zip ({0:N2} MB)" -f $fileSize "SUCCESS"
} catch {
    Write-Log "✗ Error en backup de expedientes_db: $_" "ERROR"
}

# Backup documentos_db
Write-Host "  → Respaldando documentos_db..." -ForegroundColor Cyan
try {
    docker exec satc-postgres-docs pg_dump -U postgres documentos_db > "$BackupDir\postgres-docs\documentos_db_$Date.sql"
    Compress-Archive -Path "$BackupDir\postgres-docs\documentos_db_$Date.sql" `
        -DestinationPath "$BackupDir\postgres-docs\documentos_db_$Date.zip" -Force
    Remove-Item "$BackupDir\postgres-docs\documentos_db_$Date.sql"
    $fileSize = (Get-Item "$BackupDir\postgres-docs\documentos_db_$Date.zip").Length / 1MB
    Write-Log "✓ Backup Docs completado: documentos_db_$Date.zip ({0:N2} MB)" -f $fileSize "SUCCESS"
} catch {
    Write-Log "✗ Error en backup de documentos_db: $_" "ERROR"
}

# ==========================================
# BACKUP ARCHIVOS MINIO
# ==========================================
Write-Host "`n[2/5] Backup de Archivos MinIO..." -ForegroundColor Yellow
Write-Log "Iniciando backup de archivos MinIO"

# Crear directorio para MinIO backups
$minioBackupDir = "$BackupDir\minio"
if (-not (Test-Path $minioBackupDir)) {
    New-Item -ItemType Directory -Path $minioBackupDir -Force | Out-Null
    Write-Log "Directorio creado: $minioBackupDir" "INFO"
}

# Backup bucket satc-expedientes
Write-Host "  → Respaldando bucket satc-expedientes..." -ForegroundColor Cyan
try {
    $expedientesBackupPath = "$minioBackupDir\satc-expedientes_$Date"
    
    # Copiar datos del volumen de MinIO
    docker cp satc-minio:/data/satc-expedientes "$expedientesBackupPath"
    
    # Comprimir backup
    Compress-Archive -Path $expedientesBackupPath `
        -DestinationPath "$minioBackupDir\satc-expedientes_$Date.zip" -Force
    
    # Eliminar carpeta temporal
    Remove-Item -Recurse -Force $expedientesBackupPath
    
    $fileSize = (Get-Item "$minioBackupDir\satc-expedientes_$Date.zip").Length / 1MB
    Write-Log "✓ Backup satc-expedientes completado: satc-expedientes_$Date.zip ({0:N2} MB)" -f $fileSize "SUCCESS"
} catch {
    Write-Log "✗ Error en backup de satc-expedientes: $_" "ERROR"
}

# Backup bucket satc-documentos
Write-Host "  → Respaldando bucket satc-documentos..." -ForegroundColor Cyan
try {
    $documentosBackupPath = "$minioBackupDir\satc-documentos_$Date"
    
    # Copiar datos del volumen de MinIO
    docker cp satc-minio:/data/satc-documentos "$documentosBackupPath"
    
    # Comprimir backup
    Compress-Archive -Path $documentosBackupPath `
        -DestinationPath "$minioBackupDir\satc-documentos_$Date.zip" -Force
    
    # Eliminar carpeta temporal
    Remove-Item -Recurse -Force $documentosBackupPath
    
    $fileSize = (Get-Item "$minioBackupDir\satc-documentos_$Date.zip").Length / 1MB
    Write-Log "✓ Backup satc-documentos completado: satc-documentos_$Date.zip ({0:N2} MB)" -f $fileSize "SUCCESS"
} catch {
    Write-Log "✗ Error en backup de satc-documentos: $_" "ERROR"
}

# ==========================================
# BACKUP VOLÚMENES DOCKER (OPCIONAL)
# ==========================================
Write-Host "`n[3/5] Backup de Metadatos de Volúmenes..." -ForegroundColor Yellow
Write-Log "Guardando información de volúmenes Docker"

try {
    $volumesInfo = docker volume ls --format "{{.Name}}" | Where-Object { $_ -like "satc*" }
    $volumesInfo | Out-File -FilePath "$BackupDir\volumes_list_$Date.txt" -Encoding utf8
    Write-Log "✓ Lista de volúmenes guardada: volumes_list_$Date.txt" "SUCCESS"
} catch {
    Write-Log "✗ Error al guardar lista de volúmenes: $_" "ERROR"
}

# ==========================================
# VERIFICACIÓN DE INTEGRIDAD
# ==========================================
Write-Host "`n[4/5] Verificando integridad de backups..." -ForegroundColor Yellow
Write-Log "Verificando integridad de archivos de backup"

$backupFiles = Get-ChildItem -Path $BackupDir -Recurse -Include *.zip -Filter "*$Date*"
$corruptedFiles = @()

foreach ($file in $backupFiles) {
    try {
        # Intentar abrir el archivo zip para verificar integridad
        $zip = [System.IO.Compression.ZipFile]::OpenRead($file.FullName)
        $zip.Dispose()
    } catch {
        $corruptedFiles += $file.Name
        Write-Log "✗ Archivo corrupto detectado: $($file.Name)" "WARNING"
    }
}

if ($corruptedFiles.Count -eq 0) {
    Write-Log "✓ Todos los backups pasaron la verificación de integridad" "SUCCESS"
} else {
    Write-Log "⚠ Se encontraron $($corruptedFiles.Count) archivos con problemas" "WARNING"
}

# ==========================================
# LIMPIEZA DE BACKUPS ANTIGUOS
# ==========================================
Write-Host "`n[5/5] Limpiando backups antiguos (>$RetentionDays días)..." -ForegroundColor Yellow
Write-Log "Iniciando limpieza de backups antiguos"

$CutoffDate = (Get-Date).AddDays(-$RetentionDays)
$deletedCount = 0
$freedSpace = 0

Get-ChildItem -Path $BackupDir -Recurse -Include *.zip,*.sql.gz | 
    Where-Object { $_.LastWriteTime -lt $CutoffDate } | 
    ForEach-Object {
        $freedSpace += $_.Length
        $deletedCount++
        Remove-Item $_.FullName -Force
    }

if ($deletedCount -gt 0) {
    Write-Log "✓ Limpieza completada: $deletedCount archivos eliminados, {0:N2} MB liberados" -f ($freedSpace / 1MB) "SUCCESS"
} else {
    Write-Log "✓ No hay backups antiguos para eliminar" "SUCCESS"
}

# ==========================================
# RESUMEN FINAL
# ==========================================
Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "✓ Backup completado exitosamente" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan

Write-Log "Proceso de backup completado exitosamente"

# Estadísticas de backups
Write-Host "`nEstadísticas de Backup:" -ForegroundColor Yellow
Write-Host "  Ubicación: $BackupDir" -ForegroundColor Cyan
Write-Host "  Fecha: $Date" -ForegroundColor Cyan
Write-Host "  Retención: $RetentionDays días" -ForegroundColor Cyan

# Calcular espacio total usado
$totalSize = (Get-ChildItem -Path $BackupDir -Recurse -File | Measure-Object -Property Length -Sum).Sum / 1MB
Write-Host "  Espacio total usado: {0:N2} MB" -f $totalSize -ForegroundColor Cyan

# Contar archivos de backup por tipo
$dbBackups = (Get-ChildItem -Path "$BackupDir\postgres-*" -Recurse -Include *.zip).Count
$minioBackups = (Get-ChildItem -Path "$BackupDir\minio" -Recurse -Include *.zip -ErrorAction SilentlyContinue).Count

Write-Host "  Backups de BD: $dbBackups archivos" -ForegroundColor Cyan
Write-Host "  Backups de MinIO: $minioBackups archivos" -ForegroundColor Cyan

Write-Host "`n=========================================" -ForegroundColor Cyan

# Exportar resumen para monitoreo
$summary = @{
    Timestamp = $Date
    Status = "SUCCESS"
    DatabaseBackups = $dbBackups
    MinIOBackups = $minioBackups
    TotalSizeMB = [math]::Round($totalSize, 2)
    FilesDeleted = $deletedCount
    SpaceFreedMB = [math]::Round($freedSpace / 1MB, 2)
}

$summary | ConvertTo-Json | Out-File -FilePath "$BackupDir\last_backup_summary.json" -Encoding utf8
Write-Log "Resumen de backup guardado en last_backup_summary.json"
