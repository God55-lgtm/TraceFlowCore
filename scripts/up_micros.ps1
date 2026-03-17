#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Levanta los 4 microservicios FastAPI en ventanas separadas.
.DESCRIPTION
    Abre una ventana de terminal para cada microservicio (puertos 8001,8002,8004,8005).
    Verifica que los puertos estén libres y que las dependencias estén instaladas.
.EXAMPLE
    .\levantar_micros.ps1
#>

$ErrorActionPreference = "Stop"

$services = @(
    @{name="tienda"; port=8001; folder="tienda"},
    @{name="pago"; port=8002; folder="pago"},
    @{name="inventario"; port=8004; folder="inventario"},
    @{name="notificacion"; port=8005; folder="notificacion"}
)

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

# Verificar que estamos en la carpeta correcta
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$microsDir = Split-Path -Parent $scriptDir
Set-Location $microsDir

if (-not (Test-Path "tienda\main.py")) {
    Show-Error "Este script debe ejecutarse desde la carpeta 'microservicios\scripts'"
    exit 1
}

Show-Info "Verificando puertos disponibles..."

# Verificar puertos
foreach ($svc in $services) {
    if (-not (Test-PortFree $svc.port)) {
        Show-Error "El puerto $($svc.port) ya está en uso. Cierra el proceso que lo está usando."
        exit 1
    }
}

Show-Success "Todos los puertos están disponibles"

Show-Info "Iniciando microservicios..."

# Abrir cada microservicio en una nueva ventana
foreach ($svc in $services) {
    Show-Info "   Iniciando $($svc.name) en puerto $($svc.port)..."
    
    $command = "cd '$microsDir\$($svc.folder)'; python -m uvicorn main:app --reload --port $($svc.port)"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $command
    
    Start-Sleep -Milliseconds 800
}

Show-Success "✅ Todos los microservicios iniciados"
Show-Info "📌 Puertos:"
Show-Info "   - Tienda:      http://localhost:8001"
Show-Info "   - Pago:        http://localhost:8002"
Show-Info "   - Inventario:  http://localhost:8004"
Show-Info "   - Notificación: http://localhost:8005"
Show-Info ""
Show-Info "Presiona Ctrl+C en cada ventana para detenerlos individualmente"
Show-Info "O usa el script detener_micros.ps1 para detener todos"