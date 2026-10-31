# Bounded synthetic regression only. Does not launch the application or worker.
# Loads actual changed function ASTs; all downstream boundary commands are doubles.
# This file is prepared for an authorized hosted PowerShell test, not run locally.
[CmdletBinding()]
param(
    [string]$PackageRoot = (Join-Path $PSScriptRoot '../app/Merch_Forge_A5_Current'),
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{32}$')][string]$RunId,
    [Parameter(Mandatory=$true)][string]$RunRoot
)
$ErrorActionPreference = 'Stop'
$startedAt = [DateTime]::UtcNow.ToString('o')
$PackageRoot = [IO.Path]::GetFullPath($PackageRoot)
$RunRoot = [IO.Path]::GetFullPath($RunRoot)
if ($RunRoot -eq $PackageRoot -or $RunRoot.StartsWith(($PackageRoot.TrimEnd([IO.Path]::DirectorySeparatorChar) + [IO.Path]::DirectorySeparatorChar), [StringComparison]::OrdinalIgnoreCase)) { throw 'Run root must be outside the source package.' }
$ReceiptPath = Join-Path $RunRoot 'receipt.json'

function Get-TestSha256([byte[]]$Bytes) {
    $sha = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($sha.ComputeHash($Bytes))).Replace('-', '').ToLowerInvariant() } finally { $sha.Dispose() }
}
function Assert-TestDirectoryUnredirected([string]$Path) {
    $cursor = [IO.DirectoryInfo]::new([IO.Path]::GetFullPath($Path))
    while ($null -ne $cursor) {
        $attributes = [IO.File]::GetAttributes($cursor.FullName)
        if (($attributes -band [IO.FileAttributes]::ReparsePoint) -or -not ($attributes -band [IO.FileAttributes]::Directory)) { throw ('Redirected or nondirectory path rejected: ' + $cursor.FullName) }
        $cursor = $cursor.Parent
    }
}
function Get-TestFileSnapshot([string]$Root) {
    Assert-TestDirectoryUnredirected $Root
    $snapshot = [ordered]@{}
    $pending = New-Object Collections.Generic.Queue[string]
    $pending.Enqueue($Root)
    while ($pending.Count -gt 0) {
        foreach ($entry in @([IO.Directory]::GetFileSystemEntries($pending.Dequeue()) | Sort-Object)) {
            $attributes = [IO.File]::GetAttributes($entry)
            if ($attributes -band [IO.FileAttributes]::ReparsePoint) { throw ('Redirected fixture entry rejected: ' + $entry) }
            if ($attributes -band [IO.FileAttributes]::Directory) { $pending.Enqueue($entry) }
            else { $snapshot[$entry.Substring($Root.Length)] = Get-TestSha256 ([IO.File]::ReadAllBytes($entry)) }
        }
    }
    return ($snapshot | ConvertTo-Json -Compress)
}

