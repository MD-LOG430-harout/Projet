[CmdletBinding(SupportsShouldProcess, ConfirmImpact = 'High')]
param(
    [string]$ProjectName = 'cantelcox-phase2full',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $RepoRoot

if (-not (Test-Path '.env')) {
    throw '.env is missing. Create it from .env.example and set the required local-only values.'
}

$env:HLR_ENABLED = 'false'
$env:HLR_FORCE_FAILURE = 'false'
$env:PAYMENT_FORCE_REFUSAL = 'false'
$env:PAYMENT_GATEWAY_FORCE_REFUSAL = 'false'
$env:PAYMENT_GATEWAY_FORCE_FAILURE = 'false'

$approved = $Force -or $PSCmdlet.ShouldProcess(
    "Compose project '$ProjectName' and its named volumes",
    'Reset the isolated demo databases, Kafka data, Grafana data, and PortabilityHub data'
)
if (-not $approved) {
    Write-Host 'Reset cancelled.'
    exit 0
}

Write-Host "Resetting only Compose project '$ProjectName'..." -ForegroundColor Yellow
& docker compose -p $ProjectName down -v
if ($LASTEXITCODE -ne 0) { throw 'docker compose down failed' }

& docker compose -p $ProjectName up -d --build --wait
if ($LASTEXITCODE -ne 0) { throw 'docker compose up failed' }

& docker compose -p $ProjectName ps
if ($LASTEXITCODE -ne 0) { throw 'docker compose ps failed' }

$statusJson = & docker compose -p $ProjectName ps --format json
if ($LASTEXITCODE -ne 0) { throw 'docker compose ps --format json failed' }
$containers = @()
if ($statusJson) {
    $containers = $statusJson | ForEach-Object { $_ | ConvertFrom-Json }
}
$badContainers = @($containers | Where-Object {
    $_.State -ne 'running' -or ($_.Health -and $_.Health -ne 'healthy')
})
if ($badContainers.Count -gt 0) {
    $badContainers | ForEach-Object {
        Write-Host "$($_.Service): state=$($_.State) health=$($_.Health)" -ForegroundColor Red
    }
    throw 'At least one required demo service is not healthy.'
}

Write-Host 'Demo stack reset completed.' -ForegroundColor Green
