#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Levanta el backend Django y el frontend Angular juntos en ventanas separadas.
.DESCRIPTION
    Abre dos ventanas de terminal: una para el backend (puerto 8000) y otra para el frontend (puerto 4200).
    También verifica que los puertos estén libres y que las dependencias estén instaladas.
.EXAMPLE
    .\up_FrontendBackend.ps1
#>

$ErrorActionPreference = "Stop"

function Test-PortFree {
    param($Port)
    $connections = netstat -ano | findstr ":$Port"
    return ($connections.Length -eq 0)
}

function Show-Error {
    param($Msg)
    Write-Host "❌ $Msg" -ForegroundColor Red
}

function Show-Success {
    param($Msg)
    Write-Host "✅ $Msg" -ForegroundColor Green
}

function Show-Info {
    param($Msg)
    Write-Host "ℹ️ $Msg" -ForegroundColor Cyan
}

function Show-Warning {
    param($Msg)
    Write-Host "⚠️ $Msg" -ForegroundColor Yellow
}

# Verificar puertos
$puertos = @(8000, 4200)
foreach ($port in $puertos) {
    if (-not (Test-PortFree $port)) {
        Show-Error "El puerto $port ya está en uso. Cierra el proceso que lo está usando."
        exit 1
    }
}

# Verificar que estamos en la carpeta correcta
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$projectRoot = Split-Path -Parent $scriptDir

if (-not (Test-Path "$projectRoot\backend\manage.py")) {
    Show-Error "No se encuentra el backend. Asegúrate de que la estructura de carpetas sea correcta."
    Show-Info "Esperado: $projectRoot\backend\manage.py"
    exit 1
}

if (-not (Test-Path "$projectRoot\frontend\package.json")) {
    Show-Error "No se encuentra el frontend. Asegúrate de que la estructura de carpetas sea correcta."
    Show-Info "Esperado: $projectRoot\frontend\package.json"
    exit 1
}

Show-Info "Iniciando backend Django..."

# Abrir backend en nueva ventana
$backendCommand = "cd '$projectRoot\backend'; python manage.py runserver"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCommand

Start-Sleep -Seconds 3

Show-Info "Iniciando frontend Angular..."
$frontendCommand = "cd '$projectRoot\frontend'; ng serve -o"
Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCommand

Show-Success "Backend y frontend iniciados correctamente."
Show-Info "Backend: http://localhost:8000"
Show-Info "Frontend: http://localhost:4200"
Show-Info "Presiona Ctrl+C en cada ventana para detener los servicios."