# Sistema de Backups Automáticos SATC

Sistema completo de respaldo y restauración para bases de datos PostgreSQL y archivos MinIO del sistema SATC.

## 📋 Tabla de Contenidos

- [Características](#características)
- [Configuración Automática](#configuración-automática)
- [Componentes Respaldados](#componentes-respaldados)
- [Uso](#uso)
- [Monitoreo](#monitoreo)
- [Restauración](#restauración)
- [Troubleshooting](#troubleshooting)
- [Detalles Técnicos](#detalles-técnicos)

---

## 🎯 Características

- ✅ **Backups automáticos cada 30 minutos** (configurado en Docker)
- ✅ **Respaldo completo**: Bases de datos PostgreSQL
- ✅ **Compresión GZIP**: Reduce espacio en disco (90% ahorro)
- ✅ **Limpieza automática**: Elimina backups antiguos (30 días por defecto)
- ✅ **Logging detallado**: Auditoría completa de operaciones
- ✅ **Auto-inicio**: Se activa al ejecutar `docker-compose up`
- ✅ **Restauración simplificada**: Script interactivo
- ✅ **Sin configuración manual**: Funciona out-of-the-box

---

## ⚙️ Configuración Automática

### ✨ Backups automáticos activos desde el inicio

Al ejecutar `docker-compose up -d`, el servicio `satc-backup-service`:

1. ✅ Se inicia automáticamente (sin configuración adicional)
2. ✅ Ejecuta un backup inicial inmediatamente
3. ✅ Configura cron job para backups cada 30 minutos
4. ✅ Limpia backups antiguos (mayores a 30 días)
5. ✅ Registra todas las operaciones en logs

### 📅 Frecuencia

```
Cron: */30 * * * * (cada 30 minutos)

Ejemplo de ejecuciones:
- 10:00 AM
- 10:30 AM
- 11:00 AM
- 11:30 AM
... cada 30 minutos las 24 horas
```

### 🔄 Verificar que está funcionando

```powershell
# Ver si el servicio está corriendo
docker ps --filter "name=backup"

# Ver logs de backups
docker logs satc-backup-service

# Ver próximos backups programados
docker exec satc-backup-service cat /etc/crontabs/root

# Ver historial de backups ejecutados
docker exec satc-backup-service tail -50 /var/log/backup-cron.log
```

Si necesitas ejecutar un backup fuera del horario programado:

```powershell
# Desde la carpeta scripts
cd C:\Users\julia\Escritorio\SATC\scripts

# Ejecutar backup con retención de 30 días (default)
.\backup-all.ps1

# O especificar días de retención personalizados
.\backup-all.ps1 -RetentionDays 60
```

### Ver último backup

```powershell
# Ver resumen del último backup
Get-Content ..\backups\last_backup_summary.json | ConvertFrom-Json | Format-List

# Listar archivos de backup más recientes
Get-ChildItem ..\backups -Recurse -Include *.zip |
    Sort-Object LastWriteTime -Descending |
    Select-Object -First 10 |
    Format-Table Name, Length, LastWriteTime
```

---

## 📊 Monitoreo

### Logs detallados

```powershell
# Ver log de backups manuales
Get-Content ..\backups\backup_log.txt -Tail 100

# Ver log de backups automáticos
Get-Content ..\backups\scheduled_backup.log -Tail 100

# Filtrar solo errores
Get-Content ..\backups\backup_log.txt | Select-String "ERROR"
```

### Información de la tarea programada

```powershell
# Ver estado de la tarea
Get-ScheduledTaskInfo -TaskName "SATC-Backup-Automatico" | Format-List

# Ver última ejecución
Get-ScheduledTask -TaskName "SATC-Backup-Automatico" |
    Get-ScheduledTaskInfo |
    Select-Object LastRunTime, NextRunTime, LastTaskResult

# Ejecutar manualmente (sin esperar)
Start-ScheduledTask -TaskName "SATC-Backup-Automatico"
```

### Espacio en disco

```powershell
# Ver espacio usado por backups
Get-ChildItem ..\backups -Recurse |
    Measure-Object -Property Length -Sum |
    Select-Object @{Name="Total (GB)"; Expression={[math]::Round($_.Sum / 1GB, 2)}}

# Ver cantidad de archivos por tipo
Get-ChildItem ..\backups -Recurse -Include *.zip |
    Group-Object Directory |
    Select-Object Name, Count
```

---

## 🔄 Restauración

### Opción 1: Restauración Interactiva (Recomendado)

```powershell
# Listar backups disponibles
Get-ChildItem ..\backups\postgres-users\*.zip |
    Format-Table Name, LastWriteTime

# Restaurar desde fecha específica
.\restore-backup.ps1 -BackupDate "20260214_153000"

# El script preguntará qué restaurar:
# 1. Solo Bases de Datos
# 2. Solo Archivos MinIO
# 3. Todo (BD + MinIO)
# 4. Cancelar
```

### Opción 2: Restauración con parámetros

```powershell
# Solo bases de datos
.\restore-backup.ps1 -BackupDate "20260214_153000" -RestoreDB

# Solo archivos MinIO
.\restore-backup.ps1 -BackupDate "20260214_153000" -RestoreMinIO

# Todo sin confirmación (usar con precaución)
.\restore-backup.ps1 -BackupDate "20260214_153000" -RestoreDB -RestoreMinIO -Force
```

### ⚠️ Advertencias

1. **La restauración sobrescribe datos actuales** - No hay undo
2. **Docker debe estar corriendo** - Verifica antes de restaurar
3. **Se recomienda detener servicios** - Para evitar inconsistencias
4. **Reiniciar servicios después** - El script lo hará automáticamente

---

## 🔧 Troubleshooting

### Problema: Tarea programada no se ejecuta

**Diagnóstico:**

```powershell
Get-ScheduledTask -TaskName "SATC-Backup-Automatico" | Select-Object State
```

**Soluciones:**

```powershell
# Si está deshabilitada
Enable-ScheduledTask -TaskName "SATC-Backup-Automatico"

# Recrear tarea
.\setup-backup-schedule.ps1
```

### Problema: Backup falla con error de Docker

**Diagnóstico:**

```powershell
docker ps
Get-Content ..\backups\backup_log.txt -Tail 50 | Select-String "ERROR"
```

**Soluciones:**

1. Verificar que Docker Desktop está corriendo
2. Verificar que contenedores están healthy: `docker ps --format "table {{.Names}}\t{{.Status}}"`
3. Reiniciar contenedores específicos: `docker restart satc-postgres-users satc-minio`

### Problema: Espacio en disco insuficiente

**Diagnóstico:**

```powershell
# Ver espacio disponible en disco C:
Get-PSDrive C | Select-Object Used, Free, @{Name="Free (GB)"; Expression={[math]::Round($_.Free / 1GB, 2)}}

# Ver espacio usado por backups
Get-ChildItem ..\backups -Recurse | Measure-Object -Property Length -Sum
```

**Soluciones:**

```powershell
# Reducir retención de backups
.\backup-all.ps1 -RetentionDays 15

# Limpiar backups antiguos manualmente
Get-ChildItem ..\backups -Recurse -Include *.zip |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
    Remove-Item -Force
```

### Problema: Backup corrupto

**Diagnóstico:**

```powershell
# Verificar integridad de un backup específico
$file = Get-Item ..\backups\postgres-users\user_db_20260214_153000.zip
[System.IO.Compression.ZipFile]::OpenRead($file.FullName).Dispose()
```

**Soluciones:**

1. Usar un backup anterior (retención de 30 días)
2. Ejecutar backup manual inmediatamente
3. Revisar logs para identificar causa: `Get-Content ..\backups\backup_log.txt | Select-String "user_db"`

### Problema: Restauración falla

**Diagnóstico:**

```powershell
# Verificar que archivo de backup existe
Test-Path ..\backups\postgres-users\user_db_20260214_153000.zip

# Verificar que contenedor está corriendo
docker ps --filter "name=satc-postgres-users"
```

**Soluciones:**

1. Verificar formato de fecha: `YYYYMMDD_HHMMSS`
2. Usar ruta completa al archivo
3. Verificar permisos de escritura en carpeta temp

---

## 📚 Detalles Técnicos

### Estructura de archivos

```
backups/
├── postgres-users/
│   └── user_db_YYYYMMDD_HHMMSS.zip
├── postgres-sanctioning/
│   └── expedientes_db_YYYYMMDD_HHMMSS.zip
├── postgres-docs/
│   └── documentos_db_YYYYMMDD_HHMMSS.zip
├── minio/
│   ├── satc-expedientes_YYYYMMDD_HHMMSS.zip
│   └── satc-documentos_YYYYMMDD_HHMMSS.zip
├── backup_log.txt                  (log de backups manuales)
├── scheduled_backup.log            (log de backups automáticos)
└── last_backup_summary.json        (resumen del último backup)
```

### Formato de backup PostgreSQL

- Método: `pg_dump` con formato SQL plano
- Encoding: UTF-8
- Incluye: Esquema + Datos + Índices
- Exclusiones: Ninguna (backup completo)

### Formato de backup MinIO

- Método: `docker cp` de volumen completo
- Estructura: Preserva jerarquía de carpetas
- Metadatos: Incluidos (permisos, timestamps)
- Compresión: ZIP estándar

### Rendimiento

**Tiempo estimado por backup completo:**

- 3 bases de datos PostgreSQL: ~30-60 segundos
- 2 buckets MinIO (depende de tamaño): ~1-5 minutos
- Total: **~2-6 minutos**

**Espacio en disco:**

- Backup completo sin comprimir: ~500 MB - 2 GB
- Backup completo comprimido: ~100 MB - 500 MB
- 30 días de backups (1/hora): **~70 GB - 360 GB**

### Tarea programada

**Configuración:**

```yaml
Nombre: SATC-Backup-Automatico
Trigger: Cada hora (RepetitionInterval: 1 hora)
Usuario: SYSTEM (LogonType: ServiceAccount)
Privilegios: Highest (Administrador)
Configuración:
  - AllowStartIfOnBatteries: Sí
  - DontStopIfGoingOnBatteries: Sí
  - StartWhenAvailable: Sí
  - ExecutionTimeLimit: Ninguno
```

### Seguridad

- ✅ Backups locales (no expuestos a red)
- ⚠️ Sin encriptación por defecto (implementar si datos sensibles)
- ✅ Permisos de administrador requeridos
- ✅ Logs de auditoría completos

---

## 📞 Comandos Útiles Rápidos

```powershell
# Ver estado general del sistema de backups
Get-ScheduledTaskInfo -TaskName "SATC-Backup-Automatico" | Format-List NextRunTime, LastRunTime
Get-Content ..\backups\last_backup_summary.json | ConvertFrom-Json | Format-List

# Ejecutar backup ahora
Start-ScheduledTask -TaskName "SATC-Backup-Automatico"

# Ver últimos 20 logs
Get-Content ..\backups\backup_log.txt -Tail 20

# Listar backups de hoy
Get-ChildItem ..\backups -Recurse -Include *.zip |
    Where-Object { $_.LastWriteTime -gt (Get-Date).Date } |
    Format-Table Name, Length, LastWriteTime

# Deshabilitar tarea programada temporalmente
Disable-ScheduledTask -TaskName "SATC-Backup-Automatico"

# Habilitar tarea programada
Enable-ScheduledTask -TaskName "SATC-Backup-Automatico"

# Eliminar tarea programada
Unregister-ScheduledTask -TaskName "SATC-Backup-Automatico" -Confirm:$false
```

---

## 📝 Notas Finales

### Mejores prácticas

1. **Monitorear regularmente**: Revisar logs semanalmente
2. **Probar restauración**: Al menos una vez al mes
3. **Backup externo**: Considerar replicación a storage remoto
4. **Retención adecuada**: Ajustar según espacio disponible
5. **Alertas**: Configurar notificaciones por email (futuro)

### Mantenimiento

- **Diario**: Verificar que tarea se ejecute (automático)
- **Semanal**: Revisar logs de errores
- **Mensual**: Probar restauración de backup
- **Trimestral**: Revisar espacio en disco y ajustar retención

### Soporte

Para problemas no cubiertos en este documento:

1. Revisar logs detallados en `backups/backup_log.txt`
2. Verificar estado de contenedores: `docker ps`
3. Consultar documentación técnica en `Documentation/docs base/ARQUITECTURA_SATC.md`

---

**Última actualización:** 14 de febrero de 2026  
**Versión:** 1.0  
**Sistema:** SATC (Sistema de Administración Tributaria y Control)
