[CmdletBinding()]
param(
    [ValidateSet('Preflight', 'Acceptance', 'Nominal', 'Compensation', 'Status', 'Evidence', 'Portability', 'Reliability', 'Links', 'All')]
    [string]$Step = 'All',
    [string]$ProjectName = 'cantelcox-phase2full',
    [string]$OrderId,
    [switch]$OpenDashboards
)

$ErrorActionPreference = 'Stop'
$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
Set-Location $RepoRoot

# Set both the requested demo shorthand and the exact Compose variable names.
$env:HLR_ENABLED = 'false'
$env:HLR_FORCE_FAILURE = 'false'
$env:PAYMENT_FORCE_REFUSAL = 'false'
$env:PAYMENT_GATEWAY_FORCE_REFUSAL = 'false'
$env:PAYMENT_GATEWAY_FORCE_FAILURE = 'false'

function Invoke-DockerChecked {
    param(
        [Parameter(Mandatory)][string[]]$Arguments,
        [switch]$Quiet
    )
    $output = & docker @Arguments
    if ($output -and -not $Quiet) {
        $output | ForEach-Object { Write-Host $_ }
    }
    if ($LASTEXITCODE -ne 0) {
        throw "docker command failed with exit code $LASTEXITCODE"
    }
}

function Get-MysqlCliArguments {
    $mysqlUser = (& docker compose -p $ProjectName exec -T mysql printenv MYSQL_USER).Trim()
    $mysqlPassword = (& docker compose -p $ProjectName exec -T mysql printenv MYSQL_PASSWORD).Trim()
    if (-not $mysqlUser -or -not $mysqlPassword) { throw 'MySQL demo credentials are not available inside the container.' }
    return @('compose', '-p', $ProjectName, 'exec', '-T', 'mysql', 'mysql', "--user=$mysqlUser", "--password=$mysqlPassword", '--batch', '--raw')
}

function Invoke-TestContainer {
    param([Parameter(Mandatory)][string[]]$PytestArguments)
    $network = "${ProjectName}_default"
    $mysqlPassword = (& docker compose -p $ProjectName exec -T mysql printenv MYSQL_PASSWORD).Trim()
    if (-not $mysqlPassword) { throw 'MYSQL_PASSWORD is not available inside the running MySQL container.' }
    $arguments = @(
        'run', '--rm', '--network', $network,
        '-v', "${RepoRoot}:/repo", '-w', '/repo',
        '-e', 'PYTHONPATH=/repo',
        '-e', 'E2E_BASE_URL=http://api-gateway',
        '-e', 'E2E_HUB_URL=http://portabilityhub-gateway:8080',
        '-e', 'E2E_MYSQL_HOST=mysql',
        '-e', 'PHASE2_MYSQL_HOST=mysql',
        '-e', 'INCREMENT0_MYSQL_HOST=mysql',
        '-e', 'INCREMENT0_KAFKA_BOOTSTRAP=kafka:9092',
        '-e', 'KAFKA_BOOTSTRAP_SERVERS=kafka:9092',
        '-e', "MYSQL_PASSWORD=$mysqlPassword",
        'cantelcox-test:phase2', 'pytest', '-q'
    ) + $PytestArguments
    Invoke-DockerChecked $arguments
}

function Show-Preflight {
    Write-Host "`n=== Preflight ===" -ForegroundColor Cyan
    Invoke-DockerChecked @('compose', '-p', $ProjectName, 'config', '--quiet')
    Invoke-DockerChecked @('compose', '-p', $ProjectName, 'ps')

    $health = Invoke-RestMethod 'http://localhost:8080/health' -TimeoutSec 5
    $hubHealth = Invoke-RestMethod 'http://localhost:8282/actuator/health' -TimeoutSec 5
    Write-Host "Gateway health: $($health | ConvertTo-Json -Compress)"
    Write-Host "PortabilityHub health: $($hubHealth | ConvertTo-Json -Compress)"

    $hlrEnabled = (& docker compose -p $ProjectName exec -T svc-lignes-services printenv HLR_ENABLED).Trim()
    $hlrFailure = (& docker compose -p $ProjectName exec -T svc-lignes-services printenv HLR_FORCE_FAILURE).Trim()
    $paymentRefusal = (& docker compose -p $ProjectName exec -T svc-usage-facturation printenv PAYMENT_GATEWAY_FORCE_REFUSAL).Trim()
    if ($hlrEnabled -ne 'false' -or $hlrFailure -ne 'false' -or $paymentRefusal -ne 'false') {
        throw "Nominal configuration mismatch: HLR_ENABLED=$hlrEnabled HLR_FORCE_FAILURE=$hlrFailure PAYMENT_GATEWAY_FORCE_REFUSAL=$paymentRefusal"
    }
    Write-Host 'Nominal environment verified.' -ForegroundColor Green
}

