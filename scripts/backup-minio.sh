#!/bin/sh
# ====================================
# SATC - Backup MinIO (volumen directo)
# ====================================
# Lee /minio-data (montado :ro) y genera tarball comprimido con
# retención escalonada igual a la de las BDs (ver backup-all.sh):
#   30min -> 48 copias (~24h) | daily -> 30 copias (~1 mes) | weekly -> 12 (~3 meses)
# ====================================

BACKUP_DIR="/backups/minio"
DATE=$(date +%Y%m%d_%H%M%S)
TODAY=$(date +%Y%m%d)
WEEK=$(date +%G-W%V)
MINIO_DATA_DIR="/minio-data"

KEEP_30MIN=48
KEEP_DAILY=30
KEEP_WEEKLY=12

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"; }

rotate() {
  dir="$1"; keep="$2"; pattern="$3"
  ls -t "$dir"/$pattern 2>/dev/null | tail -n +"$((keep + 1))" | while IFS= read -r f; do
    rm -f -- "$f"
  done
}

if [ ! -d "$MINIO_DATA_DIR" ] || [ -z "$(ls -A "$MINIO_DATA_DIR" 2>/dev/null)" ]; then
  log "SKIP MinIO: $MINIO_DATA_DIR vacío o no montado"
  exit 0
fi

mkdir -p "$BACKUP_DIR/30min" "$BACKUP_DIR/daily" "$BACKUP_DIR/weekly"

file="$BACKUP_DIR/30min/minio_${DATE}.tar.gz"
tar -czf "$file" -C "$MINIO_DATA_DIR" .

if ! tar -tzf "$file" >/dev/null 2>&1; then
  log "ERROR MinIO: backup corrupto, descartando $file"
  rm -f "$file"
  exit 1
fi
log "OK MinIO: minio_${DATE}.tar.gz ($(du -h "$file" | cut -f1))"

if ! ls "$BACKUP_DIR/daily/minio_${TODAY}"_*.tar.gz >/dev/null 2>&1; then
  cp "$file" "$BACKUP_DIR/daily/minio_${DATE}.tar.gz"
fi

if ! ls "$BACKUP_DIR/weekly/minio_week-${WEEK}"_*.tar.gz >/dev/null 2>&1; then
  cp "$file" "$BACKUP_DIR/weekly/minio_week-${WEEK}_${DATE}.tar.gz"
fi

rotate "$BACKUP_DIR/30min"  "$KEEP_30MIN"  "minio_*.tar.gz"
rotate "$BACKUP_DIR/daily"  "$KEEP_DAILY"  "minio_*.tar.gz"
rotate "$BACKUP_DIR/weekly" "$KEEP_WEEKLY" "minio_week-*.tar.gz"