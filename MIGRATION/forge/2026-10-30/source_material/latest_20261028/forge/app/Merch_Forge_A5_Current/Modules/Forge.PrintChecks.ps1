# Merch Forge · print/channel profile + trusted local check-worker bridge
function Get-LocalCheckSpoolRoot { return (Join-Path $script:StateRoot 'check-spool-v1') }
function Get-LocalCheckRequestRoot { return (Join-Path (Get-LocalCheckSpoolRoot) 'requests') }
function Get-LocalCheckResultRoot { return (Join-Path (Get-LocalCheckSpoolRoot) 'results') }
function Get-LocalChannelProfileRoot { return (Join-Path $script:StateRoot 'channel-profiles') }
function Get-LocalAmazonPrintProfilePath { return (Join-Path (Get-LocalChannelProfileRoot) 'amazon-merch.json') }
function Initialize-PrintChecks {
    foreach($p in @((Get-LocalCheckSpoolRoot),(Get-LocalCheckRequestRoot),(Get-LocalCheckResultRoot),(Get-LocalChannelProfileRoot))){Ensure-Dir $p}
}
function ConvertTo-ForgeUtcDateTime($Value) {
    # Windows PowerShell 5.1 ConvertFrom-Json keeps ISO dates as strings; PowerShell 7 turns them into DateTime.
    # Casting a DateTime to [string] drops its zone, so handle both shapes explicitly.
    if($Value -is [DateTime]){ return $Value.ToUniversalTime() }
    return [DateTime]::Parse([string]$Value,[Globalization.CultureInfo]::InvariantCulture,[Globalization.DateTimeStyles]::RoundtripKind).ToUniversalTime()
}
function Get-LocalAmazonPrintProfile {
    $path=Get-LocalAmazonPrintProfilePath;if(-not(Test-Path -LiteralPath $path -PathType Leaf)){return $null}
    try{$p=Get-Content -LiteralPath $path -Raw -Encoding UTF8|ConvertFrom-Json}catch{return $null}
    if([string](Get-PropertyValue $p 'schema') -ne 'forge.amazon_print_profile.v1' -or [bool](Get-PropertyValue $p 'attested') -ne $true -or [string](Get-PropertyValue $p 'authority_kind') -ne 'owner_attested_external' -or [bool](Get-PropertyValue $p 'independent_verification') -ne $false){return $null}
    $w=[int](Get-PropertyValue $p 'canvas_width_px');$h=[int](Get-PropertyValue $p 'canvas_height_px');$dpi=[int](Get-PropertyValue $p 'dpi');$fmt=([string](Get-PropertyValue $p 'file_format')).ToLowerInvariant();$bg=([string](Get-PropertyValue $p 'background')).ToLowerInvariant();$tsha=([string](Get-PropertyValue $p 'template_file_sha256')).ToLowerInvariant();$sourceSha=([string](Get-PropertyValue $p 'source_file_sha256')).ToLowerInvariant();$refs=@(Get-PropertyValue $p 'source_refs');$market=[string](Get-PropertyValue $p 'marketplace');$product=[string](Get-PropertyValue $p 'product_type_key');$template=[string](Get-PropertyValue $p 'template_key')
    if($w-lt500 -or $w-gt10000 -or $h-lt500 -or $h-gt10000 -or $dpi-lt72 -or $dpi-gt600 -or $fmt-ne'png' -or $bg-ne'transparent' -or $tsha-notmatch'^[0-9a-f]{64}$' -or $sourceSha-notmatch'^[0-9a-f]{64}$' -or $refs.Count-lt1 -or [string]::IsNullOrWhiteSpace($market) -or [string]::IsNullOrWhiteSpace($product) -or [string]::IsNullOrWhiteSpace($template)){return $null}
    foreach($r in $refs){try{$u=[Uri][string]$r;$refHost=$u.Host.ToLowerInvariant();if($u.Scheme-ne'https' -or $refHost-notin@('developer.amazon.com','merch.amazon.com','sellercentral.amazon.com')){return $null}}catch{return $null}}
    try{$capt=ConvertTo-ForgeUtcDateTime (Get-PropertyValue $p 'captured_at');$vu=ConvertTo-ForgeUtcDateTime (Get-PropertyValue $p 'valid_until');if($capt-gt[DateTime]::UtcNow.AddMinutes(10) -or $vu-lt[DateTime]::UtcNow -or $vu-le$capt -or ($vu-$capt).TotalDays-gt120){return $null}}catch{return $null}
    return $p
}
function Get-LocalPrintTechnicalSnapshot([string]$ArtworkPath) {
    if(-not(Test-Path -LiteralPath $ArtworkPath -PathType Leaf)){return [pscustomobject]@{ok=$false;reason='artwork_missing'}}
    try{$info=Get-LocalArtworkInfo $ArtworkPath}catch{return [pscustomobject]@{ok=$false;reason=('decode_failed: '+$_.Exception.Message)}}
    $png=$null;if($info.mime_type-eq'image/png'){try{$png=Test-ForgeGenerationPngFile $ArtworkPath $info.width_px $info.height_px}catch{}}
    $native=($null-ne$png -and [bool](Get-PropertyValue $png 'ok'))
    return [pscustomobject]@{ok=$true;sha256=$info.sha256;mime_type=$info.mime_type;file_size_bytes=[int64]$info.bytes.Length;width_px=[int]$info.width_px;height_px=[int]$info.height_px;png_native_validation=$native;png_validation_reason=if($null-ne$png){[string](Get-PropertyValue $png 'reason')}else{'not_png'};max_print_width_in_at_300ppi=[Math]::Round(([double]$info.width_px/300.0),2);max_print_height_in_at_300ppi=[Math]::Round(([double]$info.height_px/300.0),2)}
}
function Get-LocalPrintProductionSnapshot($Lc,$Identity,$Acceptance) {
    if($null-eq$Lc -or $null-eq$Identity -or $null-eq$Acceptance){return [pscustomobject]@{schema='forge.print_production_snapshot.v1';ready=$false;reason='missing_lineage'}}
    $path=[string](Get-PropertyValue $Acceptance 'local_file_path');$tech=Get-LocalPrintTechnicalSnapshot $path;$profile=Get-LocalAmazonPrintProfile
    $profileStatus=if($null-eq$profile){'missing_or_expired'}else{'owner_attested_current'};$ready=$false;$reason='channel_profile_missing_or_expired'
    if([bool](Get-PropertyValue $tech 'ok')){
        if($null-ne$profile){$exact=([int](Get-PropertyValue $tech 'width_px') -eq [int](Get-PropertyValue $profile 'canvas_width_px') -and [int](Get-PropertyValue $tech 'height_px') -eq [int](Get-PropertyValue $profile 'canvas_height_px'));$fmt=([string](Get-PropertyValue $tech 'mime_type') -eq 'image/png');$transparent=[bool](Get-PropertyValue $tech 'png_native_validation');$ready=($exact -and $fmt -and $transparent);$reason=if($ready){'exact_canvas_png_transparency_match'}elseif(-not$exact){'accepted_artwork_dimensions_do_not_match_attested_channel_template'}elseif(-not$fmt){'accepted_artwork_is_not_png'}else{'accepted_png_failed_transparency_validation'}}
        else{$reason='channel_profile_missing_or_expired'}
    }else{$reason=[string](Get-PropertyValue $tech 'reason')}
    return [pscustomobject]@{schema='forge.print_production_snapshot.v1';ready=$ready;reason=$reason;technical=$tech;channel_profile_status=$profileStatus;channel_profile=$profile;concept_revision_id=[string](Get-PropertyValue $Identity 'id');revision_hash=[string](Get-PropertyValue $Identity 'hash');acceptance_fingerprint=[string](Get-PropertyValue $Acceptance 'lineage_fingerprint');artwork_sha256=[string](Get-PropertyValue $Acceptance 'asset_sha256');created_at=[DateTime]::UtcNow.ToString('o')}
}
function Get-LocalCheckWorkerRequestPath([string]$RequestId){return Join-Path (Get-LocalCheckRequestRoot) ($RequestId+'.worker.json')}
function Get-LocalCheckWorkerResultPath([string]$RequestId){return Join-Path (Get-LocalCheckResultRoot) ($RequestId+'.result.json')}
function New-LocalCheckWorkerRequest($Lc,$Identity,$Acceptance) {
    Initialize-PrintChecks
    $path=[string](Get-PropertyValue $Acceptance 'local_file_path')
    $sha=([string](Get-PropertyValue $Acceptance 'asset_sha256')).ToLowerInvariant()
    if(-not(Test-Path -LiteralPath $path -PathType Leaf) -or (Get-FileSha256Hex $path)-ne$sha){throw 'Accepted artwork is missing or failed SHA verification for local check worker.'}
    $listingHash=Get-LocalPublicationHash (Get-PropertyValue $Lc 'publication')
    $profilePath=Get-LocalAmazonPrintProfilePath
    $profileSha=if(Test-Path -LiteralPath $profilePath -PathType Leaf){Get-FileSha256Hex $profilePath}else{''}
    $workerPath=Join-Path (Split-Path -Parent $script:ModuleRoot) 'MerchForgeCheckWorker.ps1'
    $workerSha=if(Test-Path -LiteralPath $workerPath -PathType Leaf){Get-FileSha256Hex $workerPath}else{''}
    $material=((@([string](Get-PropertyValue $Lc 'concept_key'),[string](Get-PropertyValue $Identity 'id'),[string](Get-PropertyValue $Identity 'hash'),$sha,$listingHash,$profileSha,$workerSha)-join '|').ToLowerInvariant())
    $requestId=('worker-check-'+(Get-StringSha256Hex $material).Substring(0,24))
    $req=[ordered]@{
        schema='forge.check_worker_request.v1'
        request_id=$requestId
        created_at=[DateTime]::UtcNow.ToString('o')
        concept_key=[string](Get-PropertyValue $Lc 'concept_key')
        concept_revision_id=[string](Get-PropertyValue $Identity 'id')
        revision_hash=[string](Get-PropertyValue $Identity 'hash')
        acceptance_fingerprint=[string](Get-PropertyValue $Acceptance 'lineage_fingerprint')
        artwork_path=$path
        artwork_sha256=$sha
        listing_hash=$listingHash
        channel_profile_path=if(Test-Path -LiteralPath $profilePath -PathType Leaf){$profilePath}else{''}
        channel_profile_sha256=$profileSha
        worker_sha256=$workerSha
        external_submission_authorized=$false
    }
    $rp=Get-LocalCheckWorkerRequestPath $requestId
    $resultPath=Get-LocalCheckWorkerResultPath $requestId
    $reuse=$false
    if(Test-Path -LiteralPath $rp -PathType Leaf){
        try{
            $existing=Get-Content -LiteralPath $rp -Raw -Encoding UTF8|ConvertFrom-Json
            $reuse=([string](Get-PropertyValue $existing 'schema') -eq 'forge.check_worker_request.v1' -and
                [string](Get-PropertyValue $existing 'request_id') -eq $requestId -and
                [string](Get-PropertyValue $existing 'concept_key') -eq [string]$req.concept_key -and
                [string](Get-PropertyValue $existing 'concept_revision_id') -eq [string]$req.concept_revision_id -and
                [string](Get-PropertyValue $existing 'revision_hash') -eq [string]$req.revision_hash -and
                [string](Get-PropertyValue $existing 'acceptance_fingerprint') -eq [string]$req.acceptance_fingerprint -and
                [string](Get-PropertyValue $existing 'artwork_path') -eq [string]$req.artwork_path -and
                [string](Get-PropertyValue $existing 'artwork_sha256') -eq [string]$req.artwork_sha256 -and
                [string](Get-PropertyValue $existing 'listing_hash') -eq [string]$req.listing_hash -and
                [string](Get-PropertyValue $existing 'channel_profile_path') -eq [string]$req.channel_profile_path -and
                [string](Get-PropertyValue $existing 'channel_profile_sha256') -eq [string]$req.channel_profile_sha256 -and
                [string](Get-PropertyValue $existing 'worker_sha256') -eq [string]$req.worker_sha256 -and
                -not[bool](Get-PropertyValue $existing 'external_submission_authorized'))
        }catch{$reuse=$false}
    }
    if($reuse){return [pscustomobject]@{request=$existing;path=$rp;sha256=(Get-FileSha256Hex $rp)}}
    Remove-Item -LiteralPath $rp -Force -ErrorAction SilentlyContinue
    Remove-Item -LiteralPath $resultPath -Force -ErrorAction SilentlyContinue
    $tmp=$rp+'.tmp.'+[Guid]::NewGuid().ToString('N')
    $utf8=New-Object Text.UTF8Encoding -ArgumentList $false
    [IO.File]::WriteAllText($tmp,($req|ConvertTo-Json -Depth 20),$utf8)
    Move-Item -LiteralPath $tmp -Destination $rp -Force
    # Callers read fields with Get-PropertyValue, which cannot see dictionary keys: return an object, like the reuse path.
    return [pscustomobject]@{request=[pscustomobject]$req;path=$rp;sha256=(Get-FileSha256Hex $rp)}
}
function ConvertTo-LocalCheckWorkerLiteral([string]$Value) { return ("'"+([string]$Value).Replace("'","''")+"'") }
function New-LocalCheckWorkerEncodedCommand([string]$Worker,[string]$PackageRoot,[string]$RequestPath) {
    $command=("& {0} -PackageRoot {1} -RequestPath {2}" -f (ConvertTo-LocalCheckWorkerLiteral $Worker),(ConvertTo-LocalCheckWorkerLiteral $PackageRoot),(ConvertTo-LocalCheckWorkerLiteral $RequestPath))
    return [Convert]::ToBase64String([Text.Encoding]::Unicode.GetBytes($command))
}
function Start-LocalCheckWorker($Queued) {
    if($null-eq$Queued){return $null};$worker=Join-Path (Split-Path -Parent $script:ModuleRoot) 'MerchForgeCheckWorker.ps1';if(-not(Test-Path -LiteralPath $worker -PathType Leaf)){throw 'Trusted local check worker is missing.'};$ps=Join-Path $env:SystemRoot 'System32\WindowsPowerShell\v1.0\powershell.exe';$sysnative=Join-Path $env:SystemRoot 'Sysnative\WindowsPowerShell\v1.0\powershell.exe';if(Test-Path -LiteralPath $sysnative){$ps=$sysnative};if(-not(Test-Path -LiteralPath $ps)){throw 'Windows PowerShell is unavailable.'}
    $packageRoot=Split-Path -Parent $script:ModuleRoot;$requestPath=[string](Get-PropertyValue $Queued 'path');$encoded=New-LocalCheckWorkerEncodedCommand $worker $packageRoot $requestPath
    $args=@('-NoLogo','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-EncodedCommand',$encoded);$p=Start-Process -FilePath $ps -ArgumentList $args -WindowStyle Hidden -PassThru;$null=$p.Handle;$null=$p.WaitForExit(15000);if(-not$p.HasExited){try{$p.Kill()}catch{};throw 'Local check worker timed out.'};$p.WaitForExit();if($p.ExitCode-ne0){throw ('Local check worker failed with exit code '+$p.ExitCode+'.')};return $p.ExitCode
}
function Get-ValidatedLocalCheckWorkerResult($Queued,[string]$ResultPath,$Identity,$Acceptance) {
    if($null-eq$Queued -or -not(Test-Path -LiteralPath $ResultPath -PathType Leaf)){return $null}
    try{$r=Get-Content -LiteralPath $ResultPath -Raw -Encoding UTF8|ConvertFrom-Json}catch{Write-AppLog 'WARN' ('Local check worker result unreadable: '+$_.Exception.Message);return $null}
    if([string](Get-PropertyValue $r 'schema')-ne'forge.check_worker_result.v1'){Write-AppLog 'WARN' ('Local check worker result rejected: schema mismatch');return $null}
    $worker=Join-Path (Split-Path -Parent $script:ModuleRoot) 'MerchForgeCheckWorker.ps1'
    if(-not(Test-Path -LiteralPath $worker -PathType Leaf)){Write-AppLog 'WARN' ('Local check worker result rejected: worker file missing');return $null}
    if([string](Get-PropertyValue $r 'worker_sha256') -ne (Get-FileSha256Hex $worker)){Write-AppLog 'WARN' ('Local check worker result rejected: worker_sha256 mismatch');return $null}
    if([string](Get-PropertyValue $r 'request_sha256') -ne [string](Get-PropertyValue $Queued 'sha256')){Write-AppLog 'WARN' ('Local check worker result rejected: request_sha256 mismatch');return $null}
    $queuedRequest=Get-PropertyValue $Queued 'request'
    if([string](Get-PropertyValue $r 'request_id') -ne [string](Get-PropertyValue $queuedRequest 'request_id')){Write-AppLog 'WARN' ('Local check worker result rejected: request_id mismatch');return $null}
    if([string](Get-PropertyValue $r 'concept_key') -ne [string](Get-PropertyValue $queuedRequest 'concept_key')){Write-AppLog 'WARN' ('Local check worker result rejected: concept_key mismatch');return $null}
    if([string](Get-PropertyValue $r 'listing_hash') -ne [string](Get-PropertyValue $queuedRequest 'listing_hash')){Write-AppLog 'WARN' ('Local check worker result rejected: listing_hash mismatch');return $null}
    if([bool](Get-PropertyValue $r 'external_submission_authorized')){Write-AppLog 'WARN' ('Local check worker result rejected: external submission flag set');return $null}
    if([string](Get-PropertyValue $r 'concept_revision_id') -ne [string](Get-PropertyValue $Identity 'id')){Write-AppLog 'WARN' ('Local check worker result rejected: concept_revision_id mismatch');return $null}
    if([string](Get-PropertyValue $r 'revision_hash') -ne [string](Get-PropertyValue $Identity 'hash')){Write-AppLog 'WARN' ('Local check worker result rejected: revision_hash mismatch');return $null}
    if([string](Get-PropertyValue $r 'acceptance_fingerprint') -ne [string](Get-PropertyValue $Acceptance 'lineage_fingerprint')){Write-AppLog 'WARN' ('Local check worker result rejected: acceptance_fingerprint mismatch');return $null}
    if([string](Get-PropertyValue $r 'artwork_sha256') -ne [string](Get-PropertyValue $Acceptance 'asset_sha256')){Write-AppLog 'WARN' ('Local check worker result rejected: artwork_sha256 mismatch');return $null}
    return $r
}
function Sync-LocalCheckWorkerResult($Lc,$Identity,$Acceptance) {
    if($null-eq$Lc -or $null-eq$Identity -or $null-eq$Acceptance){return $false}
    $q=New-LocalCheckWorkerRequest $Lc $Identity $Acceptance
    $request=Get-PropertyValue $q 'request'
    $requestId=[string](Get-PropertyValue $request 'request_id')
    $resultPath=Get-LocalCheckWorkerResultPath $requestId
    $r=Get-ValidatedLocalCheckWorkerResult $q $resultPath $Identity $Acceptance
    if($null-eq$r){
        Remove-Item -LiteralPath $resultPath -Force -ErrorAction SilentlyContinue
        try{$null=Start-LocalCheckWorker $q}catch{Write-AppLog 'WARN' ('Local check worker: '+$_.Exception.Message)}
        $r=Get-ValidatedLocalCheckWorkerResult $q $resultPath $Identity $Acceptance
    }
    if($null-eq$r){Write-AppLog 'WARN' ('Local check worker produced no valid result at '+$resultPath+' (exists='+(Test-Path -LiteralPath $resultPath)+')');return $false}
    $print=Get-PropertyValue $r 'print'
    if($null-eq$print){Write-AppLog 'WARN' 'Local check worker result has no print section';return $false}
    $state=[string](Get-PropertyValue $print 'state')
    $authority=[string](Get-PropertyValue $print 'authority_kind')
    $refs=@(Get-PropertyValue $print 'evidence_refs')
    if($state-eq'pass'){
        if($authority-ne'owner_attested_external' -or $refs.Count-lt1){Write-AppLog 'WARN' ('Local check worker pass without authority/refs: '+$authority+' refs='+$refs.Count);return $false}
    }else{
        $authority='none';$refs=@()
    }
    $Lc.checks.print=[pscustomobject]@{
        state=$state
        source='trusted_local_check_worker'
        note=[string](Get-PropertyValue $print 'note')
        checked_at=[string](Get-PropertyValue $r 'checked_at')
        scope='artwork'
        concept_revision_id=[string](Get-PropertyValue $Identity 'id')
        asset_sha256=[string](Get-PropertyValue $Acceptance 'asset_sha256')
        listing_hash=''
        authority_kind=$authority
        evidence_refs=@($refs)
        evidence_source_file_sha256=[string](Get-PropertyValue $r 'profile_source_file_sha256')
        evidence_schema='forge.check_worker_result.v1'
    }
    Add-OrSetProperty $Lc 'print_production' (Get-PropertyValue $r 'print_production')
    return $true
}
function Invoke-LocalCheckAutomation {
    if($null-eq$script:Current){return $false};$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null-eq$lc -or $null-eq$lc.active_acceptance){return $false};$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$acc=$lc.active_acceptance;if([string](Get-PropertyValue $acc 'concept_revision_id')-ne$identity.id -or [string](Get-PropertyValue $acc 'revision_hash')-ne$identity.hash){return $false};if(Sync-LocalCheckWorkerResult $lc $identity $acc){try{Write-LocalCoreState $s;return $true}catch{Write-AppLog 'WARN' ('Local check automation state write: '+$_.Exception.Message)}};return $false
}
