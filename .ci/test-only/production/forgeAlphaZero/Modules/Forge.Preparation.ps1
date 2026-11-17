# BiRefNet preparation is an unaccepted derivative, never print approval.
function Assert-ForgePreparationConfigDocument($Cfg) {
    $root='CI_UNCONFIGURED/runtime-0';$model='CI_UNCONFIGURED/runtime-1'
    $workerSha='a7464789643ac6f4293100202527dd7e37ea1f6ba309a8f781dcd25a6119d9a1';$modelSha='9ab37426bf4de0567af6b5d21b16151357149139362e6e8992021b8ce356a154'
    if($Cfg-isnot[pscustomobject]-or$Cfg.schema-cne'forge.preparation_provider.v1'-or$Cfg.root-cne$root-or$Cfg.worker-cne(Join-Path $root 'birefnet_worker.py')-or$Cfg.worker_sha256-cne$workerSha-or$Cfg.model_sha256-cne$modelSha-or$Cfg.python-cne'CI_UNCONFIGURED/runtime-2'){throw 'Preparation configuration does not bind the reviewed installed CPU worker and model.'}
    if($Cfg.device-cne'cpu'-or$Cfg.threads-isnot[int]-or$Cfg.threads-ne2-or$Cfg.owner_approval_authorized-isnot[bool]-or$Cfg.owner_approval_authorized-or$Cfg.print_ready_authorized-isnot[bool]-or$Cfg.print_ready_authorized){throw 'Preparation configuration cannot change CPU policy or grant owner/print authority.'}
    $expected=@{}
    $expected[(Join-Path $root 'birefnet_worker.py')]=$workerSha
    $expected[(Join-Path $root 'site-packages\timm\__init__.py')]='9668df8ff48b33f846428cd7607399cf14b4f0feef157930eabf6defe932b1d3'
    $expected[(Join-Path $model 'model.safetensors')]=$modelSha
    $expected[(Join-Path $model 'birefnet.py')]='208771ae626f653d64128fbf2d6ac9f8e645c5cc5e286258a73ec3322bbfe5ef'
    $expected[(Join-Path $model 'BiRefNet_config.py')]='e7b8c2a74f6cea6a59553d517f71d47f2c1d90e670a13416af17c25fe2f3dc52'
    if($Cfg.files-isnot[Array]-or$Cfg.files.Count-ne$expected.Count){throw 'Preparation component attestation is incomplete.'}
    $seen=@{};foreach($f in $Cfg.files){if($f-isnot[pscustomobject]-or$f.path-isnot[string]-or!$expected.ContainsKey($f.path)-or$seen.ContainsKey($f.path)-or$f.sha256-isnot[string]-or$f.sha256-cne$expected[$f.path]){throw 'Preparation component path/hash binding is invalid or duplicated.'};$seen[$f.path]=$true}
}
function Assert-ForgePreparationChecks($Result) {
    if($Result-isnot[pscustomobject]-or$Result.checks-isnot[pscustomobject]-or(Get-PropertyValue $Result 'artwork_preservation_review_required')-isnot[bool]){throw 'Preparation checks require an explicit typed preservation-review decision.'}
    $c=$Result.checks
    foreach($n in @('nonempty','transparent_border','rgb_preserved','dimensions_preserved','edge_review_required','detail_quality_verified')){if((Get-PropertyValue $c $n)-isnot[bool]){throw ('Preparation check must be boolean: '+$n)}}
    if(!$c.edge_review_required-or$c.detail_quality_verified){throw 'Preparation remains advisory: edge review is required and detail quality is not verified.'}
    foreach($n in @('interior_pixel_retention','contrasting_pixel_retention')){$v=Get-PropertyValue $c $n;if(($v-isnot[int]-and$v-isnot[long]-and$v-isnot[double]-and$v-isnot[decimal])-or[double]::IsNaN([double]$v)-or[double]::IsInfinity([double]$v)-or$v-lt0-or$v-gt1){throw ('Preparation retention must be finite numeric0..1: '+$n)}}
    foreach($n in @('opaque_pixels','clear_pixels','lost_contrasting_source_pixels','contrasting_source_pixels','interior_source_pixels','interior_pixels_lost')){$v=Get-PropertyValue $c $n;if(($v-isnot[int]-and$v-isnot[long])-or$v-lt0-or$v-gt50000000){throw ('Invalid preparation pixel count: '+$n)}}
    if($c.lost_contrasting_source_pixels-gt$c.contrasting_source_pixels-or$c.interior_pixels_lost-gt$c.interior_source_pixels-or$c.interior_source_pixels-gt$c.contrasting_source_pixels){throw 'Preparation pixel loss counts contradict their source counts.'}
    $interiorLoss=[double]$c.interior_pixels_lost/[math]::Max(1,$c.interior_source_pixels);$contrastLoss=[double]$c.lost_contrasting_source_pixels/[math]::Max(1,$c.contrasting_source_pixels);$interior=1.0-$interiorLoss;$contrast=1.0-$contrastLoss
    if([math]::Abs($interior-[double]$c.interior_pixel_retention)-gt0.000001-or[math]::Abs($contrast-[double]$c.contrasting_pixel_retention)-gt0.000001){throw 'Preparation retention ratios contradict pixel loss counts.'}
    $requiresReview=$c.interior_source_pixels-eq0-or$interiorLoss-gt0.005-or$contrastLoss-gt0.1
    if($Result.artwork_preservation_review_required-ne$requiresReview){throw 'Preparation preservation-review flag contradicts loss measurements.'}
}
function Read-ForgePreparationJson([string]$Path,[int]$MaxBytes=2097152) {
    $item=Get-Item -LiteralPath $Path -Force
    if($item-isnot[IO.FileInfo]-or$item.Length-le0-or$item.Length-gt$MaxBytes-or($item.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Preparation JSON is missing, oversized or redirected.'}
    $bytes=[IO.File]::ReadAllBytes($Path);if($bytes.Length-le0-or$bytes.Length-gt$MaxBytes){throw 'Preparation JSON changed size while reading; no import.'}
    return (ConvertFrom-ForgeJsonObjectStrict ((New-Object Text.UTF8Encoding($false,$true)).GetString($bytes).TrimStart([char]0xFEFF)))
}
function Get-ForgePreparationConfig {
    $p=Join-Path (Split-Path $script:ModuleRoot -Parent) 'Data\Forge.PreparationProvider.json'
    $info=Get-Item -LiteralPath $p -Force;if($info-isnot[IO.FileInfo]-or$info.Length-le0-or$info.Length-gt64KB-or($info.Attributes-band[IO.FileAttributes]::ReparsePoint)){throw 'Preparation configuration is unavailable, oversized or redirected.'}
    $cfg=Read-ForgePreparationJson $p 65536;Assert-ForgePreparationConfigDocument $cfg
    foreach($f in $cfg.files){if(!(Test-Path -LiteralPath $f.path -PathType Leaf)-or(Get-FileSha256Hex $f.path)-cne$f.sha256){throw 'Installed preparation component changed; no processing or cached import allowed.'}}
    return $cfg
}
function Get-ForgePreparationCachePath($Cfg,$Context) {
    $key=Get-ForgeBriefSha256 ([ordered]@{context=$Context;worker=$Cfg.worker_sha256;model=$Cfg.model_sha256})
    return Join-Path (Join-Path $Cfg.root 'cache-index') ($key+'.json')
}
function Assert-ForgePreparationResult($Result,$Cfg,$Context,[string]$RunPath) {
    if((Get-PropertyValue $Result 'automatic_retry')-isnot[bool]-or$Result.automatic_retry){throw 'Preparation result must forbid automatic retry.'};Assert-ForgePreparationChecks $Result
    if(Test-Path -LiteralPath (Join-Path $RunPath 'cancel.request')){throw 'Preparation cancelled; result is not importable.'}
    if($Result.schema-cne'forge.preparation_result.v1'-or$Result.status-cne'completed_for_review'-or$Result.device-cne'cpu'-or$Result.owner_approved-isnot[bool]-or$Result.owner_approved-or$Result.print_ready-isnot[bool]-or$Result.print_ready){throw ('Preparation did not produce an advisory candidate: '+[string](Get-PropertyValue $Result 'error'))}
    if((ConvertTo-ForgeBriefCanonicalJson $Result.context)-cne(ConvertTo-ForgeBriefCanonicalJson $Context)-or$Result.source_sha256-cne$Context.asset_sha256-or$Result.model_sha256-cne$Cfg.model_sha256){throw 'Preparation result lineage changed.'}
    $output=[IO.Path]::GetFullPath([string]$Result.output_path);$expected=Join-Path $RunPath 'prepared.png'
    if($output-cne$expected-or!(Test-Path -LiteralPath $output -PathType Leaf)-or(Get-FileSha256Hex $output)-cne$Result.output_sha256){throw 'Prepared file is missing or has changed.'}
}
function Test-ForgePreparationImportable($Result) {
    try{Assert-ForgePreparationChecks $Result}catch{return $false}
    $c=$Result.checks
    return ($c.nonempty-and$c.transparent_border-and$c.rgb_preserved-and$c.dimensions_preserved-and!$Result.artwork_preservation_review_required-and[double]$c.interior_pixel_retention-ge0.995-and[double]$c.contrasting_pixel_retention-ge0.9)
}
function Show-ForgePreparationResult($Result) {
    try{Assert-ForgePreparationChecks $Result}catch{$script:PreparationResult=$null;$PreparationImportButton.IsEnabled=$false;$PreparationStatus.Text='Preparation report invalid; import blocked: '+$_.Exception.Message;return}
    $script:PreparationResult=$Result
    $PreparationImportButton.IsEnabled=Test-ForgePreparationImportable $Result
    $PreparationStatus.Text=('BiRefNet: candidate only. Interior retention: '+$Result.checks.interior_pixel_retention+'; edge-inclusive retention: '+$Result.checks.contrasting_pixel_retention+'; border clear: '+$Result.checks.transparent_border+"`n"+$Result.output_path+"`nOriginal RGB and size preserved. Edge pixels are excluded from the interior metric: inspect edges, halo, missing parts and colour. No acceptance or print-ready approval.")
    if(!$PreparationImportButton.IsEnabled){$PreparationStatus.Text+="`nIMPORT BLOCKED: empty/opaque edges or possible artwork loss. Do not use this mask as the final artwork."}
}
function Start-ForgePreparation {
    if($null-ne$script:PreparationProcess-and!$script:PreparationProcess.HasExited){return}
    try{
        $selected=Get-ForgeVisionSelectedContext;$cfg=Get-ForgePreparationConfig;$context=$selected.context
        $cache=Get-ForgePreparationCachePath $cfg $context
        if(Test-Path -LiteralPath $cache){try{$pointer=Read-ForgePreparationJson $cache 4096;$run=[IO.Path]::GetFullPath([string]$pointer.run);if(!$run.StartsWith((Join-Path $cfg.root 'runs')+'\',[StringComparison]::OrdinalIgnoreCase)){throw 'Invalid cache root'};$result=Read-ForgePreparationJson (Join-Path $run 'result.json');Assert-ForgePreparationResult $result $cfg $context $run;$script:PreparationRun=$run;$script:PreparationContext=$context;Show-ForgePreparationResult $result;return}catch{Move-Item -LiteralPath $cache -Destination ($cache+'.invalid-'+[guid]::NewGuid().ToString('N'))}}
        $run=Join-Path (Join-Path $cfg.root 'runs') ('run-'+[guid]::NewGuid().ToString('N'));Ensure-Dir $run
        $request=[ordered]@{schema='forge.preparation_request.v1';context=$context;source_path=[string]$selected.artwork.local_file_path;source_sha256=$context.asset_sha256;owner_approved=$false;print_ready=$false}
        [IO.File]::WriteAllText((Join-Path $run 'request.json'),($request|ConvertTo-Json -Depth 40),(New-Object Text.UTF8Encoding($false)))
        $script:PreparationContext=$context;$script:PreparationRun=$run;$script:PreparationResult=$null;$script:PreparationStarted=[DateTime]::UtcNow
        $script:PreparationProcess=Start-Process -FilePath $cfg.python -ArgumentList @(('"'+$cfg.worker+'"'),'--request',('"'+(Join-Path $run 'request.json')+'"')) -WindowStyle Hidden -RedirectStandardOutput (Join-Path $run 'worker.log') -RedirectStandardError (Join-Path $run 'worker-errors.log') -PassThru
        $PreparationStartButton.IsEnabled=$false;$PreparationCancelButton.IsEnabled=$true;$PreparationImportButton.IsEnabled=$false;$PreparationStatus.Text='BiRefNet prepares a separate alpha candidate on CPU (2 threads). Source is unchanged.'
    }catch{$PreparationStatus.Text=$_.Exception.Message}
}
function Cancel-ForgePreparation {
    if($script:PreparationRun){[IO.File]::WriteAllText((Join-Path $script:PreparationRun 'cancel.request'),'cancel')}
    $p=$script:PreparationProcess;if($null-ne$p-and!$p.HasExited){try{$p.Kill()}catch{}}
    $script:PreparationProcess=$null;$script:PreparationResult=$null
    $PreparationStartButton.IsEnabled=$true;$PreparationCancelButton.IsEnabled=$false;$PreparationImportButton.IsEnabled=$false;$PreparationStatus.Text='Preparation cancelled. No derivative imported; source and approval unchanged. Explicit retry is available.'
}
function Update-ForgePreparation {
    $p=$script:PreparationProcess;if($null-eq$p){return}
    if(!$p.HasExited){if(([DateTime]::UtcNow-$script:PreparationStarted).TotalSeconds-gt600){Cancel-ForgePreparation;$PreparationStatus.Text='Preparation timed out; no import. Explicit retry is available.'};return}
    $script:PreparationProcess=$null;$PreparationStartButton.IsEnabled=$true;$PreparationCancelButton.IsEnabled=$false
    try{
        $selected=Get-ForgeVisionSelectedContext
        if((ConvertTo-ForgeBriefCanonicalJson $selected.context)-cne(ConvertTo-ForgeBriefCanonicalJson $script:PreparationContext)){throw 'Selection, source or approval changed; candidate discarded.'}
        $cfg=Get-ForgePreparationConfig;$result=Read-ForgePreparationJson (Join-Path $script:PreparationRun 'result.json')
        Assert-ForgePreparationResult $result $cfg $selected.context $script:PreparationRun
        $cache=Get-ForgePreparationCachePath $cfg $selected.context;Ensure-Dir (Split-Path $cache -Parent)
        [IO.File]::WriteAllText($cache,(@{run=$script:PreparationRun}|ConvertTo-Json),(New-Object Text.UTF8Encoding($false)))
        Show-ForgePreparationResult $result
    }catch{$script:PreparationResult=$null;$PreparationImportButton.IsEnabled=$false;$PreparationStatus.Text=('Preparation not imported: '+$_.Exception.Message)}
}
function Import-ForgePreparedCandidate {
    try{
        $selected=Get-ForgeVisionSelectedContext;$cfg=Get-ForgePreparationConfig
        Assert-ForgePreparationResult $script:PreparationResult $cfg $selected.context $script:PreparationRun
        if(!(Test-ForgePreparationImportable $script:PreparationResult)){throw 'Possible artwork loss or invalid alpha; import blocked.'}
        $m=Get-ForgePngMetadata ([IO.File]::ReadAllBytes($selected.artwork.local_file_path))
        $test=Test-ForgePrintPngBytes ([IO.File]::ReadAllBytes($script:PreparationResult.output_path)) $m.width $m.height
        if(!$test.ok){throw 'Derivative failed independent PNG/alpha validation.'}
        $provenance=[pscustomobject]@{provider_model='BiRefNet';preparation_source_sha256=$selected.context.asset_sha256;preparation_source_variant_id=$selected.context.variant_id;preparation_source_generation_request_id=[string](Get-PropertyValue $selected.artwork 'generation_request_id');preparation_result_path=(Join-Path $script:PreparationRun 'result.json');preparation_model_sha256=$cfg.model_sha256}
        $null=Add-LocalArtworkFromPath $script:PreparationResult.output_path ([IO.Path]::GetFileName($script:PreparationRun)) 'local_birefnet_preparation' $selected.context.concept_revision_id $selected.context.revision_hash $script:PreparationResult.output_sha256 $provenance
        Refresh-LocalArtworkUi;$PreparationStatus.Text='Candidate imported for review only. Exact acceptance, print quality, sRGB interpretation and rights checks remain required.'
    }catch{$PreparationStatus.Text=('Candidate not imported: '+$_.Exception.Message)}
}
function Initialize-ForgePreparationUI {
    $script:PreparationProcess=$null;$script:PreparationRun='';$script:PreparationContext=$null;$script:PreparationResult=$null
    $PreparationStartButton.Add_Click({Start-ForgePreparation});$PreparationCancelButton.Add_Click({Cancel-ForgePreparation});$PreparationImportButton.Add_Click({Import-ForgePreparedCandidate})
    $script:PreparationTimer=New-Object Windows.Threading.DispatcherTimer;$script:PreparationTimer.Interval=[TimeSpan]::FromMilliseconds(500);$script:PreparationTimer.Add_Tick({Update-ForgePreparation});$script:PreparationTimer.Start()
    $Window.Add_Closed({$script:PreparationTimer.Stop();if($null-ne$script:PreparationProcess){Cancel-ForgePreparation}})
    $VariantList.Add_SelectionChanged({if($null-ne$script:PreparationProcess){Cancel-ForgePreparation}else{$script:PreparationResult=$null;$PreparationImportButton.IsEnabled=$false;$PreparationStatus.Text='Выберите исходный PNG. Кандидат требует проверки краёв, цвета и точной acceptance.'}})
}
