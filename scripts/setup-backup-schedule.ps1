# ====================================
# SATC - Configuración de Backup Automático
# ====================================
# Este script configura una tarea programada de Windows
# para ejecutar backups cada hora
# ====================================
# Uso: Ejecutar como Administrador
#      .\setup-backup-schedule.ps1
# ====================================

#Requires -RunAsAdministrator

$ErrorActionPreference = "Stop"

Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "SATC - Configuración de Backup Automático" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

# Configuración
$TaskName = "SATC-Backup-Automatico"
$ScriptPath = Join-Path $PSScriptRoot "backup-all.ps1"
$WorkingDirectory = Split-Path $PSScriptRoot -Parent
$LogPath = Join-Path $WorkingDirectory "backups\scheduled_backup.log"

# Verificar que el script de backup existe
if (-not (Test-Path $ScriptPath)) {
    Write-Host "✗ Error: No se encuentra el script backup-all.ps1 en $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "`nConfigurando tarea programada..." -ForegroundColor Yellow
Write-Host "  Nombre: $TaskName" -ForegroundColor Cyan
Write-Host "  Script: $ScriptPath" -ForegroundColor Cyan
Write-Host "  Directorio: $WorkingDirectory" -ForegroundColor Cyan
Write-Host "  Frecuencia: Cada hora" -ForegroundColor Cyan

# Eliminar tarea existente si existe
$existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($existingTask) {
    Write-Host "`n⚠ Tarea existente encontrada. Eliminando..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Host "✓ Tarea anterior eliminada" -ForegroundColor Green
}

# Crear acción de la tarea
$Action = New-ScheduledTaskAction `
    -Execute "PowerShell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$ScriptPath`" -RetentionDays 30 >> `"$LogPath`" 2>&1" `
    -WorkingDirectory $WorkingDirectory

# Crear trigger (cada hora)
$Trigger = New-ScheduledTaskTrigger -Once -At (Get-Date) -RepetitionInterval (New-TimeSpan -Hours 1)

# Configuración adicional
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable:$false `
    -MultipleInstances IgnoreNew

# Configuración de usuario (SYSTEM para que corra sin login)
$Principal = New-ScheduledTaskPrincipal `
    -UserId "SYSTEM" `
    -LogonType ServiceAccount `
    -RunLevel Highest

# Descripción de la tarea
$Description = @"
SATC - Backup Automático Cada Hora
Respalda bases de datos PostgreSQL y archivos MinIO del sistema SATC.
Script: $ScriptPath
Retención: 30 días
Creado: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
"@

# Registrar tarea programada
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal `
        -Description $Description | Out-Null
    
    Write-Host "`n✓ Tarea programada creada exitosamente" -ForegroundColor Green
} catch {
    Write-Host "`n✗ Error al crear la tarea programada: $_" -ForegroundColor Red
    exit 1
}

# Verificar la tarea
$task = Get-ScheduledTask -TaskName $TaskName
if ($task.State -ne "Disabled") {
    Write-Host "✓ Tarea verificada y habilitada" -ForegroundColor Green
} else {
    Write-Host "⚠ Tarea creada pero está deshabilitada" -ForegroundColor Yellow
}

# Mostrar información de la tarea
Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "Información de la Tarea Programada:" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Nombre: $($task.TaskName)" -ForegroundColor White
Write-Host "  Estado: $($task.State)" -ForegroundColor White
Write-Host "  Próxima ejecución: $((Get-ScheduledTaskInfo -TaskName $TaskName).NextRunTime)" -ForegroundColor White
Write-Host "  Última ejecución: $((Get-ScheduledTaskInfo -TaskName $TaskName).LastRunTime)" -ForegroundColor White
Write-Host "  Última resultado: $((Get-ScheduledTaskInfo -TaskName $TaskName).LastTaskResult)" -ForegroundColor White

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "Comandos Útiles:" -ForegroundColor Yellow
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "  Ver estado:" -ForegroundColor White
Write-Host "    Get-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host ""
Write-Host "  Ejecutar manualmente:" -ForegroundColor White
Write-Host "    Start-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host ""
Write-Host "  Ver historial:" -ForegroundColor White
Write-Host "    Get-ScheduledTaskInfo -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host ""
Write-Host "  Deshabilitar:" -ForegroundColor White
Write-Host "    Disable-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host ""
Write-Host "  Eliminar:" -ForegroundColor White
Write-Host "    Unregister-ScheduledTask -TaskName '$TaskName'" -ForegroundColor Gray
Write-Host ""
Write-Host "  Ver logs:" -ForegroundColor White
Write-Host "    Get-Content '$LogPath' -Tail 50" -ForegroundColor Gray

Write-Host "`n=========================================" -ForegroundColor Cyan
Write-Host "✓ Configuración completada" -ForegroundColor Green
Write-Host "=========================================" -ForegroundColor Cyan

Write-Host "`n¿Deseas ejecutar un backup de prueba ahora? (S/N): " -ForegroundColor Yellow -NoNewline
$response = Read-Host

if ($response -match "^[Ss]$") {
    Write-Host "`nEjecutando backup de prueba..." -ForegroundColor Yellow
    Start-ScheduledTask -TaskName $TaskName
    Start-Sleep -Seconds 2
    
    # Esperar a que termine
    $timeout = 300  # 5 minutos
    $elapsed = 0
    while ((Get-ScheduledTask -TaskName $TaskName).State -eq "Running" -and $elapsed -lt $timeout) {
        Write-Host "." -NoNewline -ForegroundColor Cyan
        Start-Sleep -Seconds 5
        $elapsed += 5
    }
    
    Write-Host ""
    
    $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
    if ($taskInfo.LastTaskResult -eq 0) {
        Write-Host "✓ Backup de prueba completado exitosamente" -ForegroundColor Green
        Write-Host "  Ver logs en: $LogPath" -ForegroundColor Cyan
    } else {
        Write-Host "✗ El backup falló. Código: $($taskInfo.LastTaskResult)" -ForegroundColor Red
        Write-Host "  Revisa los logs en: $LogPath" -ForegroundColor Yellow
    }
}

Write-Host "`nPresiona Enter para salir..." -ForegroundColor Gray
Read-Host
