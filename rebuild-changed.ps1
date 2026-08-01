# rebuild-changed.ps1
# Detecta servicios con cambios (git diff HEAD) y los rebuilda en Docker.
# Uso manual: .\rebuild-changed.ps1
# Con flag:   .\rebuild-changed.ps1 -Force      → rebuilda todo
#             .\rebuild-changed.ps1 -Service frontend  → solo ese servicio

param(
    [switch]$Force,
    [string]$Service = ""
)

$root = $PSScriptRoot
Set-Location $root

# Mapa: carpeta → { nombre en docker-compose, necesita npm build }
$serviceMap = [ordered]@{
    "app-infraction"    = @{ docker = "app-infraction";    npm = $false }
    "app-sancionatoria" = @{ docker = "app-sancionatoria";  npm = $false }
    "app-docs"          = @{ docker = "app-docs";           npm = $false }
    "app-involved"      = @{ docker = "app-involved";       npm = $false }
    "app-users"         = @{ docker = "app-users";          npm = $false }
    "api-gateway"       = @{ docker = "api-gateway";        npm = $false }
    "frontend"          = @{ docker = "frontend";           npm = $true  }
}

# ── Determinar qué rebuildar ──────────────────────────────────────────────────
if ($Service -ne "") {
    if (-not $serviceMap.Contains($Service)) {
        Write-Host "Servicio desconocido: $Service. Opciones: $($serviceMap.Keys -join ', ')" -ForegroundColor Red
        exit 1
    }
    $toRebuild = @($Service)

} elseif ($Force) {
    $toRebuild = @($serviceMap.Keys)

} else {
    # Archivos modificados vs último commit (staged + unstaged)
    $changed = @(git diff HEAD --name-only 2>$null)
    # También archivos nuevos sin seguimiento
    $changed += @(git ls-files --others --exclude-standard 2>$null)

    $toRebuild = @()
    foreach ($svc in $serviceMap.Keys) {
        if ($changed | Where-Object { $_ -match "^$([regex]::Escape($svc))/" }) {
            $toRebuild += $svc
        }
    }
}

if ($toRebuild.Count -eq 0) {
    Write-Host "Sin cambios detectados en servicios Docker." -ForegroundColor Green
    exit 0
}

Write-Host ""
Write-Host "Servicios a rebuildar: $($toRebuild -join ', ')" -ForegroundColor Cyan
Write-Host ""

$errors = @()

foreach ($svc in $toRebuild) {
    $info = $serviceMap[$svc]
    Write-Host "=== $svc ===" -ForegroundColor Yellow

    # npm build (solo frontend)
    if ($info.npm) {
        Write-Host "  npm run build..." -ForegroundColor Gray
        Push-Location "$root\frontend"
        npm run build
        $npmExit = $LASTEXITCODE
        Pop-Location
        if ($npmExit -ne 0) {
            $errors += "$svc : npm build fallo (exit $npmExit)"
            Write-Host "  ERROR: npm build fallo" -ForegroundColor Red
            continue
        }
        Write-Host "  npm build OK" -ForegroundColor Green
    }

    # Docker build
    Write-Host "  docker compose build $($info.docker)..." -ForegroundColor Gray
    docker compose build $info.docker
    if ($LASTEXITCODE -ne 0) {
        $errors += "$svc : docker build fallo"
        Write-Host "  ERROR: docker build fallo" -ForegroundColor Red
        continue
    }
    Write-Host "  docker build OK" -ForegroundColor Green

    # Up
    Write-Host "  docker compose up -d $($info.docker)..." -ForegroundColor Gray
    docker compose up -d $info.docker
    if ($LASTEXITCODE -ne 0) {
        $errors += "$svc : docker up fallo"
        Write-Host "  ERROR: docker up fallo" -ForegroundColor Red
        continue
    }
    Write-Host "  Servicio levantado OK" -ForegroundColor Green
    Write-Host ""
}

# ── Resultado final ───────────────────────────────────────────────────────────
if ($errors.Count -gt 0) {
    Write-Host "Rebuild terminado con errores:" -ForegroundColor Red
    $errors | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
    exit 1
} else {
    Write-Host "Rebuild completado exitosamente." -ForegroundColor Green
    exit 0
}
