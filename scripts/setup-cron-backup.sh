#!/bin/sh
# ====================================
# SATC - Setup Cron para Backups Automáticos
# ====================================
# Este script configura cron para ejecutar backups cada 30 minutos
# ====================================

set -e

echo "========================================="
echo "SATC - Configurando Backups Automáticos"
echo "Frecuencia: Cada 30 minutos"
echo "========================================="

# Crear directorios de backup si no existen
mkdir -p /backups/postgres-users
mkdir -p /backups/postgres-sanctioning
mkdir -p /backups/postgres-docs
mkdir -p /backups/minio

# Crear log file
touch /var/log/backup-cron.log

# Ejecutar un backup inicial inmediatamente
echo "Ejecutando backup inicial..."
sh /backup-all.sh

echo ""
echo "Backup inicial completado"
echo "Iniciando loop de backups cada 30 minutos..."
echo ""

# Loop simple cada 30 minutos (más compatible que crond en esta imagen)
while true; do
  sleep 1800
  echo "=========================================" >> /var/log/backup-cron.log 2>&1
  echo "Iniciando backup programado: $(date)" >> /var/log/backup-cron.log 2>&1
  sh /backup-all.sh >> /var/log/backup-cron.log 2>&1
done
