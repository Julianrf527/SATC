#!/bin/sh
# ====================================
# SATC - Setup de Backups Automáticos
# ====================================
# Loop simple cada 30 minutos (más compatible que crond en esta imagen).
# Retención escalonada: ver backup-all.sh / backup-minio.sh
# ====================================

echo "========================================="
echo "SATC - Configurando Backups Automáticos"
echo "Frecuencia: cada 30 minutos"
echo "Retención: 48x30min (~24h) / 30 daily (~1 mes) / 12 weekly (~3 meses)"
echo "========================================="

for svc in postgres-users postgres-sanctioning postgres-docs postgres-involved postgres-infraction; do
  mkdir -p "/backups/$svc/30min" "/backups/$svc/daily" "/backups/$svc/weekly"
done
mkdir -p /backups/minio/30min /backups/minio/daily /backups/minio/weekly

touch /var/log/backup-cron.log

echo "Ejecutando backup inicial..."
sh /backup-all.sh 2>&1 | tee -a /var/log/backup-cron.log

echo ""
echo "Backup inicial completado. Iniciando loop cada 30 minutos..."
echo ""

while true; do
  sleep 1800
  {
    echo "========================================="
    echo "Backup programado: $(date)"
    sh /backup-all.sh
  } >> /var/log/backup-cron.log 2>&1

  # Evita que el log crezca sin límite
  if [ "$(wc -c < /var/log/backup-cron.log)" -gt 10485760 ]; then
    tail -n 2000 /var/log/backup-cron.log > /var/log/backup-cron.log.tmp
    mv /var/log/backup-cron.log.tmp /var/log/backup-cron.log
    echo "[$(date)] Log rotado (excedía 10MB)" >> /var/log/backup-cron.log
  fi
done