function New-DemoOrder {
    param(
        [string]$ExpectedTerminalStatus,
        [string]$ScenarioName
    )
    Write-Host "`n=== $ScenarioName ===" -ForegroundColor Cyan
    $suffix = [Guid]::NewGuid().ToString('N').Substring(0, 12)
    $traceId = [Guid]::NewGuid().ToString('N')
    $password = 'Stronger123'
    $email = "demo-$suffix@example.test"

    $registerBody = @{
        email = $email; password = $password; displayName = 'Demo Phase 2'; legalName = 'Demo Phase 2'; customerType = 'individual'
        address = @{ line1 = '1 Rue Demo'; city = 'Montreal'; province = 'QC'; postalCode = 'H1A1A1' }
        identityDocument = @{ type = 'driver_license'; number = "DEMO-$suffix" }
    } | ConvertTo-Json -Depth 5
    $register = Invoke-RestMethod 'http://localhost:8080/v1/customers/register' -Method Post -ContentType 'application/json' -Headers @{ TraceId = $traceId } -Body $registerBody

    $loginBody = @{ email = $email; password = $password } | ConvertTo-Json
    $login = Invoke-RestMethod 'http://localhost:8080/v1/auth/login' -Method Post -ContentType 'application/json' -Headers @{ TraceId = $traceId } -Body $loginBody
    $mfaBody = @{ challengeId = $login.challengeId; otp = $login.devOtp } | ConvertTo-Json
    $mfa = Invoke-RestMethod 'http://localhost:8080/v1/auth/mfa/verify' -Method Post -ContentType 'application/json' -Headers @{ TraceId = $traceId } -Body $mfaBody
    $headers = @{ Authorization = "Bearer $($mfa.sessionToken)"; TraceId = $traceId }
    $offers = Invoke-RestMethod 'http://localhost:8080/v1/offers' -Headers $headers

    $idempotencyKey = [Guid]::NewGuid().ToString()
    $orderHeaders = $headers.Clone()
    $orderHeaders['Idempotency-Key'] = $idempotencyKey
    $orderBody = @{ customerId = $register.customerId; offerId = $offers.offers[0].offerId; quantity = 1; orderType = 'NEW_PLAN'; numberMode = 'NEW' } | ConvertTo-Json
    $accepted = Invoke-WebRequest 'http://localhost:8080/v1/orders' -UseBasicParsing -Method Post -ContentType 'application/json' -Headers $orderHeaders -Body $orderBody
    $acceptedBody = $accepted.Content | ConvertFrom-Json
    Write-Host "HTTP $($accepted.StatusCode)"
    Write-Host "Location: $($accepted.Headers['Location'])"
    Write-Host "orderId: $($acceptedBody.orderId)"
    Write-Host "sagaId: $($acceptedBody.sagaId)"
    Write-Host "initial status: $($acceptedBody.status)"
    Write-Host "Body: $($accepted.Content)"
    if ($accepted.StatusCode -ne 202 -or $acceptedBody.status -ne 'EN_COURS') { throw 'Order was not accepted as EN_COURS.' }

    $replay = Invoke-WebRequest 'http://localhost:8080/v1/orders' -UseBasicParsing -Method Post -ContentType 'application/json' -Headers $orderHeaders -Body $orderBody
    $replayBody = $replay.Content | ConvertFrom-Json
    Write-Host "Replay orderId: $($replayBody.orderId)"
    if ($replayBody.orderId -ne $acceptedBody.orderId) { throw 'Idempotency replay created another order.' }

    $deadline = (Get-Date).AddSeconds(15)
    do {
        Start-Sleep -Milliseconds 250
        $status = Invoke-RestMethod "http://localhost:8080/v1/orders/$($acceptedBody.orderId)/status" -Headers $headers
    } while ($status.status -eq 'EN_COURS' -and (Get-Date) -lt $deadline)
    Write-Host "Terminal status: $($status.status)"
    if ($status.status -ne $ExpectedTerminalStatus) { throw "Expected $ExpectedTerminalStatus, got $($status.status)" }
    Show-DatabaseInspection -OrderId $acceptedBody.orderId
    Write-Host "$ScenarioName passed." -ForegroundColor Green
    return $acceptedBody.orderId
}

