# Focused native regression, not a full application test. No top-level app code is loaded.
# Requires an already installed PowerShell Core 7.5+ stable on Windows and external timeout supervision.
# The supervisor supplies a fresh invocation directory/run ID. No existing receipt is reusable.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ModuleRoot,
    [Parameter(Mandatory=$true)][string]$InvocationRoot,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{32}$')][string]$RunId,
    [Parameter(Mandatory=$true)][string]$SourceManifest,
    [Parameter(Mandatory=$true)][ValidatePattern('^[0-9a-f]{64}$')][string]$ExpectedSourceManifestSha256,
    [switch]$ExternalSupervisorConfirmed
)
$ErrorActionPreference = 'Stop'
$started = [DateTime]::UtcNow.ToString('o')
$script:Cases = New-Object 'Collections.Generic.List[object]'
$script:Loaded = New-Object 'Collections.Generic.List[object]'
$script:Sources = New-Object 'Collections.Generic.List[object]'
$script:ControlSources = New-Object 'Collections.Generic.List[object]'
$script:Assertions = 0
$script:ForbiddenAttempts=New-Object 'Collections.Generic.List[string]'
$script:ImportStatePath=$null
$script:Current = $null
$script:Dirty = $false
$script:PublicationDirty = $false
$script:Observed = New-Object 'Collections.Generic.List[object]'
$status = 'FAIL'
# This check rejects redirection, not unsafe ACLs. The separately reviewed
# external supervisor must provision and verify the Windows owner-private ACL
# before invoking this script. A switch is acknowledgement, not an ACL proof.
function Assert-TestNonredirectedPath([string]$Path) {
    $current=[IO.Path]::GetFullPath($Path)
    while($current) {
        $item=Get-Item -LiteralPath $current -Force -ErrorAction Stop
        if($item.Attributes -band [IO.FileAttributes]::ReparsePoint) {throw ('Redirected path component: '+$current)}
        $parent=[IO.Path]::GetDirectoryName($current)
        if(!$parent -or $parent -ceq $current){break}
        $current=$parent
    }
}
foreach($path in @($InvocationRoot,$ModuleRoot,$SourceManifest,$PSCommandPath)) { Assert-TestNonredirectedPath $path }
$receiptPath = Join-Path $InvocationRoot 'native-receipt.json'
$script:FixtureRoot = Join-Path $InvocationRoot 'owned-fixtures'
if (!(Test-Path -LiteralPath $InvocationRoot -PathType Container) -or
    (Test-Path -LiteralPath $receiptPath) -or (Test-Path -LiteralPath $script:FixtureRoot)) {
    throw 'Supervisor must supply a fresh invocation directory without a receipt or fixtures.'
}
if ((Get-Item -LiteralPath $InvocationRoot -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) {
    throw 'Invocation directory must not be a reparse point.'
}
[void][IO.Directory]::CreateDirectory($script:FixtureRoot)

function Get-TestHash([byte[]]$Bytes) {
    $hash = [Security.Cryptography.SHA256]::Create()
    try { return ([BitConverter]::ToString($hash.ComputeHash($Bytes))).Replace('-','').ToLowerInvariant() }
    finally { $hash.Dispose() }
}
function Get-TestJson($Value) { return ConvertTo-Json -InputObject $Value -Depth 60 -Compress }
function Assert-Test([bool]$Condition,[string]$Message) {
    $script:Assertions++
    if (!$Condition) { throw ('CHECK_FAILED: '+$Message) }
}
function Invoke-TestCase([string]$Name,[scriptblock]$Body) {
    try { & $Body; $script:Cases.Add([pscustomobject]@{name=$Name;status='PASS';detail=''}) }
    catch { $script:Cases.Add([pscustomobject]@{name=$Name;status='FAIL';detail=$_.Exception.Message}) }
}
function Write-TestJson([string]$Path,$Value) {
    [IO.File]::WriteAllText($Path,(Get-TestJson $Value),(New-Object Text.UTF8Encoding($false)))
}

# EXPLICIT PREREQUISITE DOUBLES. They do not replace package/ZIP/hash/content authority.
# The inherited prerequisite doubles isolate filesystem state loading, review/check prerequisites,
# current print capture, semantic-review outcome, and unrelated sales reconciliation.
function Read-LocalCoreState {
    $script:StateReadCalls++
    if ($script:StateReadThrows) { throw 'SYNTHETIC_STATE_UNAVAILABLE' }
    if($script:ImportStatePath){return (Get-ImportFixtureState)}
    return ((Get-TestJson $script:PersistedState)|ConvertFrom-Json -DateKind String)
}
function Get-LocalPackageBriefApprovalSnapshot($Lc,$Identity) {
    return [pscustomobject]@{approved=$script:ApprovalReady;brief_sha256=('b'*64);reason='SYNTHETIC_PREREQUISITE_ONLY'}
}
function Get-LocalCheckGateSnapshot($Lc) {
    return [pscustomobject]@{all_ready=$script:ChecksReady;checks=$script:GateChecks}
}
function Get-LocalPrintProductionSnapshot($Lc,$Identity,$Acceptance) {
    # Always a labeled synthetic current-capture prerequisite. Actual archived
    # profile, bytes, expiry, lineage and PNG validators still execute unchanged.
    return [pscustomobject]@{ready=$script:PrintReady;channel_profile=$script:Profile;reason='SYNTHETIC_PREREQUISITE_ONLY'}
}
function Test-ForgeSemanticReviewCurrent($Draft) {
    $script:SemanticCalls++
    return $script:SemanticReviewCurrent
}
function Reconcile-LocalSalesLinks($State) {
    $script:SalesReconcileCalls++
    if (@($State.sales_rows).Count -ne 0) { throw 'This focused harness allows only empty sales data.' }
}
# Only the profile storage location is redirected; its parser/expiry logic is real.
function Get-LocalAmazonPrintProfilePath { return (Join-Path $script:CaseRoot 'current-profile.json') }

function New-TestFixture([switch]$Expired) {
    $script:CaseRoot = Join-Path $script:FixtureRoot ([Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($script:CaseRoot)
    $script:ImportStatePath=$null
    $script:StateReadCalls=0; $script:SemanticCalls=0; $script:SalesReconcileCalls=0
    $script:StateReadThrows=$false; $script:SemanticReviewCurrent=$false
    $script:ApprovalReady=$true; $script:ChecksReady=$true; $script:PrintReady=$true
    $script:Now=[DateTime]::UtcNow
    $created=$script:Now.AddDays(-10).ToString('o')
    $valid=if($Expired){$script:Now.AddDays(-1).ToString('o')}else{$script:Now.AddDays(60).ToString('o')}
    $script:Profile=[pscustomobject][ordered]@{
        schema='forge.amazon_print_profile.v1';authority_kind='owner_attested_external';attested=$true;independent_verification=$false
        marketplace='US';product_type_key='SYNTHETIC_TEST';template_key='SYNTHETIC_500';file_format='png';background='transparent'
        canvas_width_px=500;canvas_height_px=500;dpi=300;template_file_sha256=('d'*64);source_file_sha256=('e'*64)
        source_refs=@('https://merch.amazon.com/');captured_at=$script:Now.AddDays(-20).ToString('o');valid_until=$valid
    }
    Write-TestJson (Get-LocalAmazonPrintProfilePath) $script:Profile
    $artPath=Join-Path $script:CaseRoot 'artwork.png'
    $bitmap=New-Object Drawing.Bitmap 500,500,([Drawing.Imaging.PixelFormat]::Format32bppArgb)
    try {
        $graphics=[Drawing.Graphics]::FromImage($bitmap)
        try { $graphics.Clear([Drawing.Color]::Transparent);$graphics.FillRectangle([Drawing.Brushes]::Black,200,200,100,100) }
        finally { $graphics.Dispose() }
        $bitmap.Save($artPath,[Drawing.Imaging.ImageFormat]::Png)
    } finally { $bitmap.Dispose() }
    $artSha=Get-FileSha256Hex $artPath
    $publication=[pscustomobject][ordered]@{
        listing_title='SYNTHETIC package authority fixture';brand='Test only';bullet_1='Not a real listing';bullet_2='No commercial use'
        description='Owned synthetic regression fixture. No submission.';keywords=@('synthetic');locale='en_US';acceptance_fingerprint=('f'*64)
    }
    $script:Lc=[pscustomobject]@{
        concept_key='synthetic-package-authority';title='SYNTHETIC package';source_revision_id='synthetic-revision-1';source_revision_hash=('a'*64)
        owner_decision='KEEP';owner_decision_revision_id='synthetic-revision-1';owner_decision_revision_hash=('a'*64)
        active_acceptance=[pscustomobject]@{concept_revision_id='synthetic-revision-1';revision_hash=('a'*64);lineage_fingerprint=('f'*64);asset_sha256=$artSha;local_file_path=$artPath}
        publication=$publication;packages=@()
    }
    $script:Package=[pscustomobject]@{
        path=(Join-Path $script:CaseRoot 'package.zip');sha256='';status='READY_FOR_MANUAL_UPLOAD';valid=$true
        concept_revision_id='synthetic-revision-1';revision_hash=('a'*64);acceptance_fingerprint=('f'*64);artwork_sha256=$artSha
        listing_hash=(Get-LocalPublicationHash $publication);preupload_gate_sha256='';print_production_sha256=''
        marketplace='US';product_type_key='SYNTHETIC_TEST';template_key='SYNTHETIC_500';created_at=$created;channel_profile_valid_until=$valid
    }
    $script:GateChecks=[pscustomobject]@{}
    foreach($name in @('ip','visual','print','policy','metadata')) {
        $script:GateChecks | Add-Member -NotePropertyName $name -NotePropertyValue ([pscustomobject]@{ready=$true;state='pass'})
    }
    $approval=[pscustomobject]@{approved=$true;brief_sha256=('b'*64)}
    $lineage=[pscustomobject]@{concept_revision_id=$script:Package.concept_revision_id;revision_hash=$script:Package.revision_hash;acceptance_fingerprint=$script:Package.acceptance_fingerprint;accepted_artwork_sha256=$artSha;listing_hash=$script:Package.listing_hash}
    $script:ArchivedPrint=[pscustomobject]@{
        schema='forge.print_production_snapshot.v1';ready=$true;technical_ready=$true;quality_reviewed=$true;channel_profile=$script:Profile
        concept_revision_id=$script:Package.concept_revision_id;revision_hash=$script:Package.revision_hash;acceptance_fingerprint=$script:Package.acceptance_fingerprint;artwork_sha256=$artSha
    }
    $script:ArchivedGate=[pscustomobject]@{
        schema='forge.preupload_gate.v1';status='READY_FOR_MANUAL_UPLOAD';concept_key=$script:Lc.concept_key;lineage=$lineage
        all_checks_ready=$true;idea_and_design_approved=$true;print_production_ready=$true;concept_approval=$approval;checks=$script:GateChecks
        print_production_sha256='';external_submission_authorized=$false;created_at=$created
    }
    $script:ArchivedMetadata=[pscustomobject]@{
        schema='forge.amazon_manual_package.v3';status='READY_FOR_MANUAL_UPLOAD';concept_key=$script:Lc.concept_key;lineage=$lineage
        manual_upload_required=$true;external_submission_authorized=$false;concept_approval=$approval;print_production_sha256=''
        print_production=$script:ArchivedPrint;listing=$publication;accepted_artwork=[pscustomobject]@{file='artwork.png';sha256=$artSha}
    }
    $script:Lc.packages=@($script:Package)
    $script:State=[pscustomobject]@{concepts=@($script:Lc);research_drafts=@();publication_receipts=@();sales_rows=@()}
    $script:PersistedState=$script:State
    Save-TestArchive
}
function Save-TestArchive {
    # A fresh physical ZIP every time; old fixtures stay in this invocation's root.
    $stage=Join-Path $script:CaseRoot ('stage-'+[Guid]::NewGuid().ToString('N'))
    [void][IO.Directory]::CreateDirectory($stage)
    Copy-Item -LiteralPath (Join-Path $script:CaseRoot 'artwork.png') -Destination (Join-Path $stage 'artwork.png')
    Write-TestJson (Join-Path $stage 'print-production.json') $script:ArchivedPrint
    $script:Package.print_production_sha256=Get-FileSha256Hex (Join-Path $stage 'print-production.json')
    $script:ArchivedGate.print_production_sha256=$script:Package.print_production_sha256
    $script:ArchivedMetadata.print_production_sha256=$script:Package.print_production_sha256
    Write-TestJson (Join-Path $stage 'preupload-gate.json') $script:ArchivedGate
    Write-TestJson (Join-Path $stage 'metadata.json') $script:ArchivedMetadata
    $script:Package.preupload_gate_sha256=Get-FileSha256Hex (Join-Path $stage 'preupload-gate.json')
    $script:Package.path=Join-Path $script:CaseRoot ('package-'+[Guid]::NewGuid().ToString('N')+'.zip')
    [IO.Compression.ZipFile]::CreateFromDirectory($stage,$script:Package.path)
    $script:Package.sha256=Get-FileSha256Hex $script:Package.path
}
function Assert-Surfaces([bool]$ExpectedReady,[string]$Label,[string]$ExpectedStage='') {
    $before=Get-TestJson $script:State
    $authority=Test-LocalPackageCurrentAuthority $script:Package $script:Lc $null $script:State
    Assert-Test ($authority -is [bool] -and $authority -eq $ExpectedReady) ($Label+': actual current authority')
    $script:StateReadCalls=0
    $stage=Get-ForgePipelineStage $script:State $script:Lc $script:Lc.concept_key
    $stageReads=$script:StateReadCalls
    if($ExpectedStage){Assert-Test ($stage -ceq $ExpectedStage) ($Label+': expected fallback stage')}
    else {Assert-Test (($stage -ceq 'package_ready') -eq $ExpectedReady) ($Label+': actual Pipeline stage')}
    $script:StateReadCalls=0
    $insights=Get-ForgePerformanceInsights $script:State $script:Now
    $insightReads=$script:StateReadCalls
    $unpublished=@($insights.attention | Where-Object {$_.kind -ceq 'unpublished'})
    Assert-Test (($unpublished.Count -eq 1) -eq $ExpectedReady) ($Label+': actual Performance unpublished attention')
    Assert-Test ($unpublished.Count -le 1) ($Label+': no duplicated attention')
    Assert-Test ($stageReads -gt 0 -and $insightReads -gt 0) ($Label+': both entrypoints traverse real authority HOLD state read')
    Assert-Test ((Get-TestJson $script:State) -ceq $before) ($Label+': entrypoints do not mutate fixture state')
    $script:Observed.Add([pscustomobject]@{label=$Label;authority=$authority;stage=$stage;unpublished_count=$unpublished.Count;stage_authority_state_reads=$stageReads;insights_authority_state_reads=$insightReads})
}
function Add-TestPublication {
    $script:State.publication_receipts=@([pscustomobject]@{
        concept_key=$script:Lc.concept_key;lineage_verified=$true;package_sha256=$script:Package.sha256
        lineage_fingerprint=$script:Package.acceptance_fingerprint;listing_hash=$script:Package.listing_hash
        preupload_gate_sha256=$script:Package.preupload_gate_sha256;print_production_sha256=$script:Package.print_production_sha256
        channel='amazon_merch';marketplace='US';product_id='SYNTHETIC-PRODUCT';published_at=$script:Now.AddDays(-9).ToString('o')
    })
}

# Focused receipt-import seams: owned detached JSON state, confirmation and UI only.
# Archive/PNG/receipt JSON/lineage/binding authority remains actual production code.
function Get-ImportFixtureState {return (ConvertFrom-ForgeJsonObjectStrict ([IO.File]::ReadAllText($script:ImportStatePath)))}
function Save-ImportFixtureState($Value) {Write-TestJson $script:ImportStatePath $Value}
function Write-LocalCoreState($Value) {
    if(!$script:ImportStatePath){throw 'Unexpected mutation outside receipt fixture.'}
    $script:ImportWriteAttempts++
    if($script:ImportBeforeWrite){& $script:ImportBeforeWrite}
    if($script:ImportRejectWrite){throw 'SYNTHETIC_WRITE_REJECTED'}
    $disk=Get-ImportFixtureState
    if($disk.state_revision-ne$Value.state_revision-or[string]$disk.last_write_id-cne[string]$Value.last_write_id){throw 'SYNTHETIC_CAS_CONFLICT'}
    $Value.state_revision++;$Value.last_write_id=[guid]::NewGuid().ToString('N');Save-ImportFixtureState $Value;$script:ImportWrites++
    if($script:ImportCommitThenThrow){throw 'SYNTHETIC_COMMITTED_THEN_VERIFICATION_ERROR'}
}
function Confirm([string]$Message,[string]$Title){
    $script:ImportQuestions.Add($Message)
    if($script:ImportOnConfirm){& $script:ImportOnConfirm}
    if($script:ImportAnswers.Count-eq0){throw 'Unexpected receipt-import confirmation.'}
    return $script:ImportAnswers.Dequeue()
}
function Show-Error([string]$Message){$script:ImportErrors.Add($Message)}
function Update-LocalCoreBusinessSurfaces {$script:ImportUiRefreshes++;if($script:ImportUiThrows){throw 'SYNTHETIC_UI_REFRESH_FAILURE'}}
function Write-AppLog([string]$Level,[string]$Message){$script:ImportLogs.Add($Level+':'+$Message)}
function Reset-ImportObservations {
    $script:ImportWriteAttempts=0;$script:ImportWrites=0;$script:ImportUiRefreshes=0;$script:ImportRejectWrite=$false;$script:ImportCommitThenThrow=$false;$script:ImportUiThrows=$false;$script:ImportBeforeWrite=$null;$script:ImportOnConfirm=$null
    $script:ImportQuestions=New-Object 'Collections.Generic.List[string]';$script:ImportErrors=New-Object 'Collections.Generic.List[string]';$script:ImportLogs=New-Object 'Collections.Generic.List[string]';$script:ImportAnswers=New-Object 'Collections.Generic.Queue[bool]'
    $script:StatusText=[pscustomobject]@{Text='before import'}
}
function New-TestReceiptDocument {
    return [pscustomobject][ordered]@{schema='forge.local_publication_receipt.v3';concept_key=$script:Lc.concept_key;package_sha256=$script:Package.sha256;lineage_fingerprint=$script:Package.acceptance_fingerprint;listing_hash=$script:Package.listing_hash;preupload_gate_sha256=$script:Package.preupload_gate_sha256;print_production_sha256=$script:Package.print_production_sha256;channel='amazon_merch';marketplace='US';product_id='SYNTHETIC-LATE-PRODUCT';published_at=$script:Now.AddDays(-9).ToString('o');source='owner-provided synthetic receipt';note='Synthetic owner attestation; not independent publication verification.'}
}
function Save-TestReceiptDocument($Document) {Write-TestJson $script:ReceiptPath $Document}
function New-ReceiptImportFixture([bool]$Historical=$true) {
    # Expired NOW but valid at the declared past event; the real archived date checks execute.
    New-TestFixture -Expired
    $script:Package.valid=!$Historical
    $script:Package|Add-Member -NotePropertyName invalidated_at -NotePropertyValue ($script:Now.AddDays(-2).ToString('o'))
    $script:Package|Add-Member -NotePropertyName invalidation_reason -NotePropertyValue 'local_acceptance_reopened'
    $script:Lc.active_acceptance=$null
    $script:Lc|Add-Member -NotePropertyName brief_approval -NotePropertyValue ([pscustomobject]@{approval_id='old-approval';approved=$true;marker='unchanged synthetic historical idea decision'})
    $script:Lc|Add-Member -NotePropertyName checks -NotePropertyValue ([pscustomobject]@{visual=[pscustomobject]@{state='needs_review';note='withdrawn exact acceptance'}})
    $script:Lc|Add-Member -NotePropertyName review_history -NotePropertyValue @([pscustomobject]@{history_only=$true;reason='artwork_acceptance_reopened';owner_reason='original reason';payload=[pscustomobject]@{timestamp='2026-01-02T03:04:05.1234000+05:45';nested=@('singleton')}})
    $script:Lc|Add-Member -NotePropertyName artwork -NotePropertyValue @([pscustomobject]@{local_file_path=(Join-Path $script:CaseRoot 'artwork.png');asset_sha256=$script:Package.artwork_sha256;accepted=$false})
    $script:State|Add-Member -NotePropertyName state_revision -NotePropertyValue 5
    $script:State|Add-Member -NotePropertyName last_write_id -NotePropertyValue ('1'*32)
    $script:ImportStatePath=Join-Path $script:CaseRoot 'synthetic-state.json';Save-ImportFixtureState $script:State
    $script:ReceiptPath=Join-Path $script:CaseRoot 'owner-receipt.json';Save-TestReceiptDocument (New-TestReceiptDocument)
    Reset-ImportObservations
    Assert-Test ($null-ne(Get-LocalReadyPackageZipAuthority $script:Package.path $script:Package $script:Lc.concept_key)) 'Import fixture positive real ZIP/PNG/strict-JSON authority control.'
}
function Assert-ImportNoWrite([string]$Before,[string]$Label){
    Assert-Test ($script:ImportWrites-eq0) ($Label+': no synthetic commit')
    Assert-Test ((Get-FileSha256Hex $script:ImportStatePath)-ceq$Before) ($Label+': saved state bytes preserved')
}
function Import-TestHistoricalReceipt {
    $script:ImportAnswers.Enqueue($true);Import-LocalPublicationReceiptFromPath $script:ReceiptPath
    Assert-Test ($script:ImportErrors.Count-eq0) ('Actual importer accepted fixture: '+($script:ImportErrors-join' | '))
    Assert-Test ($script:ImportWrites-eq1) 'Exactly one synthetic state commit.'
    return (Get-ImportFixtureState)
}
function Bump-ImportFixtureState {
    $state=Get-ImportFixtureState;$state.state_revision++;$state.last_write_id=[guid]::NewGuid().ToString('N');$state.concepts[0].owner_decision='EDIT';Save-ImportFixtureState $state
}
foreach($command in @('Invoke-ForgeApi','Start-LocalGenerationWorker','Invoke-ForgeLocalFlux','Sync-LocalGenerationResults','Invoke-LocalCheckAutomation','Build-LocalAmazonPackage','New-ForgeBriefApprovalRecord','Start-Process','Invoke-WebRequest','Invoke-RestMethod')){
    Set-Item -Path ('Function:'+$command) -Value ([scriptblock]::Create("`$script:ForbiddenAttempts.Add('$command');throw 'Unexpected external boundary: $command'"))
}

try {
    if (!$ExternalSupervisorConfirmed) { throw 'External timeout and fresh receipt supervisor is required.' }
    $runtimeText=[string]$PSVersionTable.PSVersion
    if ($PSVersionTable.PSEdition -cne 'Core' -or $runtimeText -notmatch '^\d+\.\d+\.\d+(?:\.\d+)?$' -or [version]$runtimeText -lt [version]'7.5' -or [Environment]::OSVersion.Platform -ne [PlatformID]::Win32NT) {
        throw 'Already installed stable PowerShell Core 7.5+ on Windows is required. Preview/Desktop/non-Windows hosts are unsupported. Do not install from this test.'
    }
    if (!(Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind')) { throw 'Native DateKind String support is required.' }
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    Add-Type -AssemblyName System.Drawing
    Assert-Test ((Get-TestHash ([IO.File]::ReadAllBytes($SourceManifest))) -ceq $ExpectedSourceManifestSha256) 'Exact externally pinned source manifest.'
    $script:ControlSources.Add([pscustomobject]@{name='source manifest';path=$SourceManifest;before_sha256=$ExpectedSourceManifestSha256;after_sha256=''})
    $manifest=Get-Content -LiteralPath $SourceManifest -Raw -Encoding UTF8 | ConvertFrom-Json -DateKind String
    Assert-Test ($manifest.schema -ceq 'forge.pipeline_package_authority.source_lock.v1') 'Expected source manifest schema.'
    $testRoot=Split-Path -Parent $PSCommandPath
    foreach($control in $manifest.test_sources) {
        if([string]$control.path -cne 'Test-PipelinePackageAuthority.ps1'){throw 'Unexpected native test source path.'}
        $path=Join-Path $testRoot $control.path;Assert-TestNonredirectedPath $path
        $hash=Get-TestHash ([IO.File]::ReadAllBytes($path))
        Assert-Test ($hash -ceq $control.sha256) ('Pinned test source: '+$control.path)
        $script:ControlSources.Add([pscustomobject]@{name=[string]$control.path;path=$path;before_sha256=$hash;after_sha256=''})
    }
    Assert-Test (@($manifest.test_sources).Count -eq 1) 'Exact single native test source is pinned.'
    $appRoot=Split-Path -Parent $ModuleRoot
    $targets=[ordered]@{
        'Modules/Forge.Pipeline.ps1'=@('Get-ForgePipelineStage','ConvertTo-PerfUtc','Get-ForgePerformanceInsights')
        'Modules/Forge.LocalCore.ps1'=@('Get-StringSha256Hex','Get-LocalPublicationHash','Get-FileSha256Hex','Get-LocalCoreConcept','Get-LocalOwnerDecisionRecord','Get-LocalDeliveryReadiness','Test-LocalPackageCurrentAuthority','Get-LocalPackageZipEntrySha256','Test-LocalPackageBoolean','Get-LocalPackageZipJsonEntry','Test-LocalPackageArtworkTechnical','Get-LocalReadyPackageZipAuthority','Get-LocalPublicationProductKey','Test-LocalPublicationReceiptAuthority','Assert-ForgeNoSemanticHold','Get-LocalSalesRawProperty','Get-LocalSalesUtcDay','Get-LocalSalesCalendarDate','Get-LocalVerifiedSalesAmount','Resolve-LocalSalesCurrency','Get-LocalRoyaltyTotals','Get-LocalSalesTotals','Read-LocalCheckEvidencePayload','Get-LocalPublicationReceiptBindingDecision','Import-LocalPublicationReceiptFromPath')
        'Modules/Forge.ImageValidation.ps1'=@('Read-ForgeUInt32BE','Get-ForgePngMetadata','Test-ForgeGenerationPngBytes','Test-ForgePrintPngBytes','Test-ForgeFlexibleUploadRules','Test-ForgeAmazonPrintProfile','Get-ForgeUploadTechnicalSnapshot')
        'Modules/Forge.Media.ps1'=@('Get-ByteSha256Hex')
        'Modules/Forge.ResearchDrafts.ps1'=@('Get-ResearchDraftList','Get-ResearchDraft')
        'Modules/Forge.BriefApproval.ps1'=@('ConvertFrom-ForgeJsonObjectStrict')
        'Modules/Forge.StrictJsonSyntax.ps1'=@('Assert-ForgeStrictJsonSyntax')
        'Modules/Forge.PrintChecks.ps1'=@('ConvertTo-ForgeUtcDateTime','Get-LocalAmazonPrintProfile')
        'MerchForgeWorkbench.ps1'=@('Get-PropertyValue')
    }
    Assert-Test ((@($manifest.application_sources | ForEach-Object {$_.path}) -join '|') -ceq (@($targets.Keys) -join '|')) 'Exact ordered application source set.'
    $expectedFunctionCount=0
    foreach($relative in $targets.Keys) {
        $source=Join-Path $appRoot $relative
        Assert-TestNonredirectedPath $source
        $bytes=[IO.File]::ReadAllBytes($source);$beforeHash=Get-TestHash $bytes
        $expected=@($manifest.application_sources | Where-Object {$_.path -ceq $relative})
        Assert-Test ($expected.Count -eq 1 -and $beforeHash -ceq $expected[0].sha256) ('Pinned source hash: '+$relative)
        $copy=Join-Path $script:FixtureRoot ($relative.Replace('/','_'))
        [IO.File]::WriteAllBytes($copy,$bytes)
        $record=[pscustomobject]@{path=$source;relative=$relative;before_sha256=$beforeHash;after_sha256='';copy_path=$copy;copy_before_sha256=(Get-TestHash ([IO.File]::ReadAllBytes($copy)));copy_after_sha256=''}
        $script:Sources.Add($record)
        Assert-Test ($record.copy_before_sha256 -ceq $beforeHash) ('Byte-exact owned source copy: '+$relative)
        $tokens=$null;$errors=$null
        $ast=[Management.Automation.Language.Parser]::ParseFile($copy,[ref]$tokens,[ref]$errors)
        Assert-Test (@($errors).Count -eq 0) ('Native parse: '+$relative)
        foreach($name in $targets[$relative]) {
            $expectedFunctionCount++
            $matches=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]},$false) | Where-Object {$_.Name -ceq $name})
            Assert-Test ($matches.Count -eq 1) ('Unique source function: '+$name)
            $definition=$matches[0]
            . ([scriptblock]::Create($definition.Extent.Text))
            $loaded=Get-Command -Name $name -CommandType Function
            Assert-Test ($loaded.ScriptBlock.Ast.Extent.Text -ceq $definition.Body.Extent.Text) ('Exact actual source body: '+$name)
            $script:Loaded.Add([pscustomobject]@{name=$name;source=$relative;line=$definition.Extent.StartLineNumber;definition_sha256=(Get-TestHash ([Text.Encoding]::UTF8.GetBytes($definition.Extent.Text)));body_sha256=(Get-TestHash ([Text.Encoding]::UTF8.GetBytes($definition.Body.Extent.Text)))})
        }
    }
    Assert-Test ($script:Loaded.Count -eq $expectedFunctionCount) 'All actual functions loaded, not module startup.'
    Assert-Test ((@($script:Loaded | ForEach-Object {$_.name}) -join '|') -ceq (@($manifest.expected_loaded_functions) -join '|')) 'Exact ordered loaded-function contract.'

    Invoke-TestCase 'Current valid noncanonical physical package is ready on both surfaces' {
        New-TestFixture
        Assert-Test ($null -ne (Get-LocalReadyPackageZipAuthority $script:Package.path $script:Package $script:Lc.concept_key)) 'Positive archive control must pass actual ZIP and PNG authority.'
        Assert-Surfaces $true 'valid noncanonical' 'package_ready'
    }
    foreach($variant in @('string_false','boolean_false','draft_status','stale_revision','stale_listing_hash')) {
        Invoke-TestCase ('Saved flags cannot confer authority: '+$variant) {
            New-TestFixture
            switch($variant) {
                'string_false' {$script:Package.valid='false'}
                'boolean_false' {$script:Package.valid=$false}
                'draft_status' {$script:Package.status='DRAFT_BLOCKED'}
                'stale_revision' {$script:Package.concept_revision_id='older-revision'}
                'stale_listing_hash' {$script:Package.listing_hash=('0'*64)}
            }
            Assert-Surfaces $false $variant 'checks_ready'
        }
    }
    Invoke-TestCase 'Missing physical ZIP cannot remain package ready' {
        New-TestFixture
        $script:Package.path=Join-Path $script:CaseRoot 'never-created.zip'
        Assert-Surfaces $false 'missing ZIP' 'checks_ready'
    }
    Invoke-TestCase 'Tampered physical ZIP with unchanged saved hash is rejected' {
        New-TestFixture
        $stream=[IO.File]::Open($script:Package.path,[IO.FileMode]::Append,[IO.FileAccess]::Write)
        try {$stream.WriteByte(42)}finally{$stream.Dispose()}
        Assert-Test ((Get-FileSha256Hex $script:Package.path) -cne $script:Package.sha256) 'Tamper control changes actual ZIP bytes.'
        Assert-Surfaces $false 'tampered ZIP' 'checks_ready'
    }
    Invoke-TestCase 'Self-consistent archive hashes cannot hide an invalid archived gate' {
        New-TestFixture
        $script:ArchivedGate.all_checks_ready=$false
        Save-TestArchive
        Assert-Test ((Get-FileSha256Hex $script:Package.path) -ceq $script:Package.sha256) 'ZIP hash is refreshed so actual content validation is required.'
        Assert-Test ($null -eq (Get-LocalReadyPackageZipAuthority $script:Package.path $script:Package $script:Lc.concept_key)) 'Real archive authority rejects gate content.'
        Assert-Surfaces $false 'invalid archive content' 'checks_ready'
    }
    Invoke-TestCase 'Changed current listing invalidates a previously valid package' {
        New-TestFixture
        # The JSON in the already-written archive is unchanged; current state changes.
        $script:Lc.publication.listing_title='SYNTHETIC changed listing'
        Assert-Test ($null -ne (Get-LocalReadyPackageZipAuthority $script:Package.path $script:Package $script:Lc.concept_key)) 'Historical archive remains internally valid.'
        Assert-Surfaces $false 'changed listing' 'checks_ready'
    }
    Invoke-TestCase 'Expired archived profile cannot remain ready even with ready prerequisites' {
        New-TestFixture -Expired
        Assert-Test ($null -ne (Get-LocalReadyPackageZipAuthority $script:Package.path $script:Package $script:Lc.concept_key)) 'Historically valid archive control remains independently valid.'
        Assert-Test ($script:PrintReady) 'Expiry rejection must not be supplied by a fake readiness failure.'
        Assert-Surfaces $false 'expired archived profile' 'checks_ready'
    }
    Invoke-TestCase 'Changed current profile invalidates an internally valid old archive' {
        New-TestFixture
        $script:Profile=Get-TestJson $script:Profile | ConvertFrom-Json -DateKind String
        $script:Profile.template_file_sha256=('9'*64)
        Write-TestJson (Get-LocalAmazonPrintProfilePath) $script:Profile
        Assert-Test ($null -ne (Get-LocalReadyPackageZipAuthority $script:Package.path $script:Package $script:Lc.concept_key)) 'Archive is still valid against its captured profile.'
        Assert-Surfaces $false 'changed current profile' 'checks_ready'
    }
    foreach($prerequisite in @('approval','checks','print')) {
        Invoke-TestCase ('Current readiness loss overrides old ready flags: '+$prerequisite) {
            New-TestFixture
            switch($prerequisite) {'approval' {$script:ApprovalReady=$false};'checks' {$script:ChecksReady=$false};'print' {$script:PrintReady=$false}}
            Assert-Surfaces $false ('current '+$prerequisite)
        }
    }
    Invoke-TestCase 'Later semantic HOLD is enforced by the actual persisted-state guard' {
        New-TestFixture
        Assert-Surfaces $true 'before later HOLD'
        $draft=[pscustomobject]@{concept_key=$script:Lc.concept_key;status='draft';current_revision_id=$script:Lc.source_revision_id;current_revision_hash=$script:Lc.source_revision_hash;semantic_review_hold=[pscustomobject]@{schema='SYNTHETIC_HOLD'} }
        $script:State.research_drafts=@($draft)
        Assert-Surfaces $false 'later semantic HOLD' 'checks_ready'
        Assert-Test ($script:SemanticCalls -gt 0) 'Actual HOLD guard must call the explicitly doubled current-review dependency.'
    }
    Invoke-TestCase 'Persisted later HOLD is not bypassed by a stale supplied state' {
        New-TestFixture
        $script:PersistedState=Get-TestJson $script:State | ConvertFrom-Json -DateKind String
        $script:PersistedState.research_drafts=@([pscustomobject]@{concept_key=$script:Lc.concept_key;status='draft';semantic_review_hold=[pscustomobject]@{schema='SYNTHETIC_HOLD'}})
        Assert-Surfaces $false 'persisted HOLD absent from caller' 'checks_ready'
        Assert-Test ($script:SemanticCalls -eq 0) 'Actual guard rejects omitted HOLD before consulting the semantic outcome double.'
    }
    Invoke-TestCase 'Unreadable current state fails closed on both surfaces' {
        New-TestFixture;$script:StateReadThrows=$true
        Assert-Surfaces $false 'state read failure' 'checks_ready'
    }
    Invoke-TestCase 'Verified historical publication retains precedence over current package expiry' {
        New-TestFixture -Expired;Add-TestPublication
        Assert-Test (!(Test-LocalPackageCurrentAuthority $script:Package $script:Lc $null $script:State)) 'Expired package cannot currently be ready.'
        Assert-Test (Test-LocalPublicationReceiptAuthority $script:State $script:State.publication_receipts[0]) 'Real receipt authority accepts publication before profile expiry.'
        $script:StateReadCalls=0
        Assert-Test ((Get-ForgePipelineStage $script:State $script:Lc $script:Lc.concept_key) -ceq 'published') 'Verified publication has stage precedence.'
        $ins=Get-ForgePerformanceInsights $script:State $script:Now
        Assert-Test (@($ins.products).Count -eq 1) 'Real verified receipt remains a product.'
        Assert-Test (@($ins.attention | Where-Object {$_.kind -ceq 'unpublished'}).Count -eq 0) 'Published concept gets no package upload reminder.'
        Assert-Test ($script:StateReadCalls -eq 0) 'Publication paths do not fall through to current-package authority.'
    }
    Invoke-TestCase 'Unverified receipt never masks an invalid current package' {
        New-TestFixture;Add-TestPublication
        $script:State.publication_receipts[0].lineage_verified=$false
        $script:Package.valid=$false
        Assert-Surfaces $false 'unverified receipt' 'checks_ready'
    }
    Invoke-TestCase 'Noncanonical concept without packages preserves accepted and decision fallbacks' {
        New-TestFixture;$script:Lc.packages=@()
        Assert-Test ((Get-ForgePipelineStage $script:State $script:Lc $script:Lc.concept_key) -ceq 'checks_ready') 'No package still uses checks fallback.'
        $script:ChecksReady=$false
        Assert-Test ((Get-ForgePipelineStage $script:State $script:Lc $script:Lc.concept_key) -ceq 'artwork_accepted') 'Non-ready checks keep accepted artwork stage.'
        $script:Lc.active_acceptance=$null
        Assert-Test ((Get-ForgePipelineStage $script:State $script:Lc $script:Lc.concept_key) -ceq 'keep_no_artwork') 'Actual owner KEEP decision still works without a semantic HOLD.'
        Assert-Test ((Get-ForgePipelineStage $script:State $null $script:Lc.concept_key) -ceq 'undecided') 'Null concept remains safe.'
        $ins=Get-ForgePerformanceInsights $script:State $script:Now
        Assert-Test (@($ins.attention | Where-Object {$_.kind -ceq 'unpublished'}).Count -eq 0) 'No package cannot produce ready reminder.'
    }

    Invoke-TestCase 'Historical receipt import validates real archive without restoring current readiness' {
        New-ReceiptImportFixture;$state=Import-TestHistoricalReceipt;$receipt=$state.publication_receipts[0]
        Assert-Test ($receipt.historical_package_at_import-is[bool]-and$receipt.historical_package_at_import) 'Invalidated archive import explicitly recorded as historical.'
        Assert-Test ($receipt.publication_evidence_kind-ceq'owner_attested_external'-and$receipt.independent_publication_verification-is[bool]-and!$receipt.independent_publication_verification) 'Owner report is not represented as independent publication verification.'
        Assert-Test (Test-LocalPublicationReceiptAuthority $state $receipt) 'Actual receipt authority verifies exact archive lineage and declared event window, not external publication.'
        Assert-Test (!$state.concepts[0].packages[0].valid-and$null-eq$state.concepts[0].active_acceptance) 'Current package/acceptance remain withdrawn.'
        Assert-Test (!(Get-LocalDeliveryReadiness $state.concepts[0] $state).ready) 'Actual current delivery readiness remains false.'
    }
    Invoke-TestCase 'Historical receipt cancellation preserves state and source files' {
        New-ReceiptImportFixture;$before=Get-FileSha256Hex $script:ImportStatePath;$receiptSha=Get-FileSha256Hex $script:ReceiptPath;$zipSha=Get-FileSha256Hex $script:Package.path
        $script:ImportAnswers.Enqueue($false);Import-LocalPublicationReceiptFromPath $script:ReceiptPath
        Assert-ImportNoWrite $before 'cancel';Assert-Test ($script:ImportErrors.Count-eq0-and$script:ImportQuestions.Count-eq1) 'One clean cancellation.'
        Assert-Test ((Get-FileSha256Hex $script:ReceiptPath)-ceq$receiptSha-and(Get-FileSha256Hex $script:Package.path)-ceq$zipSha) 'Receipt and archive bytes unchanged.'
    }
    Invoke-TestCase 'Historical exact receipt source deduplicates before confirmation' {
        New-ReceiptImportFixture;$null=Import-TestHistoricalReceipt;$before=Get-FileSha256Hex $script:ImportStatePath;Reset-ImportObservations;Import-LocalPublicationReceiptFromPath $script:ReceiptPath
        Assert-ImportNoWrite $before 'same receipt';Assert-Test ($script:ImportQuestions.Count-eq0-and$script:ImportErrors.Count-eq0) 'Exact source duplicate requires no confirmation or new receipt.'
    }
    Invoke-TestCase 'Historical same product package binding deduplicates a different source' {
        New-ReceiptImportFixture;$null=Import-TestHistoricalReceipt;$before=Get-FileSha256Hex $script:ImportStatePath;$doc=New-TestReceiptDocument;$doc.note='Different source document, same exact binding';Save-TestReceiptDocument $doc;Reset-ImportObservations;Import-LocalPublicationReceiptFromPath $script:ReceiptPath
        Assert-ImportNoWrite $before 'same binding';Assert-Test ($script:ImportQuestions.Count-eq0-and$script:ImportErrors.Count-eq0) 'Real binding decision deduplicates distinct source bytes.'
    }
    Invoke-TestCase 'Historical conflicting product binding is refused using real archive authority' {
        New-ReceiptImportFixture;$null=Import-TestHistoricalReceipt;$saved=Get-ImportFixtureState;$first=$saved.concepts[0].packages[0]
        $script:Lc.publication.listing_title='Another exact historical listing';$script:Package=(Get-TestJson $first)|ConvertFrom-Json -DateKind String;$script:Package.listing_hash=Get-LocalPublicationHash $script:Lc.publication
        $script:ArchivedMetadata.listing=$script:Lc.publication;$script:ArchivedGate.lineage.listing_hash=$script:Package.listing_hash;$script:ArchivedMetadata.lineage=$script:ArchivedGate.lineage;Save-TestArchive
        Assert-Test ($null-ne(Get-LocalReadyPackageZipAuthority $script:Package.path $script:Package $script:Lc.concept_key)) 'Second package has independently real valid archive authority.'
        $saved.concepts[0].packages=@($first,$script:Package);Save-ImportFixtureState $saved;Save-TestReceiptDocument (New-TestReceiptDocument);$before=Get-FileSha256Hex $script:ImportStatePath;Reset-ImportObservations;Import-LocalPublicationReceiptFromPath $script:ReceiptPath
        Assert-ImportNoWrite $before 'conflict';Assert-Test ($script:ImportErrors.Count-eq1-and$script:ImportQuestions.Count-eq0) 'Conflict rejected before human confirmation.'
    }
    Invoke-TestCase 'Historical receipt bytes changed during confirmation are not imported' {
        New-ReceiptImportFixture;$before=Get-FileSha256Hex $script:ImportStatePath;$script:ImportOnConfirm={[IO.File]::AppendAllText($script:ReceiptPath,' ')};$script:ImportAnswers.Enqueue($true);Import-LocalPublicationReceiptFromPath $script:ReceiptPath
        Assert-ImportNoWrite $before 'receipt byte race';Assert-Test ($script:ImportErrors.Count-eq1) 'Actual rehash detects even valid-JSON whitespace replacement.'
    }
    Invoke-TestCase 'Historical archive bytes changed during confirmation are not imported' {
        New-ReceiptImportFixture;$before=Get-FileSha256Hex $script:ImportStatePath;$script:ImportOnConfirm={$stream=[IO.File]::Open($script:Package.path,[IO.FileMode]::Append,[IO.FileAccess]::Write);try{$stream.WriteByte(42)}finally{$stream.Dispose()}};$script:ImportAnswers.Enqueue($true);Import-LocalPublicationReceiptFromPath $script:ReceiptPath
        Assert-ImportNoWrite $before 'archive byte race';Assert-Test ($script:ImportErrors.Count-eq1) 'Actual archive rehash detects changed bytes after confirmation.'
    }
    Invoke-TestCase 'Historical receipt identity channel market and event date guards remain exact' {
        New-ReceiptImportFixture;$base=New-TestReceiptDocument;$before=Get-FileSha256Hex $script:ImportStatePath
        foreach($variant in @('schema','concept','package','print','fingerprint','listing','gate','channel','market','product','invalid_date','future','before_package','after_profile')){
            $doc=(Get-TestJson $base)|ConvertFrom-Json -DateKind String
            switch($variant){
                'schema'{$doc.schema='forge.local_publication_receipt.v2'} 'concept'{$doc.concept_key='unknown'} 'package'{$doc.package_sha256=('0'*64)}
                'print'{$doc.print_production_sha256=('0'*64)} 'fingerprint'{$doc.lineage_fingerprint=('0'*64)} 'listing'{$doc.listing_hash=('0'*64)} 'gate'{$doc.preupload_gate_sha256=('0'*64)}
                'channel'{$doc.channel='other'} 'market'{$doc.marketplace='DE'} 'product'{$doc.product_id=''} 'invalid_date'{$doc.published_at='not-a-date'}
                'future'{$doc.published_at=$script:Now.AddDays(1).ToString('o')} 'before_package'{$doc.published_at=$script:Now.AddDays(-11).ToString('o')} 'after_profile'{$doc.published_at=$script:Now.AddHours(-1).ToString('o')}
            }
            Save-TestReceiptDocument $doc;Reset-ImportObservations;Import-LocalPublicationReceiptFromPath $script:ReceiptPath
            Assert-ImportNoWrite $before $variant;Assert-Test ($script:ImportErrors.Count-eq1-and$script:ImportQuestions.Count-eq0) ($variant+': reject before confirmation')
        }
    }
    Invoke-TestCase 'Historical malformed validity and non READY status cannot become evidence' {
        New-ReceiptImportFixture;$original=Get-TestJson (Get-ImportFixtureState)
        foreach($variant in @('missing','null','string_false','string_true','number','draft_status')){
            $state=$original|ConvertFrom-Json -DateKind String
            switch($variant){'missing'{$state.concepts[0].packages[0].PSObject.Properties.Remove('valid')}'null'{$state.concepts[0].packages[0].valid=$null}'string_false'{$state.concepts[0].packages[0].valid='false'}'string_true'{$state.concepts[0].packages[0].valid='true'}'number'{$state.concepts[0].packages[0].valid=0}'draft_status'{$state.concepts[0].packages[0].status='DRAFT_BLOCKED'}}
            Save-ImportFixtureState $state;$before=Get-FileSha256Hex $script:ImportStatePath;Reset-ImportObservations;Import-LocalPublicationReceiptFromPath $script:ReceiptPath
            Assert-ImportNoWrite $before $variant;Assert-Test ($script:ImportErrors.Count-eq1-and$script:ImportQuestions.Count-eq0) ($variant+': no implicit historical truthiness')
        }
    }
    Invoke-TestCase 'Historical missing or tampered physical archives are still refused' {
        foreach($variant in @('missing','tampered')){
            New-ReceiptImportFixture
            if($variant-ceq'missing'){$state=Get-ImportFixtureState;$state.concepts[0].packages[0].path=Join-Path $script:CaseRoot 'not-present.zip';Save-ImportFixtureState $state}
            else{$stream=[IO.File]::Open($script:Package.path,[IO.FileMode]::Append,[IO.FileAccess]::Write);try{$stream.WriteByte(42)}finally{$stream.Dispose()}}
            $before=Get-FileSha256Hex $script:ImportStatePath;Import-LocalPublicationReceiptFromPath $script:ReceiptPath;Assert-ImportNoWrite $before $variant;Assert-Test ($script:ImportErrors.Count-eq1-and$script:ImportQuestions.Count-eq0) ($variant+': actual physical check retained')
        }
    }
    Invoke-TestCase 'Historical self consistent ZIP with invalid gate is refused by real authority' {
        New-ReceiptImportFixture;$script:ArchivedGate.all_checks_ready=$false;Save-TestArchive;$state=Get-ImportFixtureState;$state.concepts[0].packages=@($script:Package);Save-ImportFixtureState $state;Save-TestReceiptDocument (New-TestReceiptDocument)
        Assert-Test ($null-eq(Get-LocalReadyPackageZipAuthority $script:Package.path $script:Package $script:Lc.concept_key)) 'Negative control fails actual gate authority despite matching ZIP SHA.'
        $before=Get-FileSha256Hex $script:ImportStatePath;Import-LocalPublicationReceiptFromPath $script:ReceiptPath;Assert-ImportNoWrite $before 'invalid gate';Assert-Test ($script:ImportErrors.Count-eq1-and$script:ImportQuestions.Count-eq0) 'No confirmation for invalid physical archive.'
    }
    Invoke-TestCase 'Historical stale writer is refused by disclosed synthetic CAS seam' {
        New-ReceiptImportFixture;$script:ImportOnConfirm={Bump-ImportFixtureState};$script:ImportAnswers.Enqueue($true);Import-LocalPublicationReceiptFromPath $script:ReceiptPath;$state=Get-ImportFixtureState
        Assert-Test ($script:ImportWriteAttempts-eq1-and$script:ImportWrites-eq0-and$script:ImportErrors.Count-eq1) 'One stale write attempt, no retry; actual durable store concurrency is not asserted.'
        Assert-Test ($state.concepts[0].owner_decision-ceq'EDIT'-and@($state.publication_receipts).Count-eq0) 'Newer state preserved without receipt append.'
    }
    Invoke-TestCase 'Historical commit then throw stays uncertain and retry deduplicates' {
        New-ReceiptImportFixture;$script:ImportCommitThenThrow=$true;$script:ImportAnswers.Enqueue($true);Import-LocalPublicationReceiptFromPath $script:ReceiptPath;$state=Get-ImportFixtureState
        Assert-Test ($script:ImportWriteAttempts-eq1-and$script:ImportWrites-eq1-and$script:ImportErrors.Count-eq1-and@($state.publication_receipts).Count-eq1) 'Explicit simulated commit followed by failure, not a claimed rollback.'
        Assert-Test ($StatusText.Text.Contains('needs attention')-and$StatusText.Text.Contains('verify saved history')) 'Uncertain save wording retained.'
        $before=Get-FileSha256Hex $script:ImportStatePath;Reset-ImportObservations;Import-LocalPublicationReceiptFromPath $script:ReceiptPath;Assert-ImportNoWrite $before 'retry after uncertain commit';Assert-Test ($script:ImportQuestions.Count-eq0) 'Retry does not ask again or append twice.'
    }
    Invoke-TestCase 'Current valid package import retains prior nonhistorical flow and truthful evidence kind' {
        New-ReceiptImportFixture $false;Import-LocalPublicationReceiptFromPath $script:ReceiptPath;$state=Get-ImportFixtureState;$receipt=$state.publication_receipts[0]
        Assert-Test ($script:ImportErrors.Count-eq0-and$script:ImportWrites-eq1-and$script:ImportQuestions.Count-eq0) 'Existing current-valid flow has no added historical confirmation.'
        Assert-Test ($receipt.historical_package_at_import-is[bool]-and!$receipt.historical_package_at_import-and$receipt.publication_evidence_kind-ceq'owner_attested_external'-and!$receipt.independent_publication_verification) 'Still explicitly owner-attested, not externally verified.'
        $before=Get-FileSha256Hex $script:ImportStatePath;Reset-ImportObservations;Import-LocalPublicationReceiptFromPath $script:ReceiptPath;Assert-ImportNoWrite $before 'current-valid exact source duplicate';Assert-Test ($script:ImportQuestions.Count-eq0-and$script:ImportErrors.Count-eq0) 'Current-valid duplicate remains idempotent.'
        $doc=New-TestReceiptDocument;$doc.note='Current valid same binding, distinct bytes';Save-TestReceiptDocument $doc;Reset-ImportObservations;Import-LocalPublicationReceiptFromPath $script:ReceiptPath;Assert-ImportNoWrite $before 'current-valid exact binding duplicate';Assert-Test ($script:ImportQuestions.Count-eq0-and$script:ImportErrors.Count-eq0) 'Current-valid binding duplicate remains idempotent.'
    }
    Invoke-TestCase 'Historical import never infers publication from invalidation timestamp' {
        foreach($invalidation in @('absent','unparseable','before_reported_event')){
            New-ReceiptImportFixture;$state=Get-ImportFixtureState
            switch($invalidation){'absent'{$state.concepts[0].packages[0].PSObject.Properties.Remove('invalidated_at')}'unparseable'{$state.concepts[0].packages[0].invalidated_at='not-an-event-date'}'before_reported_event'{$state.concepts[0].packages[0].invalidated_at=$script:Now.AddDays(-20).ToString('o')}}
            Save-ImportFixtureState $state;$state=Import-TestHistoricalReceipt
            Assert-Test ($state.publication_receipts[0].published_at-ceq$script:Now.AddDays(-9).ToUniversalTime().ToString('o')-and$script:ImportQuestions.Count-eq1) ($invalidation+': exact owner-reported date requires explicit confirmation')
        }
    }
    Invoke-TestCase 'Historical import preserves current concept approval checks history artwork and archives' {
        New-ReceiptImportFixture
        # A past package must not revoke or replace a newer review/acceptance for this concept.
        $newer=Get-ImportFixtureState;$newer.concepts[0].source_revision_id='newer-current-revision';$newer.concepts[0].source_revision_hash=('2'*64)
        $newer.concepts[0].active_acceptance=[pscustomobject]@{acceptance_id='newer-active-acceptance';concept_revision_id='newer-current-revision';revision_hash=('2'*64);lineage_fingerprint=('3'*64);asset_sha256=$script:Package.artwork_sha256;local_file_path=(Join-Path $script:CaseRoot 'artwork.png')}
        $newer.concepts[0].brief_approval.approval_id='newer-brief-approval';$newer.concepts[0].checks.visual.state='pass';$newer.concepts[0].checks.visual.note='Newer current review must remain byte-equivalent';$newer.concepts[0].artwork[0].accepted=$true;Save-ImportFixtureState $newer
        $before=Get-ImportFixtureState;$concepts=Get-TestJson $before.concepts;$drafts=Get-TestJson $before.research_drafts;$artPath=Join-Path $script:CaseRoot 'artwork.png';$artSha=Get-FileSha256Hex $artPath;$zipSha=Get-FileSha256Hex $script:Package.path;$receiptSha=Get-FileSha256Hex $script:ReceiptPath
        $state=Import-TestHistoricalReceipt
        Assert-Test ((Get-TestJson $state.concepts)-ceq$concepts-and(Get-TestJson $state.research_drafts)-ceq$drafts) 'All concept readiness/approval/check/history/package fields unchanged; only receipt/state envelope appended.'
        Assert-Test ((Get-FileSha256Hex $artPath)-ceq$artSha-and(Get-FileSha256Hex $script:Package.path)-ceq$zipSha-and(Get-FileSha256Hex $script:ReceiptPath)-ceq$receiptSha) 'Actual PNG, ZIP and supplied receipt bytes intact.'
        Assert-Test ($state.concepts[0].active_acceptance.acceptance_id-ceq'newer-active-acceptance'-and$state.concepts[0].source_revision_id-cne$state.concepts[0].packages[0].concept_revision_id) 'Old archive import is independent of newer current revision and acceptance.'
        $reloaded=Read-LocalCoreState;Assert-Test (@($reloaded.publication_receipts).Count-eq1-and!$reloaded.concepts[0].packages[0].valid) 'Detached saved JSON reload retains historical evidence, not ready flag; not app restart proof.'
    }
    Invoke-TestCase 'Historical confirmation distinguishes owner report from external verification' {
        New-ReceiptImportFixture;$script:ImportAnswers.Enqueue($false);Import-LocalPublicationReceiptFromPath $script:ReceiptPath;$q=$script:ImportQuestions[0];$doc=New-TestReceiptDocument
        foreach($value in @($doc.concept_key,$doc.package_sha256,$doc.channel,$doc.marketplace,$doc.product_id,$script:Now.AddDays(-9).ToUniversalTime().ToString('o'))){Assert-Test ($q.Contains($value)) 'Confirmation carries exact archive/product/event identity.'}
        Assert-Test ($q.Contains('owner-reported')-and$q.Contains('actual publication')-and$q.Contains('not external publication')-and$q.Contains('does not restore')) 'Actual confirmation does not claim independent event verification or reapproval.'
    }
    Invoke-TestCase 'Historical receipt duplicate JSON keys are rejected before state access' {
        New-ReceiptImportFixture;$raw=Get-TestJson (New-TestReceiptDocument);$raw=$raw.Insert(1,'"schema":"forge.local_publication_receipt.v3",');[IO.File]::WriteAllText($script:ReceiptPath,$raw,(New-Object Text.UTF8Encoding($false)));$before=Get-FileSha256Hex $script:ImportStatePath;$script:StateReadCalls=0
        Import-LocalPublicationReceiptFromPath $script:ReceiptPath;Assert-ImportNoWrite $before 'duplicate source keys';Assert-Test ($script:ImportErrors.Count-eq1-and$script:StateReadCalls-eq0-and$script:ImportQuestions.Count-eq0) 'Actual strict payload parser rejects duplicate source fields before state access.'
    }
    Invoke-TestCase 'Historical saved receipt survives UI refresh failure without second mutation' {
        New-ReceiptImportFixture;$script:ImportUiThrows=$true;$state=Import-TestHistoricalReceipt
        Assert-Test (@($state.publication_receipts).Count-eq1-and$script:ImportWriteAttempts-eq1) 'One receipt saved despite UI failure.'
        Assert-Test ($StatusText.Text.Contains('owner-reported')-and@($script:ImportLogs).Count-eq1) 'Saved owner-report result remains truthful with warning.'
    }
    Invoke-TestCase 'Historical receipt path makes no generation publication or network dispatch' {
        Assert-Test ($script:ForbiddenAttempts.Count-eq0) ('Forbidden boundary calls: '+($script:ForbiddenAttempts-join','))
    }
} catch {
    $script:Cases.Add([pscustomobject]@{name='Setup or unexpected harness failure';status='FAIL';detail=$_.Exception.Message})
} finally {
    foreach($source in $script:Sources) {
        Invoke-TestCase ('Final source integrity: '+$source.relative) {
            Assert-TestNonredirectedPath $source.path;Assert-TestNonredirectedPath $source.copy_path
            $source.after_sha256=Get-TestHash ([IO.File]::ReadAllBytes($source.path))
            $source.copy_after_sha256=Get-TestHash ([IO.File]::ReadAllBytes($source.copy_path))
            Assert-Test ($source.after_sha256 -ceq $source.before_sha256) 'Actual source changed during invocation.'
            Assert-Test ($source.copy_after_sha256 -ceq $source.before_sha256) 'Owned source copy changed during invocation.'
        }
    }
    foreach($source in $script:ControlSources) {
        Invoke-TestCase ('Final control integrity: '+$source.name) {
            Assert-TestNonredirectedPath $source.path
            $source.after_sha256=Get-TestHash ([IO.File]::ReadAllBytes($source.path))
            Assert-Test ($source.after_sha256 -ceq $source.before_sha256) 'Test or manifest changed during invocation.'
        }
    }
    Invoke-TestCase 'Exact ordered receipt case and function identities' {
        Assert-Test ($null -ne $manifest) 'Manifest must have been validated.'
        $expectedPrior=@($manifest.expected_case_names | Where-Object {$_ -cne 'Exact ordered receipt case and function identities'})
        Assert-Test ((@($script:Cases | ForEach-Object {$_.name}) -join '|') -ceq ($expectedPrior -join '|')) 'Exact ordered complete case identities required, not only a count.'
        Assert-Test ((@($script:Loaded | ForEach-Object {$_.name}) -join '|') -ceq (@($manifest.expected_loaded_functions) -join '|')) 'Exact ordered complete function identities required, not only a count.'
    }
    $failed=@($script:Cases | Where-Object {$_.status -ceq 'FAIL'}).Count
    $status=if($failed -eq 0 -and $script:Loaded.Count -eq 43 -and $script:Assertions -gt 0){'PASS'}else{'FAIL'}
    $receipt=[ordered]@{
        schema='forge.pipeline_package_authority.native_receipt.v1';run_id=$RunId;status=$status;started_at=$started;completed_at=[DateTime]::UtcNow.ToString('o')
        runtime=[string]$PSVersionTable.PSVersion;ps_edition=[string]$PSVersionTable.PSEdition;date_kind_string_available=[bool]((Get-Command ConvertFrom-Json).Parameters.ContainsKey('DateKind'));minimum_powershell_core='7.5';platform=[Environment]::OSVersion.Platform.ToString();module_root=$ModuleRoot;owned_fixture_root=$script:FixtureRoot
        assertions=$script:Assertions;failed_cases=$failed;cases=@($script:Cases.ToArray());observed_surfaces=@($script:Observed.ToArray())
        source_manifest_sha256=$ExpectedSourceManifestSha256;control_sources=@($script:ControlSources.ToArray());sources=@($script:Sources.ToArray());loaded_functions=@($script:Loaded.ToArray())
        dependency_doubles=@('Read-LocalCoreState: detached owned synthetic state or throws; receipt cases use an owned synthetic JSON file','Write-LocalCoreState: synthetic detached JSON CAS, rejection and commit-then-throw injection; NOT real durable-store concurrency','Confirm/Show-Error/status/business refresh: explicit queued answers, mutation hooks and bounded UI counters; NOT WPF','Get-LocalPackageBriefApprovalSnapshot: synthetic approval prerequisite','Get-LocalCheckGateSnapshot: synthetic current checks prerequisite','Get-LocalPrintProductionSnapshot: synthetic current-capture prerequisite','Test-ForgeSemanticReviewCurrent: synthetic review outcome, not full canonical review verification','Reconcile-LocalSalesLinks: empty-sales no-op guard','Get-LocalAmazonPrintProfilePath: owned fixture location only')
        actual_boundaries=@('Both Pipeline entrypoints','Get-LocalDeliveryReadiness','Test-LocalPackageCurrentAuthority','Assert-ForgeNoSemanticHold','Physical ZIP hash and JSON entry reads','Get-LocalReadyPackageZipAuthority','Strict JSON parser','Real archived PNG decode and technical validation','Current listing hash and profile equality','Archived profile expiry','Publication receipt authority and precedence','Import-LocalPublicationReceiptFromPath','Read-LocalCheckEvidencePayload','Get-LocalPublicationReceiptBindingDecision')
        forbidden_boundary_attempts=@($script:ForbiddenAttempts.ToArray())
        external_supervisor_contract='Separately reviewed Windows owner-private ACL and bounded process-tree supervisor required; switch acknowledges this but does not provision or prove ACLs.'
        limitations=@('Focused extracted-function synthetic regression, not full app or real approval evidence.','Imported publication event remains owner-attested external evidence, NOT independent marketplace verification.','Synthetic state CAS and commit-then-throw do not establish real durable-store atomicity/concurrency; detached JSON reload is not app restart.','No full semantic-review receipt/source verifier test.','No real source, approval, publication, export, model, network, or user data is created or modified.','Fixtures are artificial and must not be imported into Forge.','Timeout, crash, nonzero exit, absent or mismatched fresh receipt, source drift, or non-PASS status are failures.','A killed host may produce no native receipt. External supervisor must establish completion.')
    }
    $stream=[IO.File]::Open($receiptPath,[IO.FileMode]::CreateNew,[IO.FileAccess]::Write,[IO.FileShare]::None)
    try {$bytes=[Text.Encoding]::UTF8.GetBytes(($receipt | ConvertTo-Json -Depth 60));$stream.Write($bytes,0,$bytes.Length)}finally{$stream.Dispose()}
    Write-Host ('Native receipt: '+$receiptPath)
}
if($status -cne 'PASS'){throw ('Focused package authority regression failed: '+$receiptPath)}
Write-Host ('PASS: '+$script:Cases.Count+' focused cases, '+$script:Assertions+' assertions. Not a full-stack claim.')