$inputsPath = Join-Path $PSScriptRoot 'GenerationUnavailableInputs.json'
$testSha256 = Get-TestSha256 ([IO.File]::ReadAllBytes($PSCommandPath))
$inputsSha256 = Get-TestSha256 ([IO.File]::ReadAllBytes($inputsPath))
$inputs = [IO.File]::ReadAllText($inputsPath) | ConvertFrom-Json
$sourceBefore = [ordered]@{}
$sourceAfter = [ordered]@{}
$definitions = @{}
$cases = @(
    [pscustomobject]@{ name='Get-LocalGenerationDispatchBinding'; operation='dispatch_binding'; arguments=@([pscustomobject]@{enabled=$true}) },
    [pscustomobject]@{ name='Assert-LocalGenerationDispatchBinding'; operation='dispatch_confirmation'; arguments=@([pscustomobject]@{enabled=$true},[pscustomobject]@{enabled=$true}) },
    [pscustomobject]@{ name='New-LocalGenerationJob'; operation='job_construction'; arguments=@('generate','',[pscustomobject]@{enabled=$true}) },
    [pscustomobject]@{ name='New-LocalGenerationJob'; operation='job_construction'; arguments=@('regenerate','gen-11111111111111111111111111111111',[pscustomobject]@{enabled=$true}) },
    [pscustomobject]@{ name='Start-LocalGenerationWorker'; operation='worker_launch'; arguments=@([pscustomobject]@{path='SYNTHETIC_EXISTING_JOB_DO_NOT_LAUNCH'}) },
    [pscustomobject]@{ name='Queue-LocalGeneration'; operation='queue_or_retry'; arguments=@('generate','',[pscustomobject]@{enabled=$true}) },
    [pscustomobject]@{ name='Queue-LocalGeneration'; operation='queue_or_retry'; arguments=@('regenerate','gen-11111111111111111111111111111111',[pscustomobject]@{enabled=$true}) },
    [pscustomobject]@{ name='Sync-LocalGenerationResults'; operation='result_import'; arguments=@() },
    [pscustomobject]@{ name='Invoke-GenerationSpoolMaintenance'; operation='spool_maintenance'; arguments=@() },
    [pscustomobject]@{ name='Invoke-ForgeLocalFlux'; operation='local_model_dispatch'; arguments=@([pscustomobject]@{job_id='gen-11111111111111111111111111111111'},'SYNTHETIC_CANCEL_PATH') },
    [pscustomobject]@{ name='Set-ForgeLocalFluxConfiguration'; operation='local_provider_configuration'; arguments=@() },
    [pscustomobject]@{ name='Assert-LocalGenerationAvailable'; operation='generation'; arguments=@() },
    [pscustomobject]@{ name='Initialize-GenerationWorkerBridge'; operation='inert_initialization'; arguments=@() }
)
$boundaryCommands = @(
    'Get-GenerationProviderRuntimeConfig', 'Get-LocalGenerationDispatchBinding',
    'Enter-LocalGenerationActionLock', 'New-LocalGenerationJob', 'Start-LocalGenerationWorker',
    'Get-PropertyValue', 'Test-Path', 'Get-ChildItem', 'Get-Content', 'Move-Item', 'Remove-Item',
    'Copy-Item', 'Set-Content', 'New-Item', 'Start-Process', 'Invoke-RestMethod', 'Invoke-WebRequest',
    'Assert-ForgeGenerationBriefComplete', 'Get-GenerationSpoolPolicy', 'Ensure-Dir',
    'Sync-LocalGenerationResults', 'Invoke-GenerationSpoolMaintenance', 'Confirm', 'Add-Type',
    'Add-LocalArtworkFromPath', 'Enter-LocalCoreMutationLock', 'Write-AppLog'
)
# REQUIRED PRECONDITION: the external supervisor exclusively creates this empty,
# owner-private LOCAL directory for this exact RunId and excludes other writers.
# This script checks freshness/redirection; it does not claim to provision ACLs.
Assert-TestDirectoryUnredirected $RunRoot
if (@([IO.Directory]::GetFileSystemEntries($RunRoot)).Count -ne 0) { throw 'Run root must be freshly provisioned and empty.' }
$claimStream = $null
$receiptStream = $null
try {
    # Fixed claim name prevents two different RunIds from sharing one run root.
    $claimStream = [IO.File]::Open((Join-Path $RunRoot '.forge-generation-boundary.claim'), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    $identityBytes = [Text.Encoding]::UTF8.GetBytes($RunId)
    $claimStream.Write($identityBytes, 0, $identityBytes.Length)
    $claimStream.Flush($true)
    Assert-TestDirectoryUnredirected $RunRoot
    # Hold an exclusive freshly created receipt handle. A crash leaves no PASS.
    $receiptStream = [IO.File]::Open($ReceiptPath, [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    $sandbox = Join-Path $RunRoot 'fixtures'
    if ([IO.Directory]::Exists($sandbox) -or [IO.File]::Exists($sandbox)) { throw 'Fixture root must not already exist.' }
[IO.Directory]::CreateDirectory($sandbox) | Out-Null
Assert-TestDirectoryUnredirected $sandbox
foreach ($subdir in @('outbox','results','attempts','receipts','assets','secrets')) { [IO.Directory]::CreateDirectory((Join-Path $sandbox $subdir)) | Out-Null }
# Intentionally synthetic sentinel bytes, not fabricated production jobs/approvals.
foreach ($entry in @('outbox/existing.json','results/existing.result.json','attempts/existing.attempt.json','receipts/existing.imported.json','assets/existing.png')) {
    $sentinelStream = [IO.File]::Open((Join-Path $sandbox $entry), [IO.FileMode]::CreateNew, [IO.FileAccess]::Write, [IO.FileShare]::None)
    try {
        $bytes = [Text.Encoding]::UTF8.GetBytes(('SYNTHETIC PRESERVATION SENTINEL: ' + $entry))
        $sentinelStream.Write($bytes, 0, $bytes.Length)
    } finally { $sentinelStream.Dispose() }
}
$stateBefore = Get-TestFileSnapshot $sandbox
$results = New-Object Collections.Generic.List[object]
$failure = $null
try {
    foreach ($inputFile in $inputs.files) {
        $path = Join-Path $PackageRoot $inputFile.path
        $actual = Get-TestSha256 ([IO.File]::ReadAllBytes($path))
        $sourceBefore[$inputFile.path] = $actual
        if ($actual -cne $inputFile.sha256) { throw ('Pinned source hash mismatch: ' + $inputFile.path) }
        $tokens = $null; $parseErrors = $null
        $ast = [Management.Automation.Language.Parser]::ParseFile($path, [ref]$tokens, [ref]$parseErrors)
        if (@($parseErrors).Count -ne 0) { throw ('PowerShell parser errors: ' + $inputFile.path) }
        foreach ($node in $ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]}, $true)) {
            if ($definitions.ContainsKey($node.Name)) { throw ('Duplicate function definition: ' + $node.Name) }
            $definitions[$node.Name] = $node.Extent.Text
        }
    }
    foreach ($case in $cases) {
        # Each case gets fresh actual entrypoint/helper definitions and synthetic doubles.
        & {
            param($case)
            $script:BoundaryHits = New-Object Collections.Generic.List[string]
            foreach ($helper in @('Get-LocalGenerationCapability','New-LocalGenerationUnavailableError','Assert-LocalGenerationAvailable',$case.name) | Select-Object -Unique) {
                if (-not $definitions.ContainsKey($helper)) { throw ('Missing actual function: ' + $helper) }
                . ([scriptblock]::Create($definitions[$helper]))
            }
            foreach ($command in $boundaryCommands) {
                if ($command -eq $case.name) { continue }
                $double = [scriptblock]::Create(("`$script:BoundaryHits.Add('" + $command + "'); throw 'SYNTHETIC BOUNDARY REACHED: " + $command + "'"))
                Set-Item -Path ('Function:' + $command) -Value $double
            }
            $script:Current = [pscustomobject]@{concept=[pscustomobject]@{synthetic_only=$true}}
            $script:Busy = $false
            $script:GenerationRoot = $sandbox
            $script:GenerationOutboxRoot = Join-Path $sandbox 'outbox'
            $script:GenerationResultRoot = Join-Path $sandbox 'results'
            $script:GenerationAttemptRoot = Join-Path $sandbox 'attempts'
            $script:GenerationReceiptRoot = Join-Path $sandbox 'receipts'
            $script:ProviderSecretRoot = Join-Path $sandbox 'secrets'
            $script:ProviderConfigPath = Join-Path $sandbox 'provider-config.json'
            $script:GenerationWorkerPath = Join-Path $sandbox 'NO_WORKER_EXISTS.ps1'
            $arguments = $case.arguments
            $caught = $null
            $output = $null
            try { $output = & $case.name @arguments } catch { $caught = $_.Exception }
            if ($case.name -eq 'Initialize-GenerationWorkerBridge') {
                if ($null -ne $caught) { throw $caught }
                if ($null -eq $output -or $output.available -isnot [bool] -or $output.available -or $output.code -cne 'matching_generation_worker_unavailable') { throw 'Initialization must return explicit unavailable status.' }
            } else {
                if ($null -eq $caught) { throw ('Entrypoint did not refuse: ' + $case.name) }
                if ($caught -isnot [NotSupportedException] -or $caught.Data['forge_generation_unavailable'] -ne $true -or $caught.Data['forge_generation_operation'] -cne $case.operation) { throw ('Wrong refusal from ' + $case.name + ': ' + $caught.Message) }
                if ($caught.Message -notlike 'Generation is unavailable in this package:*') { throw 'Missing truthful capability message.' }
                if ($null -ne $output) { throw 'Refusal emitted a success value.' }
            }
            if ($script:BoundaryHits.Count -ne 0) { throw ('Downstream boundary was reached: ' + ($script:BoundaryHits -join ', ')) }
            if ((Get-TestFileSnapshot $sandbox) -cne $stateBefore) { throw 'Synthetic existing artifacts changed or new artifacts appeared.' }
            $results.Add([pscustomobject]@{name=$case.name; operation=$case.operation; request_kind=($arguments | Select-Object -First 1); status='PASS'; downstream_boundary_hits=0; function_sha256=(Get-TestSha256 ([Text.Encoding]::UTF8.GetBytes($definitions[$case.name])))})
        } $case
    }
} catch { $failure = $_.Exception.Message }
finally {
    Assert-TestDirectoryUnredirected $RunRoot
    foreach ($inputFile in $inputs.files) {
        $path = Join-Path $PackageRoot $inputFile.path
        $sourceAfter[$inputFile.path] = Get-TestSha256 ([IO.File]::ReadAllBytes($path))
    }
    $sourcesUnchanged = (($sourceBefore | ConvertTo-Json -Compress) -ceq ($sourceAfter | ConvertTo-Json -Compress))
    $stateUnchanged = ((Get-TestFileSnapshot $sandbox) -ceq $stateBefore)
    if (-not $sourcesUnchanged -and $null -eq $failure) { $failure = 'Source hashes changed during regression.' }
    if (-not $stateUnchanged -and $null -eq $failure) { $failure = 'Synthetic preservation state changed.' }
    if ($results.Count -ne 13 -and $null -eq $failure) { $failure = 'Exactly 13 regression cases are required.' }
    if ($sourceBefore.Count -ne 5 -or $sourceAfter.Count -ne 5) { $failure = 'Exactly five before/after source hashes are required.' }
    if ((Get-TestSha256 ([IO.File]::ReadAllBytes($PSCommandPath))) -cne $testSha256 -or (Get-TestSha256 ([IO.File]::ReadAllBytes($inputsPath))) -cne $inputsSha256) { $failure = 'Test or input manifest changed during regression.' }
    $receipt = [ordered]@{
        schema='forge.synthetic_generation_unavailable_regression.v1'; run_id=$RunId
        started_at_utc=$startedAt; finished_at_utc=[DateTime]::UtcNow.ToString('o')
        status=$(if($null -eq $failure){'PASS'}else{'FAIL'}); error=$failure
        scope='Actual changed function ASTs, synthetic downstream boundary doubles only'
        powershell_version=$PSVersionTable.PSVersion.ToString(); generation_available=$false
        app_launched=$false; worker_launched=$false; model_or_provider_called=$false
        test_sha256=$testSha256; inputs_sha256=$inputsSha256; supervisor_private_run_root=$RunRoot
        source_hashes_before=$sourceBefore; source_hashes_after=$sourceAfter; sources_unchanged=$sourcesUnchanged
        synthetic_artifacts_unchanged=$stateUnchanged; synthetic_fixture_root=$sandbox
        cases=@($results.ToArray())
    }
    $writer = [IO.StreamWriter]::new($receiptStream, [Text.UTF8Encoding]::new($false), 4096, $true)
    try {
        $writer.Write(($receipt | ConvertTo-Json -Depth 12))
        $writer.Flush()
        $receiptStream.Flush($true)
    } finally { $writer.Dispose() }
}
Write-Output ('Fresh synthetic regression receipt: ' + $ReceiptPath)
if ($null -ne $failure) { throw $failure }
} finally {
    if ($null -ne $receiptStream) { $receiptStream.Dispose() }
    if ($null -ne $claimStream) { $claimStream.Dispose() }
}
