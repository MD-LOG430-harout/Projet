param(
    [int]$TimeoutSeconds = 300,
    [int]$IntervalSeconds = 5
)

$ErrorActionPreference = "Stop"
$deadline = (Get-Date).AddSeconds($TimeoutSeconds)

try {
    docker info | Out-Null
}
catch {
    Write-Error "Docker Desktop/Engine is not reachable from this PowerShell session. Start Docker Desktop, then retry. Details: $($_.Exception.Message)"
    exit 1
}

function Get-ContainerHealth {
    param([string]$ContainerId)

    $name = docker inspect --format "{{.Name}}" $ContainerId
    $state = docker inspect --format "{{.State.Status}}" $ContainerId
    $exitCode = docker inspect --format "{{.State.ExitCode}}" $ContainerId
    $health = docker inspect --format "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}" $ContainerId

    [PSCustomObject]@{
        Name = $name.TrimStart("/")
        State = $state
        ExitCode = $exitCode
        Health = $health
    }
}

while ($true) {
    $containerIds = @(docker compose ps -q)

    if ($containerIds.Count -eq 0) {
        Write-Host "No Compose containers are running yet."
    }
    else {
        $pending = @()

        foreach ($containerId in $containerIds) {
            $container = Get-ContainerHealth -ContainerId $containerId

            if ($container.Health -eq "healthy") {
                continue
            }

            if ($container.Health -eq "none" -and $container.State -eq "running") {
                continue
            }

            if ($container.State -eq "exited" -and $container.ExitCode -eq "0") {
                continue
            }

            $pending += $container
        }

        if ($pending.Count -eq 0) {
            Write-Host "All Compose containers are healthy, running, or completed successfully."
            docker compose ps
            exit 0
        }

        foreach ($container in $pending) {
            Write-Host "Waiting for $($container.Name): state=$($container.State) health=$($container.Health) exitCode=$($container.ExitCode)"
        }
    }

    if ((Get-Date) -ge $deadline) {
        Write-Error "Timed out after ${TimeoutSeconds}s waiting for Compose healthchecks."
        docker compose ps
        docker compose logs --tail=120
        exit 1
    }

    Start-Sleep -Seconds $IntervalSeconds
}