function Invoke-AcceptanceDemo {
    [void](New-DemoOrder -ExpectedTerminalStatus 'CONFIRMEE' -ScenarioName 'Live nominal saga: 202 + idempotency + CONFIRMEE')
}

function Invoke-CompensationDemo {
    Write-Host "`n=== Enable payment refusal without rebuilding the stack ===" -ForegroundColor Cyan
    $env:PAYMENT_FORCE_REFUSAL = 'true'
    $env:PAYMENT_GATEWAY_FORCE_REFUSAL = 'true'
    Invoke-DockerChecked @('compose', '-p', $ProjectName, 'up', '-d', '--force-recreate', '--wait', 'svc-usage-facturation') -Quiet
    $effective = (& docker compose -p $ProjectName exec -T svc-usage-facturation printenv PAYMENT_GATEWAY_FORCE_REFUSAL).Trim()
    if ($effective -ne 'true') { throw "Payment refusal flag was not applied: $effective" }
    try {
        [void](New-DemoOrder -ExpectedTerminalStatus 'ANNULEE' -ScenarioName 'Live compensation saga: PaiementRefuse -> CommandeAnnulee')
    }
    finally {
        Write-Host "`n=== Restore nominal payment configuration ===" -ForegroundColor Cyan
        $env:PAYMENT_FORCE_REFUSAL = 'false'
        $env:PAYMENT_GATEWAY_FORCE_REFUSAL = 'false'
        Invoke-DockerChecked @('compose', '-p', $ProjectName, 'up', '-d', '--force-recreate', '--wait', 'svc-usage-facturation') -Quiet
        $restored = (& docker compose -p $ProjectName exec -T svc-usage-facturation printenv PAYMENT_GATEWAY_FORCE_REFUSAL).Trim()
        Write-Host "PAYMENT_GATEWAY_FORCE_REFUSAL=$restored"
    }
}

function Show-OrderStatus {
    if (-not $OrderId) { throw 'Pass -OrderId when using -Step Status.' }
    $status = Invoke-RestMethod "http://localhost:8080/v1/orders/$OrderId/status" -TimeoutSec 5
    Write-Host ($status | ConvertTo-Json -Depth 5)
}

function Show-DatabaseInspection {
    param([Parameter(Mandatory)][string]$OrderId)
    $mysqlArgs = Get-MysqlCliArguments

    Write-Host "`n--- order row ---" -ForegroundColor DarkCyan
    Invoke-DockerChecked ($mysqlArgs + @('-e', "SELECT order_id,saga_id,status,terminal_reason,current_operator FROM commandes_activations.orders WHERE order_id='$OrderId';"))
    Write-Host "`n--- saga_state ---" -ForegroundColor DarkCyan
    Invoke-DockerChecked ($mysqlArgs + @('-e', "SELECT saga_id,order_id,status,payment_status,line_status,portability_status,deadline_at FROM commandes_activations.saga_state WHERE order_id='$OrderId';"))
    Write-Host "`n--- outbox_events ---" -ForegroundColor DarkCyan
    Invoke-DockerChecked ($mysqlArgs + @('-e', "SELECT event_type,status,event_id,aggregate_id,published_at,attempt_count FROM commandes_activations.outbox_events WHERE aggregate_id='$OrderId' UNION ALL SELECT event_type,status,event_id,aggregate_id,published_at,attempt_count FROM usage_facturation.outbox_events WHERE JSON_UNQUOTE(JSON_EXTRACT(payload,'$.idCommande'))='$OrderId' UNION ALL SELECT event_type,status,event_id,aggregate_id,published_at,attempt_count FROM lignes_services.outbox_events WHERE JSON_UNQUOTE(JSON_EXTRACT(payload,'$.idCommande'))='$OrderId';"))
    Write-Host "`n--- processed_events counts ---" -ForegroundColor DarkCyan
    Invoke-DockerChecked ($mysqlArgs + @('-e', "SELECT 'commandes' service,COUNT(*) processed FROM commandes_activations.processed_events UNION ALL SELECT 'billing',COUNT(*) FROM usage_facturation.processed_events UNION ALL SELECT 'lines',COUNT(*) FROM lignes_services.processed_events UNION ALL SELECT 'audit',COUNT(*) FROM conformite_audit.processed_events;"))
    Write-Host "`n--- audit records ---" -ForegroundColor DarkCyan
    Invoke-DockerChecked ($mysqlArgs + @('-e', "SELECT event_type,aggregate_id,saga_id,trace_id,result FROM conformite_audit.audit_events WHERE saga_id=(SELECT saga_id FROM commandes_activations.orders WHERE order_id='$OrderId') ORDER BY inserted_at;"))
}

