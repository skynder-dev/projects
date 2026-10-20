function Read-ForgeGenerationJournalSnapshot([string]$Path,[long]$MaxBytes=1048576) {
    return (Read-ForgeJsonFileSnapshot $Path $MaxBytes)
}
# Merch Forge · local generation job/worker bridge
# Creates exact-revision jobs, launches a separate provider worker, imports verified results back into local core.
. (Join-Path $PSScriptRoot 'Forge.GenerationAuthority.ps1')
. (Join-Path $PSScriptRoot 'Forge.LocalFlux.ps1')
. (Join-Path $PSScriptRoot 'Forge.GenerationMaintenance.ps1')
$script:GenerationImportIssues=@{}
function Initialize-GenerationWorkerBridge {
    foreach($p in @($script:GenerationRoot,$script:GenerationOutboxRoot,$script:GenerationResultRoot,$script:GenerationReceiptRoot,$script:GenerationAttemptRoot,$script:ProviderSecretRoot)){Ensure-Dir $p}
    try{Sync-LocalGenerationResults}catch{Write-AppLog 'WARN' ('Generation result sync failed during initialization: '+$_.Exception.Message)}
    try{$null=Invoke-GenerationSpoolMaintenance}catch{Write-AppLog 'WARN' ('Generation spool maintenance skipped: '+$_.Exception.Message)}
}
function Get-LocalGenerationPromptCompilerVersion { return 'forge.prompt.apparel.v3' }
function Get-LocalGenerationPromptTemplateMaterial { return (Get-ForgeGenerationBriefPromptTemplate) }
function Get-LocalGenerationPromptTemplateSha256 { return Get-GenerationProviderTextSha256 (Get-LocalGenerationPromptTemplateMaterial) }
function Get-LocalGenerationPrompt($Concept,$Identity) { return (Get-ForgeGenerationBriefPrompt (New-ForgeGenerationBriefSnapshot $Concept)) }
function Get-LocalGenerationJobPath([string]$JobId){return Join-Path $script:GenerationOutboxRoot ($JobId+'.json')}
function Get-LocalGenerationResultPath([string]$JobId){return Join-Path $script:GenerationResultRoot ($JobId+'.result.json')}
function Get-LocalGenerationReceiptPath([string]$JobId){return Join-Path $script:GenerationReceiptRoot ($JobId+'.imported.json')}
function Get-LocalGenerationAttemptPath([string]$JobId){return Join-Path $script:GenerationAttemptRoot ($JobId+'.attempt.json')}
function Get-LocalGenerationRegistrySha256 { if(-not(Test-Path -LiteralPath $script:GenerationProvidersPath -PathType Leaf)){throw 'Generation provider registry is missing.'};return Get-FileSha256Hex $script:GenerationProvidersPath }
function Test-LocalGenerationJobJournalEnvelope($Job,[string]$LeafName='') {
    return (Test-ForgeGenerationJobEnvelope $Job $LeafName)
}
function Assert-LocalGenerationOutboxJournalsSafe {
    if(-not(Test-Path -LiteralPath $script:GenerationOutboxRoot)){return $true}
    try{$files=@(Get-ChildItem -LiteralPath $script:GenerationOutboxRoot -Filter '*.json' -File -ErrorAction Stop)}catch{throw ('Generation outbox cannot be read safely. New paid generation is blocked: '+$_.Exception.Message)}
    foreach($f in $files){
        try{$j=(Read-ForgeGenerationJournalSnapshot $f.FullName 16777216).data}catch{throw ('Generation job journal is unreadable. New paid generation is blocked: '+$f.Name)}
        if(-not(Test-LocalGenerationJobJournalEnvelope $j ([IO.Path]::GetFileName($f.FullName)))){throw ('Generation job journal is structurally incomplete or unsafe. New paid generation is blocked: '+$f.Name)}
    }
    return $true
}
function Test-LocalGenerationReceiptSatisfied([string]$ReceiptPath,[string]$ConceptKey,[string]$RevisionId,[string]$RevisionHash='') {
    try {
    if(-not(Test-Path -LiteralPath $ReceiptPath -PathType Leaf)){return $false}
    try{$receiptCapture=Read-ForgeGenerationJournalSnapshot $ReceiptPath;$receipt=$receiptCapture.data}catch{return $false}
    if([string](Get-PropertyValue $receipt 'schema') -ne 'forge.generation_import_receipt.v4'){return $false};$jobId=[string](Get-PropertyValue $receipt 'job_id');if($jobId -notmatch '^gen-[0-9a-f]{32}$'){return $false}
    $jobPath=Get-LocalGenerationJobPath $jobId;$resultPath=Get-LocalGenerationResultPath $jobId;$attemptPath=Get-LocalGenerationAttemptPath $jobId
    if(-not(Test-Path -LiteralPath $jobPath -PathType Leaf) -or -not(Test-Path -LiteralPath $resultPath -PathType Leaf) -or -not(Test-Path -LiteralPath $attemptPath -PathType Leaf)){return $false}
    try{$jobCapture=Read-ForgeGenerationJournalSnapshot $jobPath 16777216;$resultCapture=Read-ForgeGenerationJournalSnapshot $resultPath 16777216;$attemptCapture=Read-ForgeGenerationJournalSnapshot $attemptPath}catch{return $false};$jobSha=$jobCapture.sha256;$resultSha=$resultCapture.sha256;$attemptSha=$attemptCapture.sha256
    if([string](Get-PropertyValue $receipt 'job_sha256') -ne $jobSha -or [string](Get-PropertyValue $receipt 'result_sha256') -ne $resultSha -or [string](Get-PropertyValue $receipt 'attempt_sha256') -ne $attemptSha){return $false}
    try{$job=$jobCapture.data;$result=$resultCapture.data;$attempt=$attemptCapture.data}catch{return $false}
    $provider=[string](Get-PropertyValue $receipt 'provider_key')
    if([string](Get-PropertyValue $job 'schema') -ne 'forge.generation_job.v4' -or [string](Get-PropertyValue $result 'schema') -ne 'forge.generation_result.v4' -or [string](Get-PropertyValue $attempt 'schema') -ne 'forge.generation_attempt.v1'){return $false}
    if([string](Get-PropertyValue $job 'job_id') -ne $jobId -or [string](Get-PropertyValue $result 'job_id') -ne $jobId -or [string](Get-PropertyValue $attempt 'job_id') -ne $jobId){return $false}
    if([string](Get-PropertyValue $job 'concept_key') -ne $ConceptKey -or [string](Get-PropertyValue $job 'source_revision_id') -ne $RevisionId -or [string](Get-PropertyValue $result 'concept_key') -ne $ConceptKey -or [string](Get-PropertyValue $result 'source_revision_id') -ne $RevisionId){return $false};if(-not[string]::IsNullOrWhiteSpace($RevisionHash) -and ([string](Get-PropertyValue $job 'source_revision_hash') -ne $RevisionHash -or [string](Get-PropertyValue $result 'source_revision_hash') -ne $RevisionHash)){return $false}
    if([string](Get-PropertyValue $job 'provider_key') -ne $provider -or [string](Get-PropertyValue $result 'provider_key') -ne $provider -or [string](Get-PropertyValue $attempt 'provider_key') -ne $provider){return $false}
    $requestCount=Get-PropertyValue $attempt 'provider_request_count';if($requestCount-isnot[int]-and$requestCount-isnot[long]){return $false}
    if([string](Get-PropertyValue $result 'status') -ne 'completed' -or [string](Get-PropertyValue $attempt 'phase') -ne 'completed' -or [int](Get-PropertyValue $attempt 'provider_request_count') -ne 1 -or [string](Get-PropertyValue $attempt 'job_sha256') -ne $jobSha -or [string](Get-PropertyValue $attempt 'result_sha256') -ne $resultSha -or [string](Get-PropertyValue $result 'job_sha256') -ne $jobSha){return $false}
    foreach($name in @('provider_contract_version','provider_registry_sha256','provider_config_fingerprint','prompt_compiler_version','prompt_template_sha256','prompt_sha256')){$want=[string](Get-PropertyValue $receipt $name);if([string]::IsNullOrWhiteSpace($want) -or $want -ne [string](Get-PropertyValue $result $name) -or $want -ne [string](Get-PropertyValue $job $name) -or $want -ne [string](Get-PropertyValue $attempt $name)){return $false}}
    foreach($name in @('provider_profile','provider_request_id')){$want=[string](Get-PropertyValue $receipt $name);if($want -ne [string](Get-PropertyValue $result $name) -or $want -ne [string](Get-PropertyValue $attempt $name)){return $false}};if([string](Get-PropertyValue $receipt 'provider_model') -ne [string](Get-PropertyValue $result 'model') -or [string](Get-PropertyValue $receipt 'provider_model') -ne [string](Get-PropertyValue $attempt 'model')){return $false}
    $want=@((Get-PropertyValue $receipt 'asset_sha256'));$resultAssets=@((Get-PropertyValue $result 'assets'));if($want.Count -lt 1 -or $want.Count -ne $resultAssets.Count){return $false};$resultSet=@{};foreach($ra in $resultAssets){$rs=([string](Get-PropertyValue $ra 'sha256')).ToLowerInvariant();if($rs -notmatch '^[0-9a-f]{64}$' -or $resultSet.ContainsKey($rs)){return $false};$resultSet[$rs]=$true}
    $lc=Get-LocalCoreConcept $ConceptKey;if($null -eq $lc){return $false};$jobRevisionHash=([string](Get-PropertyValue $job 'source_revision_hash')).Trim().ToLowerInvariant();if($jobRevisionHash -notmatch '^[0-9a-f]{64}$'){return $false}
    $seen=@{};foreach($sha in $want){
        $k=([string]$sha).ToLowerInvariant();if($k -notmatch '^[0-9a-f]{64}$' -or $seen.ContainsKey($k) -or -not $resultSet.ContainsKey($k)){return $false}
        $art=$null;foreach($v in @((Get-PropertyValue $lc 'artwork'))){
            if([string](Get-PropertyValue $v 'concept_revision_id') -ne $RevisionId -or ([string](Get-PropertyValue $v 'asset_sha256')).ToLowerInvariant() -ne $k){continue}
            if(([string](Get-PropertyValue $v 'source_revision_hash')).Trim().ToLowerInvariant() -ne $jobRevisionHash -or [string](Get-PropertyValue $v 'generation_request_id') -ne $jobId -or [string](Get-PropertyValue $v 'provider_key') -ne $provider -or [string](Get-PropertyValue $v 'generation_method') -ne 'local_provider_worker'){continue}
            $provOk=$true;foreach($name in @('provider_profile','provider_model','provider_contract_version','provider_registry_sha256','provider_config_fingerprint','prompt_compiler_version','prompt_template_sha256','provider_request_id','prompt_sha256')){if([string](Get-PropertyValue $v $name) -ne [string](Get-PropertyValue $receipt $name)){$provOk=$false;break}};if(-not$provOk){continue}
            if([string](Get-PropertyValue $v 'generation_result_sha256') -ne $resultSha -or [string](Get-PropertyValue $v 'generation_attempt_sha256') -ne $attemptSha){continue}
            $localPath=[string](Get-PropertyValue $v 'local_file_path');if([string]::IsNullOrWhiteSpace($localPath) -or -not(Test-ForgeAuthorityPathWithinRoot $localPath $script:LocalCoreArtworkRoot) -or -not(Test-Path -LiteralPath $localPath -PathType Leaf)){continue};try{if((Get-FileSha256Hex $localPath) -ne $k){continue}}catch{continue}
            $art=$v;break
        }
        if($null -eq $art){return $false};$seen[$k]=$true
    };return ($seen.Count -eq $resultSet.Count)

    }catch{return $false}
}
function Test-LocalAmbiguousGenerationChain([object[]]$Jobs,[string]$PriorJobId) {
    $amb=@($Jobs|Where-Object{$_.status -eq 'ambiguous'});if($amb.Count -eq 0){return [pscustomobject]@{ok=$true;count=0}}
    if([string]::IsNullOrWhiteSpace($PriorJobId)){return [pscustomobject]@{ok=$false;count=$amb.Count;reason='explicit_prior_required'}}
    $allowed=@{};$cursor=$PriorJobId;$guard=0
    while(-not[string]::IsNullOrWhiteSpace($cursor) -and $guard -lt 64){$guard++;if($allowed.ContainsKey($cursor)){break};$allowed[$cursor]=$true;$jp=Get-LocalGenerationJobPath $cursor;if(-not(Test-Path -LiteralPath $jp -PathType Leaf)){break};try{$jj=Get-Content -LiteralPath $jp -Raw -Encoding UTF8|ConvertFrom-Json;$cursor=([string](Get-PropertyValue $jj 'prior_job_id')).Trim()}catch{break}}
    foreach($a in $amb){if(-not $allowed.ContainsKey([string]$a.id)){return [pscustomobject]@{ok=$false;count=$amb.Count;reason='unrelated_ambiguous_job'}}}
    return [pscustomobject]@{ok=$true;count=$amb.Count}
}
function Get-LocalGenerationPreDispatchExpiryMinutes { $reg=Get-Content -LiteralPath $script:GenerationProvidersPath -Raw -Encoding UTF8|ConvertFrom-Json;$policy=Get-PropertyValue $reg 'worker_policy';$n=[int](Get-PropertyValue $policy 'pre_dispatch_job_expiry_minutes');if($n -lt 1 -or $n -gt 1440){throw 'Generation pre-dispatch expiry policy is invalid.'};return $n }
function Enter-LocalGenerationActionLock { Ensure-Dir $script:GenerationRoot;$path=Join-Path $script:GenerationRoot 'owner-action.lock';try{return [IO.File]::Open($path,[IO.FileMode]::OpenOrCreate,[IO.FileAccess]::ReadWrite,[IO.FileShare]::None)}catch{throw 'Another Merch Forge window is creating a generation action right now. No job was created; wait a moment and try again.'} }
function Get-LocalGenerationDispatchBinding($Config=$null) {
    if($null-eq$Config){$Config=Get-GenerationProviderRuntimeConfig}
    return [pscustomobject]@{schema='forge.generation_dispatch_binding.v1';provider_enabled=(Get-PropertyValue $Config 'enabled');provider_config_fingerprint=(Get-GenerationProviderConfigFingerprint $Config);provider_registry_sha256=(Get-LocalGenerationRegistrySha256);prompt_compiler_version=(Get-LocalGenerationPromptCompilerVersion);prompt_template_sha256=(Get-LocalGenerationPromptTemplateSha256)}
}
function Assert-LocalGenerationDispatchBinding($Expected,$Config) {
    $actual=Get-LocalGenerationDispatchBinding $Config
    foreach($name in @('schema','provider_config_fingerprint','provider_registry_sha256','prompt_compiler_version','prompt_template_sha256')){
        $value=Get-PropertyValue $Expected $name
        if($value-isnot[string]-or[string]::IsNullOrWhiteSpace($value)-or$value-cne[string](Get-PropertyValue $actual $name)){throw (Get-UiText 'generation.settings.changed' 'Provider or render settings changed, or their confirmation is missing. Review the current settings and confirm generation again. No job was created.')}
    }
    if((Get-PropertyValue $Expected 'provider_enabled')-isnot[bool]-or!(Get-PropertyValue $Expected 'provider_enabled')-or(Get-PropertyValue $actual 'provider_enabled')-isnot[bool]-or!(Get-PropertyValue $actual 'provider_enabled')){throw (Get-UiText 'generation.settings.changed' 'Provider settings changed or are disabled. Confirm the current settings again. No job was created.')}
    return $actual
}
function New-LocalGenerationJob([string]$Kind='generate',[string]$PriorJobId='',$ExpectedDispatchBinding=$null) {
    $actionLock=$null;$stateLock=$null
    try {
        $actionLock=Enter-LocalGenerationActionLock
        if($null -eq $script:Current){throw 'Choose an idea first.'};$c=$script:Current.concept;$approved=Assert-LocalGenerationBriefApproved $c;$identity=$approved.identity;if($Kind -notin @('generate','regenerate')){throw 'Invalid local generation request kind.'};$null=Assert-LocalGenerationOutboxJournalsSafe
        if(-not(Test-LocalProductionProviderReady)){throw 'No production image provider is configured locally.'};$null=Assert-GenerationProviderConfigSafe
        try{$null=Sync-LocalGenerationResults}catch{Write-AppLog 'WARN' ('Pre-generation result recovery failed: '+$_.Exception.Message)}
        $jobs=@(Get-LocalGenerationJobsForCurrent);$active=@($jobs|Where-Object{$_.status -in @('queued','running','completed_pending_import')});if($active.Count -gt 0){$st=[string]$active[0].status;$msg=if($st -eq 'completed_pending_import'){'A completed provider result is waiting for verified import/recovery before another paid request can start: '}else{'A local generation job is already in progress for this exact revision: '};throw ($msg+[string]$active[0].id)}
        $chain=Test-LocalAmbiguousGenerationChain $jobs $PriorJobId;if(-not[bool](Get-PropertyValue $chain 'ok')){if([int](Get-PropertyValue $chain 'count') -gt 0){throw ('There are '+[int](Get-PropertyValue $chain 'count')+' unresolved ambiguous paid request(s). A new request requires an explicit retry from the latest linear retry chain; unrelated ambiguous outcomes must not be bypassed.')}}
        $cfg=Get-GenerationProviderRuntimeConfig;$confirmedDispatch=Assert-LocalGenerationDispatchBinding $ExpectedDispatchBinding $cfg;$provider=[string](Get-PropertyValue $cfg 'provider_key');$def=Get-GenerationProviderDefinition $provider;$readiness=Get-GenerationProviderLocalReadiness;if(-not[bool](Get-PropertyValue $readiness 'ready')){throw ('Production provider is not ready: '+[string](Get-PropertyValue $readiness 'code'))};$dailyLimit=[int](Get-PropertyValue $cfg 'daily_request_limit');$usedToday=[int](Get-PropertyValue $readiness 'paid_requests_today');if($provider-ne'local_comfy_flux2_klein_4b'-and$usedToday -ge $dailyLimit){throw ('Daily provider request limit reached: '+$usedToday+'/'+$dailyLimit)};$prompt=Get-LocalGenerationPrompt $c $identity;$promptSha=Get-StringSha256Hex $prompt;$jobId=('gen-'+[Guid]::NewGuid().ToString('N'))
        $model=[string](Get-PropertyValue $cfg 'model');if([string]::IsNullOrWhiteSpace($model)){$model=[string](Get-PropertyValue $def 'model')};$size=[string](Get-PropertyValue $cfg 'size');if([string]::IsNullOrWhiteSpace($size)){$size=[string](Get-PropertyValue $def 'size')};$quality=[string](Get-PropertyValue $cfg 'quality');if([string]::IsNullOrWhiteSpace($quality)){$quality=[string](Get-PropertyValue $def 'quality')};$background=[string](Get-PropertyValue $cfg 'background');if([string]::IsNullOrWhiteSpace($background)){$background=[string](Get-PropertyValue $def 'background')};$fmt=[string](Get-PropertyValue $cfg 'output_format');if([string]::IsNullOrWhiteSpace($fmt)){$fmt=[string](Get-PropertyValue $def 'output_format')};$count=[int](Get-PropertyValue $cfg 'output_count');if($count -lt 1){$count=[int](Get-PropertyValue $def 'output_count')};if($count -lt 1 -or $count -gt 4){throw 'Generation output count must be between 1 and 4.'}
        $registrySha=Get-LocalGenerationRegistrySha256;$contractVersion=[string](Get-PropertyValue $def 'contract_version');$configFingerprint=Get-GenerationProviderConfigFingerprint $cfg;$job=[ordered]@{schema='forge.generation_job.v4';job_id=$jobId;owner_action_id=('owner-'+[Guid]::NewGuid().ToString('N'));created_at=[DateTime]::UtcNow.ToString('o');request_kind=$Kind;max_provider_requests=1;automatic_retry=$false;ambiguity_policy='explicit_owner_action_required';prior_job_id=$PriorJobId;unresolved_ambiguous_ancestor_count=[int](Get-PropertyValue $chain 'count');concept_key=[string](Get-PropertyValue $c 'concept_key');source_revision_id=$identity.id;source_revision_hash=$identity.hash;brief_snapshot=$approved.brief;brief_sha256=$approved.sha256;brief_approval=$approved.approval;provider_key=$provider;provider_profile=[string](Get-PropertyValue $cfg 'profile_key');provider_contract_version=$contractVersion;provider_registry_sha256=$registrySha;provider_config_fingerprint=$configFingerprint;dispatch_confirmation=$confirmedDispatch;prompt_compiler_version=(Get-LocalGenerationPromptCompilerVersion);prompt_template_sha256=(Get-LocalGenerationPromptTemplateSha256);daily_request_limit=$dailyLimit;paid_requests_today_before=$usedToday;prompt=$prompt;prompt_sha256=$promptSha;render=[ordered]@{model=$model;size=$size;quality=$quality;background=$background;output_format=$fmt;output_count=$count};explicit_owner_action=$true;external_submission_authorized=$false}
        if($provider-eq'local_comfy_flux2_klein_4b'){$job.Remove('daily_request_limit');$job.Remove('paid_requests_today_before')}
        $stateLock=Enter-LocalCoreMutationLock;$null=Assert-LocalGenerationDispatchBinding $ExpectedDispatchBinding (Get-GenerationProviderRuntimeConfig);Assert-ForgeGenerationJobBriefApproval ([pscustomobject]$job) (Read-LocalCoreState)
        Ensure-Dir $script:GenerationOutboxRoot;$path=Get-LocalGenerationJobPath $jobId;$tmp=$path+'.tmp-'+[Guid]::NewGuid().ToString('N');$utf8=New-Object System.Text.UTF8Encoding -ArgumentList $false;[IO.File]::WriteAllText($tmp,($job|ConvertTo-Json -Depth 60),$utf8);Move-Item -LiteralPath $tmp -Destination $path -Force
        return [pscustomobject]@{job=[pscustomobject]$job;path=$path}   # object, so Get-PropertyValue can read job_id/provider_key
    } finally { if($null -ne $stateLock){try{$stateLock.Dispose()}catch{}};if($null -ne $actionLock){try{$actionLock.Dispose()}catch{}} }
}
function ConvertTo-LocalGenerationWorkerLiteral([string]$Value) { return ("'"+([string]$Value).Replace("'","''")+"'") }
function New-LocalGenerationWorkerEncodedCommand([string]$Worker,[string]$PackageRoot,[string]$JobPath) {
    $command=("& {0} -PackageRoot {1} -JobPath {2}" -f (ConvertTo-LocalGenerationWorkerLiteral $Worker),(ConvertTo-LocalGenerationWorkerLiteral $PackageRoot),(ConvertTo-LocalGenerationWorkerLiteral $JobPath))
    return [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
}
function Start-LocalGenerationWorker($Queued) {
    if($null -eq $Queued -or $null -eq (Get-PropertyValue $Queued 'path')){$e=[InvalidOperationException]::new('Generation job path is missing.');$e.Data['forge_worker_launch_not_attempted']=$true;throw $e};if(-not(Test-Path -LiteralPath $script:GenerationWorkerPath -PathType Leaf)){$e=[InvalidOperationException]::new('Generation worker is missing from this package.');$e.Data['forge_worker_launch_not_attempted']=$true;throw $e}
    $ps=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe';$sysnative=Join-Path $env:SystemRoot 'Sysnative\WindowsPowerShell\v1.0\powershell.exe';if(Test-Path -LiteralPath $sysnative){$ps=$sysnative};if(-not(Test-Path -LiteralPath $ps)){$e=[InvalidOperationException]::new('Windows PowerShell is unavailable.');$e.Data['forge_worker_launch_not_attempted']=$true;throw $e}
    $jobPath=[string](Get-PropertyValue $Queued 'path');$packageRoot=Split-Path -Parent $script:GenerationWorkerPath;$encoded=New-LocalGenerationWorkerEncodedCommand $script:GenerationWorkerPath $packageRoot $jobPath
    $args=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded);$p=Start-Process -FilePath $ps -ArgumentList $args -WindowStyle Hidden -PassThru;return $p.Id
}
function Get-LocalGenerationCancellationTarget($Row) {
    if($null-eq$Row-or$null-eq$script:Current-or[string](Get-PropertyValue $Row 'request_origin')-cne'local_worker'-or[string](Get-PropertyValue $Row 'provider_key')-cne'local_comfy_flux2_klein_4b'-or[string](Get-PropertyValue $Row 'status')-notin@('queued','running','ambiguous','completed_pending_import')){return $null}
    $id=[string](Get-PropertyValue $Row 'id');if($id-cnotmatch'^gen-[0-9a-f]{32}$'){return $null}
    try {
        $path=Get-LocalGenerationJobPath $id;$item=Get-Item -LiteralPath $path -Force -ErrorAction Stop
        if($item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)-or$item.Length-gt10MB){return $null}
        $payload=Read-LocalCheckEvidencePayload $path;$j=$payload.data;$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept
        if([string](Get-PropertyValue $j 'schema')-cne'forge.generation_job.v4'-or[string](Get-PropertyValue $j 'job_id')-cne$id-or[string](Get-PropertyValue $j 'provider_key')-cne'local_comfy_flux2_klein_4b'-or[string](Get-PropertyValue $j 'concept_key')-cne[string](Get-PropertyValue $script:Current.concept 'concept_key')-or[string](Get-PropertyValue $j 'source_revision_id')-cne$identity.id-or[string](Get-PropertyValue $j 'source_revision_hash')-cne$identity.hash){return $null}
        if(Test-LocalGenerationReceiptSatisfied (Get-LocalGenerationReceiptPath $id) ([string](Get-PropertyValue $j 'concept_key')) $identity.id $identity.hash){return $null}
        return [pscustomobject]@{job_id=$id;job_path=$path;job_sha256=$payload.sha256;cancel_path=($path+'.cancel')}
    } catch {return $null}
}
function Test-LocalGenerationWorkerIdentityAlive($Attempt,$Job,[string]$JobPath) {
    # PID existence is insufficient: Windows can assign the same number to a later process.
    try {
        if([string](Get-PropertyValue $Attempt 'schema')-cne'forge.generation_attempt.v1'-or[string](Get-PropertyValue $Attempt 'job_id')-cne[string](Get-PropertyValue $Job 'job_id')-or[string](Get-PropertyValue $Attempt 'provider_key')-cne[string](Get-PropertyValue $Job 'provider_key')-or[int](Get-PropertyValue $Attempt 'provider_request_count')-ne1){return $false}
        if([string](Get-PropertyValue $Attempt 'job_sha256')-cne(Get-FileSha256Hex $JobPath)){return $false}
        $workerId=[int](Get-PropertyValue $Attempt 'worker_pid');if($workerId-le0){return $false}
        $created=[DateTime]::Parse([string](Get-PropertyValue $Job 'created_at'),[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()
        $dispatch=[DateTime]::Parse([string](Get-PropertyValue $Attempt 'dispatch_started_at'),[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()
        if($dispatch-lt$created-or$dispatch-gt[DateTime]::UtcNow.AddMinutes(10)){return $false}
        $process=Get-Process -Id $workerId -ErrorAction Stop
        if([int]$process.Id-ne$workerId){return $false}
        $actualStart=([DateTime]$process.StartTime).ToUniversalTime()
        if($actualStart-lt$created-or$actualStart-gt$dispatch){return $false}
        $recordedStart=[string](Get-PropertyValue $Attempt 'worker_started_at')
        if($recordedStart){$expectedStart=[DateTime]::Parse($recordedStart,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime();if($actualStart.Ticks-ne$expectedStart.Ticks){return $false}}
        # Legacy journals have no exact start stamp; the process must still predate their dispatch.
        return $true
    } catch {return $false}
}
function Get-ForgeGenerationHistoryStatusText([string]$Status) {
    return (Get-UiText ('generation.history.'+$Status) (Get-UiText 'generation.history.unknown' 'Needs review'))
}
function Add-ForgeGenerationHistoryDisplay($Row) {
    $label=Get-ForgeGenerationHistoryStatusText ([string](Get-PropertyValue $Row 'status'))
    $display=([string](Get-PropertyValue $Row 'request_no'))+' | '+$label
    $failure=[string](Get-PropertyValue $Row 'failure_message');if($failure.Length-gt400){$failure=$failure.Substring(0,400)+'...'}
    if($failure){$display+="`n"+$failure}
    $Row|Add-Member NoteProperty display $display -Force
    return $Row
}
function New-ForgeInvalidGenerationHistoryRow([string]$Leaf,[string]$Reason) {
    # No action identifier: unknown/corrupt journal cannot become a cancellation or retry target.
    return (Add-ForgeGenerationHistoryDisplay ([pscustomobject]@{id='';request_no=$Leaf;request_kind='';request_origin='local_worker';provider_key='';status='journal_invalid';failure_message=((Get-UiText 'generation.history.invalid' 'Generation journal needs review. Original files were preserved. This check sends no new request and does not retry.')+' '+$Reason);created_at=''}))
}

function Get-LocalGenerationJobsForCurrent {
    if($null -eq $script:Current){return @()};$c=$script:Current.concept;$identity=Get-LocalCurrentRevisionIdentity $c;$key=[string](Get-PropertyValue $c 'concept_key');$out=@();if(-not(Test-Path -LiteralPath $script:GenerationOutboxRoot)){return @()};$expiry=Get-LocalGenerationPreDispatchExpiryMinutes
    foreach($f in @(Get-ChildItem -LiteralPath $script:GenerationOutboxRoot -Filter '*.json' -File -ErrorAction SilentlyContinue|Sort-Object LastWriteTimeUtc -Descending)){
        try{$j=(Read-ForgeGenerationJournalSnapshot $f.FullName 16777216).data}catch{$out+=@(New-ForgeInvalidGenerationHistoryRow $f.Name 'JSON');continue};if([string](Get-PropertyValue $j 'schema') -ne 'forge.generation_job.v4'){$out+=@(New-ForgeInvalidGenerationHistoryRow $f.Name 'Schema');continue};$journalId=[string](Get-PropertyValue $j 'job_id');if($journalId-cnotmatch'^gen-[0-9a-f]{32}$'-or$f.Name-ine($journalId+'.json')){$out+=@(New-ForgeInvalidGenerationHistoryRow $f.Name 'Identity');continue};if([string](Get-PropertyValue $j 'concept_key') -ne $key -or [string](Get-PropertyValue $j 'source_revision_id') -ne $identity.id -or [string](Get-PropertyValue $j 'source_revision_hash') -ne $identity.hash){continue}
        $id=[string](Get-PropertyValue $j 'job_id');$resultPath=Get-LocalGenerationResultPath $id;$receiptPath=Get-LocalGenerationReceiptPath $id;$attemptPath=Get-LocalGenerationAttemptPath $id;$status='queued';$failure=''
        if(Test-Path -LiteralPath $resultPath){
            try{$historyResultCapture=Read-ForgeGenerationJournalSnapshot $resultPath 16777216;$r=$historyResultCapture.data;$status=[string](Get-PropertyValue $r 'status');$failure=[string](Get-PropertyValue $r 'error_message');if($status -eq 'completed'){if(-not(Test-Path -LiteralPath $attemptPath -PathType Leaf)){$status='ambiguous'}else{try{$a=(Read-ForgeGenerationJournalSnapshot $attemptPath).data;if([string](Get-PropertyValue $a 'phase') -ne 'completed' -or [string](Get-PropertyValue $a 'result_sha256') -ne $historyResultCapture.sha256){$status='ambiguous'}else{$status='completed_pending_import'}}catch{$status='ambiguous'}}}}catch{if(Test-Path -LiteralPath $attemptPath -PathType Leaf){$status='ambiguous';$failure='Provider result is unreadable after a dispatch attempt.'}else{$status='result_invalid_pre_dispatch';$failure='Provider result is unreadable before any recorded dispatch.'}}
        } elseif(Test-Path -LiteralPath $attemptPath){
            try{$a=(Read-ForgeGenerationJournalSnapshot $attemptPath).data;$phase=[string](Get-PropertyValue $a 'phase');$alive=Test-LocalGenerationWorkerIdentityAlive $a $j $f.FullName;if($phase -in @('dispatching','response_received')){$status=if($alive){'running'}else{'ambiguous'}}elseif($phase -eq 'completed'){$status='ambiguous'}elseif($phase -eq 'pre_dispatch_failed'){$status='failed_pre_dispatch'}else{$status='ambiguous'}}catch{$status='ambiguous'}
        } else {
            try{$created=[DateTime]::Parse([string](Get-PropertyValue $j 'created_at')).ToUniversalTime();if(([DateTime]::UtcNow-$created).TotalMinutes -gt $expiry){$status='stale_pre_dispatch'}}catch{$status='stale_pre_dispatch'}
        }
        if([string](Get-PropertyValue $j 'provider_key')-ceq'local_comfy_flux2_klein_4b'-and(Test-Path -LiteralPath ($f.FullName+'.cancel'))){if($status-ceq'completed_pending_import'){$status='ambiguous'}elseif($status-in@('queued','stale_pre_dispatch')-and!(Test-Path -LiteralPath $attemptPath)){$status='failed_pre_dispatch'};$failure='Cancellation requested. Unimported result is retained and skipped; existing artwork is preserved. Review the journal before an explicit new request.'}
        if($script:GenerationImportIssues.ContainsKey($id+'.result.json')){$status='ambiguous';$failure=(Get-UiText 'generation.import.failed' 'Result verification/import failed; original files were preserved. Review the journal before an explicit retry.')+' '+[string]$script:GenerationImportIssues[$id+'.result.json']}
        if(Test-LocalGenerationReceiptSatisfied $receiptPath $key $identity.id $identity.hash){$status='imported';$failure=''}elseif((Test-Path -LiteralPath $receiptPath -PathType Leaf) -and $status -eq 'completed_pending_import'){$failure='Import receipt is invalid or incomplete; verified recovery/import is required before another paid request.'}
        $historyRow=[pscustomobject]@{id=$id;request_no=$id.Substring([Math]::Max(0,$id.Length-8));request_kind=[string](Get-PropertyValue $j 'request_kind');request_origin='local_worker';provider_key=[string](Get-PropertyValue $j 'provider_key');status=$status;failure_message=$failure;created_at=[string](Get-PropertyValue $j 'created_at')};$out+=@(Add-ForgeGenerationHistoryDisplay $historyRow)
    };return @($out)
}
function Test-LocalGenerationImportPromptContract($Job) {
    $compiler=[string](Get-PropertyValue $Job 'prompt_compiler_version');$template=[string](Get-PropertyValue $Job 'prompt_template_sha256');$registry=[string](Get-PropertyValue $Job 'provider_registry_sha256')
    if($compiler -eq (Get-LocalGenerationPromptCompilerVersion) -and $template -eq (Get-LocalGenerationPromptTemplateSha256) -and $registry -eq (Get-FileSha256Hex $script:GenerationProvidersPath)){return $true}
    # Read/import-only compatibility for the exact shipped 077 registry. This never permits dispatch.
    # All job/result/attempt/file hashes and exact-revision checks below still apply.
    return ($compiler -eq 'forge.prompt.apparel.v2' -and $template -eq '8f5e3bbdd3d8ec3e1205c6bf2d18e541a6b34532a82539c29320ae02e12efdd4' -and $registry -eq '9dd37f684592f10ae5134d5306834a00d45a4e3ed2bff3896d7ea5c0158dad39')
}
function Sync-LocalGenerationResults {
    if($null -eq $script:Current -or -not(Test-Path -LiteralPath $script:GenerationResultRoot)){return 0};$c=$script:Current.concept;$identity=Get-LocalCurrentRevisionIdentity $c;$key=[string](Get-PropertyValue $c 'concept_key');$imported=0
    foreach($rf in @(Get-ChildItem -LiteralPath $script:GenerationResultRoot -Filter '*.result.json' -File -ErrorAction SilentlyContinue|Sort-Object LastWriteTimeUtc)){
        $script:GenerationImportIssues.Remove($rf.Name)
        try {
        try{$resultCapture=Read-ForgeGenerationJournalSnapshot $rf.FullName 16777216;$r=$resultCapture.data}catch{continue};if([string](Get-PropertyValue $r 'schema') -ne 'forge.generation_result.v4' -or [string](Get-PropertyValue $r 'status') -ne 'completed'){continue};$jobId=[string](Get-PropertyValue $r 'job_id');if($jobId -notmatch '^gen-[0-9a-f]{32}$'){continue};$existingReceipt=Get-LocalGenerationReceiptPath $jobId;if((Test-LocalGenerationReceiptSatisfied $existingReceipt $key $identity.id $identity.hash)){continue};if([string](Get-PropertyValue $r 'concept_key') -ne $key -or [string](Get-PropertyValue $r 'source_revision_id') -ne $identity.id -or [string](Get-PropertyValue $r 'source_revision_hash') -ne $identity.hash){continue}
        $jobPath=Get-LocalGenerationJobPath $jobId;if(-not(Test-Path -LiteralPath $jobPath -PathType Leaf)){Write-AppLog 'WARN' ('Generation result has no source job: '+$jobId);continue};$jobCapture=Read-ForgeGenerationJournalSnapshot $jobPath 16777216;$jobSha=$jobCapture.sha256;if($jobSha -ne [string](Get-PropertyValue $r 'job_sha256')){Write-AppLog 'WARN' ('Generation job SHA mismatch: '+$jobId);continue}
        try{$j=$jobCapture.data}catch{Write-AppLog 'WARN' ('Generation job JSON is invalid: '+$jobId);continue}
        $provider=[string](Get-PropertyValue $r 'provider_key');if($provider-ceq'local_comfy_flux2_klein_4b'-and[string](Get-PropertyValue $j 'provider_key')-ceq$provider-and(Test-Path -LiteralPath ($jobPath+'.cancel'))){Write-AppLog 'INFO' ('Cancelled local result retained without import: '+$jobId);continue};$render=Get-PropertyValue $j 'render';$expectedCount=[int](Get-PropertyValue $render 'output_count');$assets=@((Get-PropertyValue $r 'assets'));$attemptPath=Get-LocalGenerationAttemptPath $jobId
        if(-not(Test-Path -LiteralPath $attemptPath -PathType Leaf)){Write-AppLog 'WARN' ('Generation result has no dispatch attempt journal: '+$jobId);continue};try{$attemptCapture=Read-ForgeGenerationJournalSnapshot $attemptPath;$attempt=$attemptCapture.data}catch{Write-AppLog 'WARN' ('Generation attempt journal is invalid: '+$jobId);continue}
        $resultSha=$resultCapture.sha256;if([string](Get-PropertyValue $attempt 'phase') -eq 'response_received' -and [string](Get-PropertyValue $attempt 'job_id') -eq $jobId -and [string](Get-PropertyValue $attempt 'job_sha256') -eq $jobSha -and [int](Get-PropertyValue $attempt 'provider_request_count') -eq 1 -and [string](Get-PropertyValue $r 'job_sha256') -eq $jobSha -and [string](Get-PropertyValue $r 'provider_registry_sha256') -eq [string](Get-PropertyValue $j 'provider_registry_sha256') -and [string](Get-PropertyValue $r 'provider_contract_version') -eq [string](Get-PropertyValue $j 'provider_contract_version') -and [string](Get-PropertyValue $r 'provider_config_fingerprint') -eq [string](Get-PropertyValue $j 'provider_config_fingerprint') -and [string](Get-PropertyValue $r 'prompt_compiler_version') -eq [string](Get-PropertyValue $j 'prompt_compiler_version') -and [string](Get-PropertyValue $r 'prompt_template_sha256') -eq [string](Get-PropertyValue $j 'prompt_template_sha256') -and [string](Get-PropertyValue $r 'prompt_sha256') -eq [string](Get-PropertyValue $j 'prompt_sha256')){try{$attempt.phase='completed';$attempt.completed_at=[string](Get-PropertyValue $r 'completed_at');$attempt.result_sha256=$resultSha;$tmpAttempt=$attemptPath+'.tmp-'+[Guid]::NewGuid().ToString('N');$utf8Attempt=New-Object System.Text.UTF8Encoding -ArgumentList $false;[IO.File]::WriteAllText($tmpAttempt,($attempt|ConvertTo-Json -Depth 20),$utf8Attempt);Move-Item -LiteralPath $tmpAttempt -Destination $attemptPath -Force;$attemptCapture=Read-ForgeGenerationJournalSnapshot $attemptPath;$attempt=$attemptCapture.data;Write-AppLog 'INFO' ('Recovered completed generation attempt journal from exact completed result: '+$jobId)}catch{Write-AppLog 'WARN' ('Generation attempt recovery failed: '+$jobId)}}
        if([string](Get-PropertyValue $j 'schema') -ne 'forge.generation_job.v4' -or [string](Get-PropertyValue $j 'job_id') -ne $jobId -or [int](Get-PropertyValue $j 'max_provider_requests') -ne 1 -or [bool](Get-PropertyValue $j 'automatic_retry') -ne $false -or [string](Get-PropertyValue $j 'provider_key') -ne $provider -or -not(Test-LocalGenerationImportPromptContract $j) -or [string](Get-PropertyValue $r 'provider_registry_sha256') -ne [string](Get-PropertyValue $j 'provider_registry_sha256') -or [string](Get-PropertyValue $r 'provider_contract_version') -ne [string](Get-PropertyValue $j 'provider_contract_version') -or [string](Get-PropertyValue $r 'provider_config_fingerprint') -ne [string](Get-PropertyValue $j 'provider_config_fingerprint') -or [string](Get-PropertyValue $r 'prompt_compiler_version') -ne [string](Get-PropertyValue $j 'prompt_compiler_version') -or [string](Get-PropertyValue $r 'prompt_template_sha256') -ne [string](Get-PropertyValue $j 'prompt_template_sha256') -or [string](Get-PropertyValue $j 'concept_key') -ne $key -or [string](Get-PropertyValue $j 'source_revision_id') -ne $identity.id -or [string](Get-PropertyValue $j 'source_revision_hash') -ne $identity.hash -or [string](Get-PropertyValue $j 'prompt_sha256') -ne [string](Get-PropertyValue $r 'prompt_sha256') -or [string](Get-PropertyValue $attempt 'schema') -ne 'forge.generation_attempt.v1' -or [string](Get-PropertyValue $attempt 'job_id') -ne $jobId -or [string](Get-PropertyValue $attempt 'job_sha256') -ne $jobSha -or [string](Get-PropertyValue $attempt 'prompt_compiler_version') -ne [string](Get-PropertyValue $j 'prompt_compiler_version') -or [string](Get-PropertyValue $attempt 'prompt_template_sha256') -ne [string](Get-PropertyValue $j 'prompt_template_sha256') -or [string](Get-PropertyValue $attempt 'phase') -ne 'completed' -or [int](Get-PropertyValue $attempt 'provider_request_count') -ne 1 -or [string](Get-PropertyValue $attempt 'result_sha256') -ne $resultSha -or $expectedCount -lt 1 -or $assets.Count -ne $expectedCount){Write-AppLog 'WARN' ('Generation result lineage/attempt does not match source job: '+$jobId);continue}
        $sm=[regex]::Match([string](Get-PropertyValue $render 'size'),'^(\d{3,4})x(\d{3,4})$');if(-not $sm.Success){Write-AppLog 'WARN' ('Generation job size is invalid during import: '+$jobId);continue};$expectedWidth=[int]$sm.Groups[1].Value;$expectedHeight=[int]$sm.Groups[2].Value
        $validated=@();$seen=@{};$ok=$true
        foreach($a in $assets){$leaf=[string](Get-PropertyValue $a 'file');$sha=([string](Get-PropertyValue $a 'sha256')).ToLowerInvariant();$mime=[string](Get-PropertyValue $a 'mime_type');if([string]::IsNullOrWhiteSpace($leaf) -or [IO.Path]::GetFileName($leaf) -ne $leaf -or $seen.ContainsKey($leaf.ToLowerInvariant()) -or $mime -ne 'image/png'){$ok=$false;break};$seen[$leaf.ToLowerInvariant()]=$true;$path=Join-Path $rf.DirectoryName $leaf;if(-not(Test-Path -LiteralPath $path -PathType Leaf) -or $sha -notmatch '^[0-9a-f]{64}$' -or (Get-FileSha256Hex $path) -ne $sha){$ok=$false;break};$png=if($provider-eq'local_comfy_flux2_klein_4b'){Test-ForgeLocalDraftPngBytes ([IO.File]::ReadAllBytes($path)) $expectedWidth $expectedHeight}else{Test-ForgeGenerationPngFile $path $expectedWidth $expectedHeight};if(-not[bool](Get-PropertyValue $png 'ok')){$ok=$false;break};$validated+=,[pscustomobject]@{path=$path;sha=$sha;asset=$a}}
        if(-not $ok){Write-AppLog 'WARN' ('Generation result assets failed verification: '+$jobId);continue}
        if($provider-ceq'local_comfy_flux2_klein_4b'-and(Test-Path -LiteralPath ($jobPath+'.cancel'))){Write-AppLog 'INFO' ('Cancellation observed before local artwork import: '+$jobId);continue}
        foreach($v in $validated){$asset=$v.asset;$prov=[pscustomobject]@{provider_profile=[string](Get-PropertyValue $r 'provider_profile');provider_model=[string](Get-PropertyValue $r 'model');provider_contract_version=[string](Get-PropertyValue $r 'provider_contract_version');provider_registry_sha256=[string](Get-PropertyValue $r 'provider_registry_sha256');provider_config_fingerprint=[string](Get-PropertyValue $r 'provider_config_fingerprint');prompt_compiler_version=[string](Get-PropertyValue $r 'prompt_compiler_version');prompt_template_sha256=[string](Get-PropertyValue $r 'prompt_template_sha256');provider_request_id=[string](Get-PropertyValue $r 'provider_request_id');generation_result_sha256=$resultSha;generation_attempt_sha256=$attemptCapture.sha256;prompt_sha256=[string](Get-PropertyValue $r 'prompt_sha256');revised_prompt=[string](Get-PropertyValue $asset 'revised_prompt');provider_usage=(Get-PropertyValue (Get-PropertyValue $r 'provider_response') 'usage')};$null=Add-LocalArtworkFromPath $v.path $jobId $provider $identity.id $identity.hash $v.sha $prov;$imported++}
        $assetShas=@($validated|ForEach-Object{$_.sha});$receipt=[ordered]@{schema='forge.generation_import_receipt.v4';job_id=$jobId;job_sha256=$jobSha;result_sha256=$resultSha;attempt_sha256=$attemptCapture.sha256;provider_key=$provider;provider_profile=[string](Get-PropertyValue $r 'provider_profile');provider_model=[string](Get-PropertyValue $r 'model');provider_contract_version=[string](Get-PropertyValue $r 'provider_contract_version');provider_registry_sha256=[string](Get-PropertyValue $r 'provider_registry_sha256');provider_config_fingerprint=[string](Get-PropertyValue $r 'provider_config_fingerprint');prompt_compiler_version=[string](Get-PropertyValue $r 'prompt_compiler_version');prompt_template_sha256=[string](Get-PropertyValue $r 'prompt_template_sha256');provider_request_id=[string](Get-PropertyValue $r 'provider_request_id');prompt_sha256=[string](Get-PropertyValue $r 'prompt_sha256');asset_sha256=$assetShas;imported_at=[DateTime]::UtcNow.ToString('o')};$receiptPath=Get-LocalGenerationReceiptPath $jobId;$tmp=$receiptPath+'.tmp-'+[Guid]::NewGuid().ToString('N');$utf8=New-Object System.Text.UTF8Encoding -ArgumentList $false;[IO.File]::WriteAllText($tmp,($receipt|ConvertTo-Json -Depth 10),$utf8);Move-Item -LiteralPath $tmp -Destination $receiptPath -Force
        } catch {
            $message=$_.Exception.Message;$script:GenerationImportIssues[$rf.Name]=$message
            Write-AppLog 'WARN' ('Generation result retained after isolated import failure: '+$rf.Name+'; '+$message)
        }
    };return $imported
}
function Queue-LocalGeneration([string]$Kind,[string]$PriorJobId='',$ExpectedDispatchBinding=$null) {
    $q=New-LocalGenerationJob $Kind $PriorJobId $ExpectedDispatchBinding
    $jobPath=[string](Get-PropertyValue $q 'path');$queuedSha=if($jobPath-and(Test-Path -LiteralPath $jobPath -PathType Leaf)){Get-FileSha256Hex $jobPath}else{''}
    try{$workerPid=Start-LocalGenerationWorker $q}catch{
        $launchError=$_;$jobId=[string](Get-PropertyValue (Get-PropertyValue $q 'job') 'job_id');$confirmedNotStarted=($launchError.Exception.Data['forge_worker_launch_not_attempted']-is[bool]-and$launchError.Exception.Data['forge_worker_launch_not_attempted'])
        $safeCleanup=$false
        if($confirmedNotStarted-and$queuedSha-and$jobId-match'^gen-[0-9a-f]{32}$'){
            try{$safeCleanup=(!(Test-Path -LiteralPath (Get-LocalGenerationAttemptPath $jobId))-and!(Test-Path -LiteralPath (Get-LocalGenerationResultPath $jobId))-and(Test-Path -LiteralPath $jobPath -PathType Leaf)-and(Get-FileSha256Hex $jobPath)-ceq$queuedSha)}catch{$safeCleanup=$false}
        }
        if($safeCleanup){try{Remove-Item -LiteralPath $jobPath -Force}catch{Write-AppLog 'WARN' ('Could not remove confirmed unstarted generation job: '+$jobPath)};throw}
        try{Write-AppLog 'WARN' ('Worker launch could not be confirmed; original job and any attempt/result journals retained: '+$jobPath+'; '+$launchError.Exception.Message)}catch{}
        throw [InvalidOperationException]::new(('Worker launch could not be confirmed. The original job was preserved; inspect its outcome before retrying. '+$launchError.Exception.Message),$launchError.Exception)
    }
    $script:LocalGenerationProviderMode=[string](Get-PropertyValue (Get-PropertyValue $q 'job') 'provider_key');return [pscustomobject]@{job=(Get-PropertyValue $q 'job');worker_pid=$workerPid}
}

function Register-GenerationRecoveryUiText {
    $text=@{
        en=@{
            'generation.next.settings'='Next request: {0} / {1}; model {2}; {3}; {4}; {5} output(s).';
            'generation.config.invalid'='Provider configuration is invalid and was preserved. Review or restore it before generating. {0}';
            'generation.settings.changed'='Provider or render settings changed, or their confirmation is missing. Review the current settings and confirm generation again. No job was created.';
            'generation.cancel.local'='Cancel selected local request';'generation.cancel.local.tip'='Skip future import for only this request. Running computation may finish; no shared process is interrupted.'
            'generation.cancel.server'='Cancel selected queued request';'generation.cancel.server.tip'='Cancel a queued generation request before provider dispatch'
            'generation.cancel.stale'='The selected local request is stale or does not belong to this exact idea. Refresh its history before cancelling.'
            'generation.cancel.requested'='Local cancellation requested. Any result not yet imported will be skipped; existing artwork is retained. Running computation may finish. No shared process interrupted.'
            'generation.unknown.title'='Provider outcome requires review'
            'generation.unknown.local'="Local request {0} has an unresolved or cancelled outcome. Unresolved requests in this revision chain: {1}. No automatic retry was attempted.`n`nStart ONE new explicit local preview request? This uses the local renderer and may use GPU resources. No paid image API is called."
            'generation.unknown.paid'="Provider request {0} has an unresolved outcome. Unresolved requests in this revision chain: {1}. No automatic retry was attempted. Another request may incur another charge.`n`nStart ONE new explicit request?"
        }
        ru=@{
            'generation.next.settings'='Новый запрос: {0} / {1}; модель {2}; {3}; {4}; результатов: {5}.';
            'generation.config.invalid'='Конфигурация провайдера повреждена и сохранена без изменений. Проверьте или восстановите её перед генерацией. {0}';
            'generation.settings.changed'='Настройки провайдера или рендера изменились либо их подтверждение отсутствует. Проверьте текущие настройки и подтвердите запрос заново. Задание не создано.';
            'generation.cancel.local'='Отменить выбранный локальный запрос';'generation.cancel.local.tip'='Не импортировать будущий результат только этого запроса. Вычисление может завершиться; общий процесс не останавливается.'
            'generation.cancel.server'='Отменить выбранный запрос в очереди';'generation.cancel.server.tip'='Отменить запрос в очереди до отправки провайдеру'
            'generation.cancel.stale'='Выбранный запрос устарел или относится к другой версии идеи. Обновите историю перед отменой.'
            'generation.cancel.requested'='Локальная отмена запрошена. Ещё не импортированный результат будет пропущен; существующий арт сохранён. Вычисление может завершиться. Общие процессы не остановлены.'
            'generation.unknown.title'='Нужно проверить исход запроса'
            'generation.unknown.local'="Локальный запрос {0}: исход не разрешён или запрошена отмена. Неразрешённых запросов в цепочке версии: {1}. Автоматического повтора не было.`n`nСоздать ОДИН новый локальный превью-запрос? Локальный рендер может использовать GPU. Платный API изображений не вызывается."
            'generation.unknown.paid'="Исход запроса {0} не разрешён. Неразрешённых запросов в цепочке версии: {1}. Автоматического повтора не было. Новый запрос может потребовать ещё одну оплату.`n`nСоздать ОДИН новый запрос?"
        }
        es=@{
            'generation.next.settings'='Nueva solicitud: {0} / {1}; modelo {2}; {3}; {4}; {5} resultado(s).';
            'generation.config.invalid'='La configuración del proveedor no es válida y se conservó. Revísala o restáurala antes de generar. {0}';
            'generation.settings.changed'='La configuración del proveedor o render cambió, o falta su confirmación. Revisa la configuración actual y confirma de nuevo. No se creó ninguna tarea.';
            'generation.cancel.local'='Cancelar solicitud local seleccionada';'generation.cancel.local.tip'='Omitir la futura importación solo de esta solicitud. El cálculo puede terminar; no se interrumpe ningún proceso compartido.'
            'generation.cancel.server'='Cancelar solicitud en cola seleccionada';'generation.cancel.server.tip'='Cancelar una solicitud en cola antes del envío al proveedor'
            'generation.cancel.stale'='La solicitud local está desactualizada o pertenece a otra revisión. Actualiza el historial antes de cancelar.'
            'generation.cancel.requested'='Cancelación local solicitada. Se omitirá cualquier resultado aún no importado; el arte existente se conserva. El cálculo puede terminar. Ningún proceso compartido interrumpido.'
            'generation.unknown.title'='El resultado requiere revisión'
            'generation.unknown.local'="La solicitud local {0} tiene un resultado sin resolver o cancelado. Solicitudes pendientes en esta revisión: {1}. No hubo reintento automático.`n`n¿Iniciar UNA nueva solicitud local de vista previa? El render local puede usar GPU. No se llama a una API de imágenes de pago."
            'generation.unknown.paid'="La solicitud {0} tiene un resultado sin resolver. Solicitudes pendientes en esta revisión: {1}. No hubo reintento automático. Otra solicitud puede generar otro cargo.`n`n¿Iniciar UNA nueva solicitud explícita?"
        }
    }
    $text.en['generation.import.failed']='Result verification/import failed; original files were preserved. Review the journal before an explicit retry.'
    $text.ru['generation.import.failed']='Проверка или импорт результата не завершены; исходные файлы сохранены. Проверьте журнал перед явным повтором.'
    $text.es['generation.import.failed']='Falló la verificación o importación del resultado; se conservaron los archivos originales. Revisa el registro antes de un reintento explícito.'
    $history=@{
      en=@{queued='Queued';running='Running';completed_pending_import='Completed; verification/import pending';imported='Imported; approval handled separately';ambiguous='Outcome unresolved; review required';stale_pre_dispatch='Expired before dispatch';failed_pre_dispatch='Stopped before dispatch';result_invalid_pre_dispatch='Invalid result before dispatch';journal_invalid='Journal needs review';unknown='Needs review';invalid='Generation journal needs review. Original files were preserved. This check sends no new request and does not retry.'}
      ru=@{queued='В очереди';running='Выполняется';completed_pending_import='Результат получен; ожидается проверка и импорт';imported='Импортировано; одобрение проверяется отдельно';ambiguous='Исход не установлен; требуется проверка';stale_pre_dispatch='Срок истёк до отправки';failed_pre_dispatch='Остановлено до отправки';result_invalid_pre_dispatch='Некорректный результат до отправки';journal_invalid='Журнал требует проверки';unknown='Требуется проверка';invalid='Журнал генерации требует проверки. Исходные файлы сохранены; новый запрос или повтор не выполнялись.'}
      es=@{queued='En cola';running='En ejecución';completed_pending_import='Resultado recibido; verificación e importación pendientes';imported='Importado; la aprobación se comprueba por separado';ambiguous='Resultado sin resolver; requiere revisión';stale_pre_dispatch='Caducó antes del envío';failed_pre_dispatch='Detenido antes del envío';result_invalid_pre_dispatch='Resultado inválido antes del envío';journal_invalid='El registro necesita revisión';unknown='Requiere revisión';invalid='El registro de generación necesita revisión. Se conservaron los archivos. Esta comprobación no envía solicitudes nuevas ni reintenta.'}
    }
    foreach($loc in $history.Keys){foreach($k in $history[$loc].Keys){$text[$loc]['generation.history.'+$k]=$history[$loc][$k]}}
    foreach($loc in $text.Keys){if($null-eq$script:UiText[$loc]){$script:UiText[$loc]=@{}};foreach($key in $text[$loc].Keys){$script:UiText[$loc][$key]=$text[$loc][$key]}}
}
function Get-LocalGenerationAmbiguousWarning($Row,[int]$Count,[string]$NextProvider,$NextConfig=$null) {
    if($null-ne$NextConfig){$NextProvider=[string](Get-PropertyValue $NextConfig 'provider_key')}
    $local=$NextProvider-ceq'local_comfy_flux2_klein_4b'
    $key=if($local){'generation.unknown.local'}else{'generation.unknown.paid'}
    $message=((Get-UiText $key 'Request {0} requires review; unresolved requests: {1}. No automatic retry. Start one explicit new request?')-f[string](Get-PropertyValue $Row 'id'),$Count)
    if($null-ne$NextConfig){$message+="`n`n"+((Get-UiText 'generation.next.settings' 'Next request: {0} / {1}; model {2}; {3}; {4}; {5} output(s).')-f[string](Get-PropertyValue $NextConfig 'provider_key'),[string](Get-PropertyValue $NextConfig 'profile_key'),[string](Get-PropertyValue $NextConfig 'model'),[string](Get-PropertyValue $NextConfig 'size'),[string](Get-PropertyValue $NextConfig 'quality'),[int](Get-PropertyValue $NextConfig 'output_count'))}
    return [pscustomobject]@{title=(Get-UiText 'generation.unknown.title' 'Provider outcome requires review');message=$message;local_preview=$local}
}