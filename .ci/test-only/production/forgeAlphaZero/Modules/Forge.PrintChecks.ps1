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
    try{$p=(Read-LocalCheckEvidencePayload $path).data}catch{return $null}
    if(!(Test-ForgeAmazonPrintProfile $p)){return $null}
    return $p
}
function Get-LocalPrintTechnicalSnapshot([string]$ArtworkPath,[ref]$CapturedInfo=$null) {
    if($null-ne$CapturedInfo){$CapturedInfo.Value=$null}
    if([string]::IsNullOrWhiteSpace($ArtworkPath)-or-not(Test-Path -LiteralPath $ArtworkPath -PathType Leaf)){return [pscustomobject]@{ok=$false;reason='artwork_missing'}}
    try{$info=Get-LocalArtworkInfo $ArtworkPath}catch{return [pscustomobject]@{ok=$false;reason=('decode_failed: '+$_.Exception.Message)}}
    if($null-ne$CapturedInfo){$CapturedInfo.Value=$info}
    $png=$null;if($info.mime_type-eq'image/png'){try{$png=Test-ForgePrintPngBytes $info.bytes $info.width_px $info.height_px}catch{}}
    $native=($null-ne$png -and [bool](Get-PropertyValue $png 'ok'))
    return [pscustomobject]@{ok=$true;sha256=$info.sha256;mime_type=$info.mime_type;file_size_bytes=[int64]$info.bytes.Length;width_px=[int]$info.width_px;height_px=[int]$info.height_px;png_native_validation=$native;png_validation_reason=if($null-ne$png){[string](Get-PropertyValue $png 'reason')}else{'not_png'};max_print_width_in_at_300ppi=[Math]::Round(([double]$info.width_px/300.0),2);max_print_height_in_at_300ppi=[Math]::Round(([double]$info.height_px/300.0),2)}
}
function Get-LocalPrintProductionSnapshot($Lc,$Identity,$Acceptance) {
    if($null-eq$Lc -or $null-eq$Identity -or $null-eq$Acceptance){return [pscustomobject]@{schema='forge.print_production_snapshot.v1';ready=$false;reason='missing_lineage'}}
    $path=[string](Get-PropertyValue $Acceptance 'local_file_path');$capturedInfo=$null;$tech=Get-LocalPrintTechnicalSnapshot $path ([ref]$capturedInfo);$profile=Get-LocalAmazonPrintProfile;$upload=$null
    if([string](Get-PropertyValue $Lc 'source_revision_id') -cne [string](Get-PropertyValue $Identity 'id') -or [string](Get-PropertyValue $Lc 'source_revision_hash') -cne [string](Get-PropertyValue $Identity 'hash')){return [pscustomobject]@{schema='forge.print_production_snapshot.v1';ready=$false;reason='saved_concept_revision_mismatch';technical=$tech}}
    if([string](Get-PropertyValue $Acceptance 'concept_revision_id') -cne [string](Get-PropertyValue $Identity 'id') -or [string](Get-PropertyValue $Acceptance 'revision_hash') -cne [string](Get-PropertyValue $Identity 'hash')){return [pscustomobject]@{schema='forge.print_production_snapshot.v1';ready=$false;reason='accepted_artwork_revision_mismatch';technical=$tech}}
    $expectedFingerprint=New-LocalAcceptanceFingerprint ([string](Get-PropertyValue $Lc 'concept_key')) ([string](Get-PropertyValue $Identity 'id')) ([string](Get-PropertyValue $Identity 'hash')) ([string](Get-PropertyValue $Acceptance 'asset_sha256'))
    if([string](Get-PropertyValue $Acceptance 'lineage_fingerprint') -cne $expectedFingerprint){return [pscustomobject]@{schema='forge.print_production_snapshot.v1';ready=$false;reason='accepted_artwork_fingerprint_mismatch';technical=$tech}}
    if([bool](Get-PropertyValue $tech 'ok') -and [string](Get-PropertyValue $tech 'sha256') -cne [string](Get-PropertyValue $Acceptance 'asset_sha256')){return [pscustomobject]@{schema='forge.print_production_snapshot.v1';ready=$false;reason='accepted_artwork_sha256_mismatch';technical=$tech}}
    $profileStatus=if($null-eq$profile){'missing_or_expired'}else{'owner_attested_current'};$ready=$false;$reason='channel_profile_missing_or_expired'
    if([bool](Get-PropertyValue $tech 'ok')){
        if($null-ne$profile){$exact=([int](Get-PropertyValue $tech 'width_px') -eq [int](Get-PropertyValue $profile 'canvas_width_px') -and [int](Get-PropertyValue $tech 'height_px') -eq [int](Get-PropertyValue $profile 'canvas_height_px'));$fmt=([string](Get-PropertyValue $tech 'mime_type') -eq 'image/png');$transparent=[bool](Get-PropertyValue $tech 'png_native_validation');$upload=Get-ForgeUploadTechnicalSnapshot $capturedInfo.bytes $profile;$exact=[bool]$upload.ok;$ready=($exact -and $fmt -and $transparent);$reason=if($ready){'exact_canvas_png_transparency_match'}elseif(-not$fmt){'accepted_artwork_is_not_png'}elseif(-not$exact){$why=[string](Get-PropertyValue $upload 'reason');if($why){$why}else{'upload_technical_constraints_not_verified'}}else{$why=[string](Get-PropertyValue $tech 'png_validation_reason');if($why){$why}else{'accepted_png_failed_native_print_validation'}}}
        else{$reason='channel_profile_missing_or_expired'}
    }else{$reason=[string](Get-PropertyValue $tech 'reason')}
    $technicalReady=$ready;$uploadSnapshot=$upload
    $qualityCheck=Get-PropertyValue (Get-PropertyValue $Lc 'checks') 'print'
    $qualityReviewed=([string](Get-PropertyValue $qualityCheck 'authority_kind')-eq'owner_attested_external' -and [string](Get-PropertyValue $qualityCheck 'source')-ne'trusted_local_check_worker' -and (Test-LocalCheckPass $qualityCheck $Lc 'print'))
    $preview=([string](Get-PropertyValue $Acceptance 'provider_key')-eq'local_comfy_flux2_klein_4b')
    if($preview){$ready=$false;$reason='local_flux_preview_requires_preparation'}
    elseif($ready-and-not$qualityReviewed){$ready=$false;$reason='exact_artwork_print_quality_review_required'}
    if($ready-and$null-ne$uploadSnapshot-and$uploadSnapshot.dimension_policy-eq'flexible'){$reason='upload_constraints_and_exact_file_review_match'}
    $productionStatus=if($ready){'ready'}elseif($preview){'preview'}else{'processing_or_review_required'}
    return [pscustomobject]@{schema='forge.print_production_snapshot.v1';ready=$ready;status=$productionStatus;technical_ready=$technicalReady;upload_technical=$uploadSnapshot;quality_reviewed=$qualityReviewed;quality_boundary='Canvas and alpha do not establish detail, edge quality or suitability at final print size. No upscaling or background removal performed.';reason=$reason;technical=$tech;channel_profile_status=$profileStatus;channel_profile=$profile;concept_revision_id=[string](Get-PropertyValue $Identity 'id');revision_hash=[string](Get-PropertyValue $Identity 'hash');acceptance_fingerprint=[string](Get-PropertyValue $Acceptance 'lineage_fingerprint');artwork_sha256=[string](Get-PropertyValue $Acceptance 'asset_sha256');created_at=[DateTime]::UtcNow.ToString('o')}
}
function Get-LocalCheckWorkerRequestPath([string]$RequestId){return Join-Path (Get-LocalCheckRequestRoot) ($RequestId+'.worker.json')}
function Get-LocalCheckWorkerResultPath([string]$RequestId){return Join-Path (Get-LocalCheckResultRoot) ($RequestId+'.result.json')}
function Preserve-LocalCheckSpoolArtifact([string]$Path,[string]$Kind) {
    $root=if($Kind-ceq'request'){Get-LocalCheckRequestRoot}elseif($Kind-ceq'result'){Get-LocalCheckResultRoot}else{throw 'Unknown check spool artifact kind.'}
    $rootFull=[IO.Path]::GetFullPath($root).TrimEnd('\','/');$full=[IO.Path]::GetFullPath($Path);$name=[IO.Path]::GetFileName($full)
    $match=[regex]::Match($name,'^worker-check-([0-9a-f]{24})\.(worker|result)\.json$')
    if([IO.Path]::GetDirectoryName($full)-ine$rootFull-or!$match.Success-or($Kind-ceq'request'-and$match.Groups[2].Value-cne'worker')-or($Kind-ceq'result'-and$match.Groups[2].Value-cne'result')){throw 'Check spool target is outside its exact owned folder.'}
    foreach($folder in @($script:StateRoot,(Get-LocalCheckSpoolRoot),$rootFull)){if(Test-Path -LiteralPath $folder){$item=Get-Item -LiteralPath $folder -Force;if(!$item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Redirected check spool was retained; retry stopped.'}}}
    if(!(Test-Path -LiteralPath $full)){return ''}
    $item=Get-Item -LiteralPath $full -Force;if($item.PSIsContainer-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Unrecognized check spool artifact was retained; retry stopped.'}
    $sha=Get-FileSha256Hex $full;$retained=Join-Path $rootFull ('retained-'+$match.Groups[1].Value+'-'+[guid]::NewGuid().ToString('N')+'.json')
    if([IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($retained))-ine$rootFull){throw 'Check retention target escaped its folder.'}
    [IO.File]::Move($full,$retained)
    if((Get-FileSha256Hex $retained)-cne$sha){throw 'Check artifact changed during retention. All remaining artifacts were preserved; retry stopped.'}
    Write-AppLog 'WARN' ('Unverified check artifact retained before retry: '+$retained)
    return $retained
}
function Set-LocalCheckProductionSnapshot($Lc,$Snapshot) {
    $old=Get-PropertyValue $Lc 'print_production'
    $oldComparable=if($null-ne$old){$old|Select-Object * -ExcludeProperty created_at|ConvertTo-Json -Depth 50 -Compress}else{''}
    $newComparable=if($null-ne$Snapshot){$Snapshot|Select-Object * -ExcludeProperty created_at|ConvertTo-Json -Depth 50 -Compress}else{''}
    if($oldComparable-ceq$newComparable){return $false}
    Add-OrSetProperty $Lc 'print_production' $Snapshot;return $true
}
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
            $existingPayload=Read-LocalCheckEvidencePayload $rp;$existing=$existingPayload.data
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
                ((Get-PropertyValue $existing 'external_submission_authorized')-is[bool]-and!(Get-PropertyValue $existing 'external_submission_authorized')))
        }catch{$reuse=$false}
    }
    if($reuse){return [pscustomobject]@{request=$existing;path=$rp;sha256=$existingPayload.sha256}}
    $null=Preserve-LocalCheckSpoolArtifact $rp 'request'
    $null=Preserve-LocalCheckSpoolArtifact $resultPath 'result'
    $tmp=$rp+'.tmp.'+[Guid]::NewGuid().ToString('N')
    $utf8=New-Object Text.UTF8Encoding -ArgumentList $false
    [IO.File]::WriteAllText($tmp,($req|ConvertTo-Json -Depth 20),$utf8)
    [IO.File]::Move($tmp,$rp)
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
    try{$r=(Read-LocalCheckEvidencePayload $ResultPath).data}catch{Write-AppLog 'WARN' ('Local check worker result unreadable: '+$_.Exception.Message);return $null}
    if([string](Get-PropertyValue $r 'schema')-ne'forge.check_worker_result.v1'){Write-AppLog 'WARN' ('Local check worker result rejected: schema mismatch');return $null}
    $worker=Join-Path (Split-Path -Parent $script:ModuleRoot) 'MerchForgeCheckWorker.ps1'
    if(-not(Test-Path -LiteralPath $worker -PathType Leaf)){Write-AppLog 'WARN' ('Local check worker result rejected: worker file missing');return $null}
    if([string](Get-PropertyValue $r 'worker_sha256') -ne (Get-FileSha256Hex $worker)){Write-AppLog 'WARN' ('Local check worker result rejected: worker_sha256 mismatch');return $null}
    if([string](Get-PropertyValue $r 'request_sha256') -ne [string](Get-PropertyValue $Queued 'sha256')){Write-AppLog 'WARN' ('Local check worker result rejected: request_sha256 mismatch');return $null}
    $queuedRequest=Get-PropertyValue $Queued 'request'
    if([string](Get-PropertyValue $r 'request_id') -ne [string](Get-PropertyValue $queuedRequest 'request_id')){Write-AppLog 'WARN' ('Local check worker result rejected: request_id mismatch');return $null}
    if([string](Get-PropertyValue $r 'concept_key') -ne [string](Get-PropertyValue $queuedRequest 'concept_key')){Write-AppLog 'WARN' ('Local check worker result rejected: concept_key mismatch');return $null}
    if([string](Get-PropertyValue $r 'listing_hash') -ne [string](Get-PropertyValue $queuedRequest 'listing_hash')){Write-AppLog 'WARN' ('Local check worker result rejected: listing_hash mismatch');return $null}
    $submission=Get-PropertyValue $r 'external_submission_authorized';$calls=Get-PropertyValue $r 'network_calls'
    if($submission-isnot[bool]-or$submission-or($calls-isnot[int]-and$calls-isnot[long])-or$calls-ne0){Write-AppLog 'WARN' 'Local check worker result has invalid submission/network authority flags';return $null}
    $production=Get-PropertyValue $r 'print_production';$ready=Get-PropertyValue $production 'ready';$quality=Get-PropertyValue $production 'quality_reviewed';$workerPrint=Get-PropertyValue $r 'print'
    if([string](Get-PropertyValue $production 'schema')-cne'forge.print_production_snapshot.v1'-or(Get-PropertyValue $production 'technical_ready')-isnot[bool]-or$ready-isnot[bool]-or$ready-or$quality-isnot[bool]-or$quality-or[string](Get-PropertyValue $workerPrint 'state')-cne'needs_review'-or[string](Get-PropertyValue $workerPrint 'authority_kind')-cne'none'){Write-AppLog 'WARN' 'Technical check worker cannot self-assert owner quality approval or production readiness';return $null}
    if([string](Get-PropertyValue $r 'concept_revision_id') -ne [string](Get-PropertyValue $Identity 'id')){Write-AppLog 'WARN' ('Local check worker result rejected: concept_revision_id mismatch');return $null}
    if([string](Get-PropertyValue $r 'revision_hash') -ne [string](Get-PropertyValue $Identity 'hash')){Write-AppLog 'WARN' ('Local check worker result rejected: revision_hash mismatch');return $null}
    if([string](Get-PropertyValue $r 'acceptance_fingerprint') -ne [string](Get-PropertyValue $Acceptance 'lineage_fingerprint')){Write-AppLog 'WARN' ('Local check worker result rejected: acceptance_fingerprint mismatch');return $null}
    if([string](Get-PropertyValue $r 'artwork_sha256') -ne [string](Get-PropertyValue $Acceptance 'asset_sha256')){Write-AppLog 'WARN' ('Local check worker result rejected: artwork_sha256 mismatch');return $null}
    return $r
}
function Sync-LocalCheckWorkerResult($Lc,$Identity,$Acceptance) {
    if($null-eq$Lc -or $null-eq$Identity -or $null-eq$Acceptance){return $false}
    $before=ConvertTo-Json -InputObject $Lc -Depth 60 -Compress
    $q=New-LocalCheckWorkerRequest $Lc $Identity $Acceptance
    $request=Get-PropertyValue $q 'request'
    $requestId=[string](Get-PropertyValue $request 'request_id')
    $resultPath=Get-LocalCheckWorkerResultPath $requestId
    $r=Get-ValidatedLocalCheckWorkerResult $q $resultPath $Identity $Acceptance
    if($null-eq$r){
        try{$null=Preserve-LocalCheckSpoolArtifact $resultPath 'result'}catch{Write-AppLog 'WARN' ($_.Exception.Message);return $false}
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
    $existingPrint=Get-PropertyValue (Get-PropertyValue $Lc 'checks') 'print'
    if([string](Get-PropertyValue $existingPrint 'source')-cne'trusted_local_check_worker'-and([string](Get-PropertyValue $existingPrint 'authority_kind')-ceq'owner_attested_external'-or[string](Get-PropertyValue $existingPrint 'evidence_capture_schema')-ceq'forge.local_check_capture.v1'-or[string](Get-PropertyValue $existingPrint 'source')-ceq'owner_in_app_checklist')){
        $null=Set-LocalCheckProductionSnapshot $Lc (Get-LocalPrintProductionSnapshot $Lc $Identity $Acceptance)
        return ((ConvertTo-Json -InputObject $Lc -Depth 60 -Compress)-cne$before)
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
    $null=Set-LocalCheckProductionSnapshot $Lc (Get-PropertyValue $r 'print_production')
    return ((ConvertTo-Json -InputObject $Lc -Depth 60 -Compress)-cne$before)
}
function Invoke-LocalCheckAutomation {
    if($null-eq$script:Current){return $false};$s=Read-LocalCoreState;$lc=Get-LocalCoreConcept ([string]$script:Current.concept.concept_key) $s;if($null-eq$lc -or $null-eq$lc.active_acceptance){return $false};$identity=Get-LocalCurrentRevisionIdentity $script:Current.concept;$acc=$lc.active_acceptance;if([string](Get-PropertyValue $acc 'concept_revision_id')-ne$identity.id -or [string](Get-PropertyValue $acc 'revision_hash')-ne$identity.hash){return $false};if(Sync-LocalCheckWorkerResult $lc $identity $acc){try{Write-LocalCoreState $s;return $true}catch{Write-AppLog 'WARN' ('Local check automation state write: '+$_.Exception.Message)}};return $false
}