function Invoke-NominalTest {
    Write-Host "`n=== Existing nominal E2E ===" -ForegroundColor Cyan
    Invoke-TestContainer @('tests/e2e/test_gateway_flow.py')
}

function Show-Evidence {
    Write-Host "`n=== Kafka topics ===" -ForegroundColor Cyan
    Invoke-DockerChecked @('compose', '-p', $ProjectName, 'exec', '-T', 'kafka', '/opt/kafka/bin/kafka-topics.sh', '--bootstrap-server', 'kafka:9092', '--list')

    $mysqlArgs = Get-MysqlCliArguments

    Write-Host "`n=== Producer Outbox rows ===" -ForegroundColor Cyan
    $outboxSql = "SELECT 'commandes' AS service,event_type,status,event_id,aggregate_id FROM commandes_activations.outbox_events UNION ALL SELECT 'facturation' AS service,event_type,status,event_id,aggregate_id FROM usage_facturation.outbox_events UNION ALL SELECT 'lignes' AS service,event_type,status,event_id,aggregate_id FROM lignes_services.outbox_events ORDER BY service LIMIT 30;"
    Invoke-DockerChecked ($mysqlArgs + @('-e', $outboxSql))

    Write-Host "`n=== Idempotent consumer reservations ===" -ForegroundColor Cyan
    $processedSql = "SELECT 'commandes' service,COUNT(*) processed FROM commandes_activations.processed_events UNION ALL SELECT 'billing',COUNT(*) FROM usage_facturation.processed_events UNION ALL SELECT 'lines',COUNT(*) FROM lignes_services.processed_events UNION ALL SELECT 'audit',COUNT(*) FROM conformite_audit.processed_events;"
    Invoke-DockerChecked ($mysqlArgs + @('-e', $processedSql))

    Write-Host "`n=== Append-only audit chain ===" -ForegroundColor Cyan
    $auditSql = 'SELECT event_type,aggregate_id,saga_id,trace_id,result FROM conformite_audit.audit_events WHERE event_id IS NOT NULL ORDER BY inserted_at DESC LIMIT 20;'
    Invoke-DockerChecked ($mysqlArgs + @('-e', $auditSql))
}

function Invoke-PortabilityTests {
    Write-Host "`n=== Supplied PortabilityHub success + rejection ===" -ForegroundColor Cyan
    Invoke-TestContainer @('tests/e2e/test_phase2_portability.py', '-k', 'success or rejection')
}

function Invoke-ReliabilityTests {
    Write-Host "`n=== Outbox, duplicate, retry and DLQ evidence ===" -ForegroundColor Cyan
    Invoke-TestContainer @('tests/unit/test_retry_dlq.py', 'tests/integration/test_increment0_foundations.py')
    Write-Host 'Replay runbook: docs/runbooks/kafka-dlq-replay.md'
}

function Show-Links {
    $links = @(
        'Swagger       http://localhost:8081',
        'Jaeger        http://localhost:16686',
        'Grafana       http://localhost:3000',
        'Prometheus    http://localhost:9090',
        'Portability   http://localhost:8282/actuator/health'
    )
    Write-Host "`n=== Demo links ===" -ForegroundColor Cyan
    $links | ForEach-Object { Write-Host $_ }
    if ($OpenDashboards) {
        @('http://localhost:8081', 'http://localhost:16686', 'http://localhost:3000', 'http://localhost:9090') | ForEach-Object { Start-Process $_ }
    }
}

switch ($Step) {
    'Preflight'   { Show-Preflight }
    'Acceptance'  { Invoke-AcceptanceDemo }
    'Nominal'     { Invoke-NominalTest }
    'Compensation' { Invoke-CompensationDemo }
    'Status'      { Show-OrderStatus }
    'Evidence'    { Show-Evidence }
    'Portability' { Invoke-PortabilityTests }
    'Reliability' { Invoke-ReliabilityTests }
    'Links'       { Show-Links }
    'All' {
        Show-Preflight
        Invoke-AcceptanceDemo
        Invoke-NominalTest
        Show-Evidence
        Invoke-CompensationDemo
        Invoke-PortabilityTests
        Invoke-ReliabilityTests
        Show-Links
    }
}
