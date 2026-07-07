param(
    [ValidateSet("deploy", "rollback", "status", "logs")]
    [string]$Action = "deploy",
    [string]$AppDir = (Get-Location).Path,
    [string]$DeployRef = "main",
    [int]$HealthTimeoutSeconds = 300,
    [int]$LogTail = 200
)

$ErrorActionPreference = "Stop"

function Require-Command {
    param([string]$Name)

    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        throw "$Name is required"
    }
}

function Ensure-EnvFile {
    if (-not (Test-Path ".env")) {
        Copy-Item ".env.example" ".env"
        Write-Host "Created .env from .env.example. Review local secrets before production use."
    }
}

function Get-CurrentRevision {
    git rev-parse --verify HEAD
}

function Wait-ForHealth {
    powershell -ExecutionPolicy Bypass -File "scripts\wait-compose-health.ps1" -TimeoutSeconds $HealthTimeoutSeconds
}

Set-Location $AppDir

$stateDir = Join-Path $AppDir ".deploy"
$previousRevFile = Join-Path $stateDir "previous_revision"
$currentRevFile = Join-Path $stateDir "current_revision"
New-Item -ItemType Directory -Force -Path $stateDir | Out-Null

switch ($Action) {
    "deploy" {
        Require-Command "docker"
        Require-Command "git"
        Ensure-EnvFile

        $currentRevision = Get-CurrentRevision
        Set-Content -Path $previousRevFile -Value $currentRevision -NoNewline

        git fetch --all --prune
        git checkout $DeployRef

        $newRevision = Get-CurrentRevision
        Set-Content -Path $currentRevFile -Value $newRevision -NoNewline

        docker compose config | Out-Null
        docker compose build
        docker compose up -d
        Wait-ForHealth

        Write-Host "Deployment completed at revision $newRevision."
    }
    "rollback" {
        Require-Command "docker"
        Require-Command "git"
        Ensure-EnvFile

        if (-not (Test-Path $previousRevFile)) {
            throw "No previous revision recorded in $previousRevFile."
        }

        $targetRevision = Get-Content $previousRevFile -Raw
        $targetRevision = $targetRevision.Trim()
        git checkout $targetRevision
        Set-Content -Path $currentRevFile -Value $targetRevision -NoNewline

        docker compose config | Out-Null
        docker compose build
        docker compose up -d
        Wait-ForHealth

        Write-Host "Rollback completed at revision $targetRevision."
    }
    "status" {
        docker compose ps
    }
    "logs" {
        docker compose logs --tail=$LogTail
    }
}
