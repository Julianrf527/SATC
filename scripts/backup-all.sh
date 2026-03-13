#!/bin/sh
# ====================================
# SATC - Script de Backup Completo
# ====================================
# Este script realiza backup de:
# - Todas las bases de datos PostgreSQL
# - Archivos de MinIO
# - Configuraciones
# ====================================

set -e

# Configuración
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)
RETENTION_DAYS=30

echo "========================================="
echo "SATC - Backup Automático"
echo "Fecha: $(date)"
echo "========================================="

# ==========================================
# BACKUP BASES DE DATOS
# ==========================================
echo ""
echo "[1/4] Backup de base de datos Users..."
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h postgres-users -U postgres -d user_db \
  > "$BACKUP_DIR/postgres-users/user_db_$DATE.sql"
gzip "$BACKUP_DIR/postgres-users/user_db_$DATE.sql"
echo "✓ Backup Users completado: user_db_$DATE.sql.gz"

echo ""
echo "[2/4] Backup de base de datos Sanctioning..."
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h postgres-sanctioning -U postgres -d expedientes_db \
  > "$BACKUP_DIR/postgres-sanctioning/expedientes_db_$DATE.sql"
gzip "$BACKUP_DIR/postgres-sanctioning/expedientes_db_$DATE.sql"
echo "✓ Backup Sanctioning completado: expedientes_db_$DATE.sql.gz"

echo ""
echo "[3/4] Backup de base de datos Docs..."
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h postgres-docs -U postgres -d documentos_db \
  > "$BACKUP_DIR/postgres-docs/documentos_db_$DATE.sql"
gzip "$BACKUP_DIR/postgres-docs/documentos_db_$DATE.sql"
echo "✓ Backup Docs completado: documentos_db_$DATE.sql.gz"

# ==========================================
# LIMPIEZA DE BACKUPS ANTIGUOS
# ==========================================
echo ""
echo "[4/4] Limpiando backups antiguos (>$RETENTION_DAYS días)..."
find "$BACKUP_DIR" -type f -name "*.sql.gz" -mtime +$RETENTION_DAYS -delete
echo "✓ Limpieza completada"

# ==========================================
# RESUMEN
# ==========================================
echo ""
echo "========================================="
echo "✓ Backup completado exitosamente"
echo "Ubicación: $BACKUP_DIR"
echo "Fecha: $DATE"
echo "========================================="

# Calcular espacio usado
echo ""
echo "Espacio usado por backups:"
du -sh "$BACKUP_DIR"/*
