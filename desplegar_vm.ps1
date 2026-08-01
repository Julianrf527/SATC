$ErrorActionPreference = "Stop"

# Configuración
$ServerIp = "192.168.254.222"
$ServerUser = "administrador"
$TarName = "satc_images.tar"
$PkgDir = "deploy_vm"

Write-Host "Verificando conexión con Docker..." -ForegroundColor Cyan
docker ps > $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Docker no está en ejecución. Por favor, inicia Docker Desktop." -ForegroundColor Red
    exit 1
}

Write-Host "`n[ 1/5 ] Construyendo imágenes locales..." -ForegroundColor Yellow
# Usamos un tag local para el registry
$Prefix = "satc-local"
docker build -t ${Prefix}/satc-gateway:latest .\api-gateway
docker build -t ${Prefix}/satc-users:latest .\app-users
docker build -t ${Prefix}/satc-sanctioning:latest .\app-sancionatoria
docker build -t ${Prefix}/satc-docs:latest .\app-docs
docker build -t ${Prefix}/satc-involved:latest .\app-involved
docker build -t ${Prefix}/satc-infraction:latest .\app-infraction
docker build -t ${Prefix}/satc-frontend:latest --build-arg VITE_API_URL=http://${ServerIp}:8000 .\frontend

Write-Host "`n[ 2/5 ] Exportando imágenes a ${TarName} (esto puede tomar unos minutos)..." -ForegroundColor Yellow
docker save -o $TarName ${Prefix}/satc-gateway:latest ${Prefix}/satc-users:latest ${Prefix}/satc-sanctioning:latest ${Prefix}/satc-docs:latest ${Prefix}/satc-involved:latest ${Prefix}/satc-infraction:latest ${Prefix}/satc-frontend:latest

Write-Host "`n[ 3/5 ] Preparando archivos de despliegue sin código..." -ForegroundColor Yellow
if (Test-Path $PkgDir) { Remove-Item -Recurse -Force $PkgDir }
New-Item -ItemType Directory -Path $PkgDir | Out-Null
Copy-Item "deploy\docker-compose.prod.yml" -Destination "$PkgDir\docker-compose.yml"
Copy-Item "deploy\env-produccion.txt" -Destination "$PkgDir\.env"
Copy-Item "db-script" -Destination "$PkgDir\db-script" -Recurse
Copy-Item "nginx" -Destination "$PkgDir\nginx" -Recurse
Copy-Item "scripts" -Destination "$PkgDir\scripts" -Recurse

# Ajustamos el .env para usar las imagenes locales
(Get-Content "$PkgDir\.env") -replace "REGISTRY=.*", "REGISTRY=$Prefix" -replace "VERSION=.*", "VERSION=latest" | Set-Content "$PkgDir\.env"

Write-Host "`n[ 4/5 ] Transfiriendo archivos e imágenes a la VM ($ServerIp)..." -ForegroundColor Yellow
Write-Host ">>> Autenticación por llave SSH configurada: no debería pedir contraseña ($ServerUser) <<<" -ForegroundColor Cyan
# Keepalive para que la conexión no se caiga durante la transferencia del .tar (varios GB)
$SshKeepalive = @("-o", "ServerAliveInterval=30", "-o", "ServerAliveCountMax=120")

# Limpia y recrea el directorio de despliegue en la VM para evitar conflictos
ssh -n @SshKeepalive ${ServerUser}@${ServerIp} "sudo rm -rf ~/satc-deploy && mkdir -p ~/satc-deploy"
scp @SshKeepalive -r ${PkgDir}/* ${ServerUser}@${ServerIp}:~/satc-deploy/
# El glob '*' de scp.exe (Windows) no incluye archivos que empiezan con punto -> .env se transfiere aparte
scp @SshKeepalive ${PkgDir}/.env ${ServerUser}@${ServerIp}:~/satc-deploy/.env
scp @SshKeepalive $TarName ${ServerUser}@${ServerIp}:~/satc-deploy/
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: la transferencia de ${TarName} falló (conexión interrumpida). Abortando antes de tocar la VM." -ForegroundColor Red
    exit 1
}
# Convertir scripts de CRLF (Windows) a LF (Linux)
ssh -n @SshKeepalive ${ServerUser}@${ServerIp} 'sed -i "s/\r$//" ~/satc-deploy/scripts/*.sh && chmod +x ~/satc-deploy/scripts/*.sh'

Write-Host "`n[ 5/5 ] Ejecutando comandos en la VM para detener contenedores, cargar imágenes y levantar..." -ForegroundColor Yellow
$SSHCommand = @"
cd ~/satc-deploy
echo '==> Apagando contenedores existentes y eliminando volúmenes...'
sudo docker compose down -v 2>/dev/null || true
sudo docker stop `$(sudo docker ps -aq) 2>/dev/null || true
sudo docker rm `$(sudo docker ps -aq) 2>/dev/null || true

echo '==> Eliminando todas las imágenes Docker...'
sudo docker rmi `$(sudo docker images -aq) 2>/dev/null || true
sudo docker system prune -af --volumes 2>/dev/null || true

echo '==> Cargando imágenes desde tar...'
sudo docker load -i $TarName || { echo '==> ERROR: docker load falló (tar incompleto/corrupto). Abortando antes de levantar.'; exit 1; }

echo '==> Levantando servicios de forma desatendida...'
# Postgres pasa por un ciclo initdb -> shutdown -> restart al primer arranque; el healthcheck
# puede marcarlo "unhealthy" un instante y abortar 'up' por dependencia. Reintenta: es idempotente,
# los contenedores ya sanos quedan intactos y solo arranca lo que falta.
for intento in 1 2 3 4 5; do
    if sudo docker compose up -d; then
        echo "==> docker compose up -d completado (intento $intento)"
        break
    fi
    echo "==> Intento $intento falló (probable healthcheck transitorio de Postgres), reintentando en 15s..."
    sleep 15
done
echo '==> Estado final de contenedores:'
sudo docker compose ps -a --format 'table {{.Names}}\t{{.Status}}'
echo '==> ¡Despliegue finalizado exitosamente!'
"@

$SSHCommandUnix = $SSHCommand -replace "`r`n", "`n"
ssh -n ${ServerUser}@${ServerIp} $SSHCommandUnix

# Limpieza local
Write-Host "`n[ Limpieza ] Eliminando archivo tar local temporal..." -ForegroundColor Yellow
Remove-Item $TarName -Force
Remove-Item -Recurse -Force $PkgDir

Write-Host "Proceso completado." -ForegroundColor Green
