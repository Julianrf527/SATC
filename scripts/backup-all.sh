#!/bin/sh
# ====================================
# SATC - Script de Backup Completo
# ====================================
# Respalda todas las BDs PostgreSQL + MinIO con retención escalonada
# (grandfather-father-son), para no saturar disco sin perder margen
# de recuperación a mediano plazo:
#
#   30min -> conserva 48 copias  (~24h de margen, 1 cada 30 min)
#   daily -> conserva 30 copias  (~1 mes,        1 por día)
#   weekly-> conserva 12 copias  (~3 meses,      1 por semana ISO)
#
# Cada DB que no exista en este entorno (ej. infraction en un
# despliegue donde aún no está activo) se omite sin abortar el resto.
# ====================================

BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
TODAY=$(date +%Y%m%d)
WEEK=$(date +%G-W%V)

KEEP_30MIN=48
KEEP_DAILY=30
KEEP_WEEKLY=12

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

# Conserva las $2 más recientes que matcheen $3 dentro de $1, borra el resto
rotate() {
  dir="$1"; keep="$2"; pattern="$3"
  ls -t "$dir"/$pattern 2>/dev/null | tail -n +"$((keep + 1))" | while IFS= read -r f; do
    rm -f -- "$f"
  done
}

# $1=carpeta destino  $2=host postgres  $3=nombre de BD
backup_db() {
  name="$1"; host="$2"; db="$3"
  base="$BACKUP_DIR/$name"
  mkdir -p "$base/30min" "$base/daily" "$base/weekly"

  if ! pg_isready -h "$host" -t 5 >/dev/null 2>&1; then
    log "SKIP $name: $host no responde (servicio ausente en este entorno)"
    return
  fi

  file="$base/30min/${db}_${DATE}.sql.gz"
  if ! PGPASSWORD="$POSTGRES_PASSWORD" pg_dump -h "$host" -U postgres -d "$db" | gzip > "$file"; then
    log "ERROR $name: pg_dump falló para $db"
    rm -f "$file"
    return
  fi

  if ! gzip -t "$file" 2>/dev/null; then
    log "ERROR $name: backup corrupto, descartando $file"
    rm -f "$file"
    return
  fi
  log "OK $name: ${db}_${DATE}.sql.gz ($(du -h "$file" | cut -f1))"

  # Promueve a daily si todavía no hay copia de hoy
  if ! ls "$base/daily/${db}_${TODAY}"_*.sql.gz >/dev/null 2>&1; then
    cp "$file" "$base/daily/${db}_${DATE}.sql.gz"
  fi

  # Promueve a weekly si todavía no hay copia de esta semana ISO
  if ! ls "$base/weekly/${db}_week-${WEEK}"_*.sql.gz >/dev/null 2>&1; then
    cp "$file" "$base/weekly/${db}_week-${WEEK}_${DATE}.sql.gz"
  fi

  rotate "$base/30min"  "$KEEP_30MIN"  "${db}_*.sql.gz"
  rotate "$base/daily"  "$KEEP_DAILY"  "${db}_*.sql.gz"
  rotate "$base/weekly" "$KEEP_WEEKLY" "${db}_week-*.sql.gz"
}

log "===== Iniciando backup SATC ====="

backup_db postgres-users       postgres-users       user_db
backup_db postgres-sanctioning postgres-sanctioning expedientes_db
backup_db postgres-docs        postgres-docs        documentos_db
backup_db postgres-involved    postgres-involved    involucrados_db
backup_db postgres-infraction  postgres-infraction  infracciones_db

log "Backup MinIO..."
sh /backup-minio.sh

log "===== Backup SATC completado · espacio total: $(du -sh "$BACKUP_DIR" | cut -f1) ====="