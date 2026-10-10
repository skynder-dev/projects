# Merch Forge · unified startup preflight
# Runs before the Workbench. Verifies package bytes, parses all PowerShell runtime files, and loads XAML without showing the app.
param([string]$PackageRoot=$PSScriptRoot,[switch]$RunProviderPipelineSelfTest)
Set-StrictMode -Version 2.0
$ErrorActionPreference='Stop'
$script:PreflightStage='init'
function Write-PreflightLine([string]$Text){
    Write-Output $Text
    if(-not [string]::IsNullOrWhiteSpace([string]$env:MERCH_FORGE_LAUNCH_LOG)){
        try{[IO.File]::AppendAllText([string]$env:MERCH_FORGE_LAUNCH_LOG,$Text+[Environment]::NewLine,(New-Object Text.UTF8Encoding -ArgumentList $false))}catch{}
    }
}
function Stop-Preflight([int]$Code,[string]$Message){Write-PreflightLine ("PRECHECK FAIL {0} [{1}]: {2}" -f $Code,$script:PreflightStage,$Message);exit $Code}
function V($Object,[string]$Name){if($null-eq$Object){return $null};$p=$Object.PSObject.Properties[$Name];if($null-eq$p){return $null};return $p.Value}
function Normalize-PathArgument([string]$Path){
    if($null-eq$Path){return ''};$v=([string]$Path).Trim();$v=$v.Trim([char[]]@([char]34));return $v
}
function Get-CanonicalDirectory([string]$Path){
    $clean=Normalize-PathArgument $Path;if([string]::IsNullOrWhiteSpace($clean)){Stop-Preflight 79 'PackageRoot is empty.'}
    try{$item=Get-Item -LiteralPath $clean -Force -ErrorAction Stop}catch{Stop-Preflight 79 ('PackageRoot is invalid: '+$_.Exception.Message)}
    if(-not $item.PSIsContainer){Stop-Preflight 79 'PackageRoot is not a directory.'};return $item.FullName
}
function Get-FullSafePath([string]$Root,[string]$Relative){
    $rootFull=Get-CanonicalDirectory $Root;$separator=[string][IO.Path]::DirectorySeparatorChar;if(-not $rootFull.EndsWith($separator,[StringComparison]::Ordinal)){$rootFull+=$separator}
    if([IO.Path]::IsPathRooted($Relative)){Stop-Preflight 84 ('Unsafe rooted package path: '+$Relative)};$candidate=Join-Path $rootFull $Relative
    try{$item=Get-Item -LiteralPath $candidate -Force -ErrorAction Stop}catch{Stop-Preflight 85 ('Required file is missing or invalid: '+$Relative)}
    $full=$item.FullName;if(-not $full.StartsWith($rootFull,[StringComparison]::OrdinalIgnoreCase)){Stop-Preflight 84 ('Unsafe package path: '+$Relative)};return $full
}
try {
    $script:PreflightStage='integrity'
    $root=Get-CanonicalDirectory $PackageRoot;Write-PreflightLine ('PRECHECK ROOT: '+$root);$integrityPath=Join-Path $root 'integrity.json';if(-not(Test-Path -LiteralPath $integrityPath -PathType Leaf)){Stop-Preflight 80 'integrity.json is missing.'}
    try{$j=Get-Content -LiteralPath $integrityPath -Raw -Encoding UTF8|ConvertFrom-Json}catch{Stop-Preflight 81 ('integrity.json could not be parsed: '+$_.Exception.Message)}
    if([string](V $j 'hash_algorithm') -ne 'SHA-256'){Stop-Preflight 82 'Integrity algorithm is not SHA-256.'}
    $files=@(V $j 'files');if($files.Count -lt 1){Stop-Preflight 83 'Integrity file list is empty.'}
    $seen=@{};foreach($f in $files){
        $rel=([string](V $f 'path')).Trim();if([string]::IsNullOrWhiteSpace($rel) -or $seen.ContainsKey($rel.ToLowerInvariant())){Stop-Preflight 83 ('Invalid or duplicate integrity path: '+$rel)};$seen[$rel.ToLowerInvariant()]=$true
        $p=Get-FullSafePath $root $rel;if(-not(Test-Path -LiteralPath $p -PathType Leaf)){Stop-Preflight 85 ('Required file is missing: '+$rel)}
        $expected=[int64](V $f 'size_bytes');if((Get-Item -LiteralPath $p).Length -ne $expected){Stop-Preflight 86 ('Wrong size: '+$rel)}
        $actual=(Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant();$want=([string](V $f 'sha256')).ToLowerInvariant();if($actual -ne $want){Stop-Preflight 87 ('Wrong SHA-256: '+$rel)}
    }
    foreach($required in @('MerchForgeWorkbench.ps1','MerchForgePreflight.ps1','MerchForgeLauncher.cmd','Start Merch Forge.vbs','candidate_manifest.json')){if(-not $seen.ContainsKey($required.ToLowerInvariant())){Stop-Preflight 83 ('Integrity list is missing '+$required)}}
    $script:PreflightStage='powershell_parse'
    $psFiles=@();foreach($f in $files){$rel=[string](V $f 'path');if($rel.ToLowerInvariant().EndsWith('.ps1')){$psFiles+=Get-FullSafePath $root $rel}}
    if($psFiles.Count -lt 10){Stop-Preflight 44 ('PowerShell runtime file count is unexpectedly low: '+$psFiles.Count)}
    foreach($p in $psFiles){$tokens=$null;$errors=$null;[System.Management.Automation.Language.Parser]::ParseFile($p,[ref]$tokens,[ref]$errors)|Out-Null;if($null -ne $errors -and @($errors).Count -gt 0){$msg=($errors|ForEach-Object{$_.Message}) -join ' | ';Stop-Preflight 41 ((Split-Path $p -Leaf)+': '+$msg)}}
    $script:PreflightStage='wpf_assemblies'
    try{Add-Type -AssemblyName PresentationFramework;Add-Type -AssemblyName PresentationCore;Add-Type -AssemblyName WindowsBase}catch{Stop-Preflight 49 ('WPF assembly load failed: '+$_.Exception.Message)}
    $script:PreflightStage='xaml_load'
    $wb=Join-Path $root 'MerchForgeWorkbench.ps1';$raw=Get-Content -LiteralPath $wb -Raw -Encoding UTF8;$marker="[xml]`$xaml=@'";$start=$raw.IndexOf($marker,[StringComparison]::Ordinal);if($start -lt 0){Stop-Preflight 45 'Workbench XAML start marker was not found.'};$bodyStart=$raw.IndexOf("`n",$start);if($bodyStart -lt 0){Stop-Preflight 45 'Workbench XAML body is malformed.'};$bodyStart++
    $end=$raw.IndexOf("`n'@",$bodyStart,[StringComparison]::Ordinal);if($end -lt 0){Stop-Preflight 45 'Workbench XAML end marker was not found.'};$xamlText=$raw.Substring($bodyStart,$end-$bodyStart).TrimStart([char[]]@([char]13))
    try{[xml]$xml=$xamlText;$reader=New-Object System.Xml.XmlNodeReader $xml;$obj=[Windows.Markup.XamlReader]::Load($reader);if($null -eq $obj){throw 'XamlReader returned null.'}}catch{Stop-Preflight 46 ('XAML load failed: '+$_.Exception.Message)}
    if($RunProviderPipelineSelfTest){
        $script:PreflightStage='provider_pipeline_selftest'
        $self=Join-Path $root 'MerchForgeProviderPipelineSelfTest.ps1';if(-not(Test-Path -LiteralPath $self -PathType Leaf)){Stop-Preflight 47 'Provider pipeline self-test is missing.'};$integritySha=(Get-FileHash -LiteralPath $integrityPath -Algorithm SHA256).Hash.ToLowerInvariant();$cacheDir=Join-Path $env:LOCALAPPDATA 'MerchForge\preflight-cache';if(-not(Test-Path -LiteralPath $cacheDir)){New-Item -ItemType Directory -Path $cacheDir -Force|Out-Null};$cache=Join-Path $cacheDir ('provider-pipeline-'+$integritySha+'.json');$cached=$false
        if(Test-Path -LiteralPath $cache -PathType Leaf){try{$cj=Get-Content -LiteralPath $cache -Raw -Encoding UTF8|ConvertFrom-Json;$cached=([string](V $cj 'schema') -eq 'forge.provider_pipeline_preflight_cache.v1' -and [string](V $cj 'integrity_sha256') -eq $integritySha -and [string](V $cj 'status') -eq 'PASS')}catch{$cached=$false}}
        if(-not $cached){$tmp=Join-Path $env:TEMP ('MerchForge-provider-selftest-'+[Guid]::NewGuid().ToString('N')+'.json');try{$null=& $self -PackageRoot $root -OutputPath $tmp;if(-not(Test-Path -LiteralPath $tmp -PathType Leaf)){Stop-Preflight 48 'Provider pipeline self-test produced no receipt.'};$sj=Get-Content -LiteralPath $tmp -Raw -Encoding UTF8|ConvertFrom-Json;if([string](V $sj 'status') -ne 'PASS' -or [int](V $sj 'network_calls') -ne 0 -or [int](V $sj 'billable_requests') -ne 0 -or [int](V $sj 'variants_imported') -ne 2 -or [bool](V $sj 'exact_acceptance') -ne $true -or [bool](V $sj 'package_ready') -ne $false -or [bool](V $sj 'corrupt_outbox_job_blocks_generation') -ne $true -or [bool](V $sj 'valid_outbox_job_envelope_passes') -ne $true -or [bool](V $sj 'legacy_v4_outbox_envelope_compatible') -ne $true -or [bool](V $sj 'parseable_truncated_outbox_job_blocks_generation') -ne $true -or [bool](V $sj 'spool_duplicate_receipt_asset_set_fail_closed') -ne $true -or [bool](V $sj 'corrupt_attempt_counter_fail_closed') -ne $true -or [bool](V $sj 'worker_corrupt_attempt_fails_pre_dispatch') -ne $true -or [bool](V $sj 'doctor_corrupt_attempt_fail_closed') -ne $true -or [bool](V $sj 'local_core_missing_primary_recovers_lastgood') -ne $true -or [bool](V $sj 'local_core_corrupt_primary_recovers_lastgood') -ne $true -or [bool](V $sj 'local_core_structural_corruption_recovers_lastgood') -ne $true -or [bool](V $sj 'local_core_double_corruption_fails_closed') -ne $true -or [bool](V $sj 'local_core_double_corruption_preserves_originals') -ne $true -or [bool](V $sj 'local_core_v1_migration_preserved') -ne $true -or [bool](V $sj 'local_core_legacy_v2_write_upgrade_preserved') -ne $true -or [bool](V $sj 'publication_identity_collision_fail_closed') -ne $true -or [bool](V $sj 'publication_unverified_legacy_reimport_allowed') -ne $true -or [bool](V $sj 'sales_ambiguous_product_id_unlinked') -ne $true -or [bool](V $sj 'publication_marketplace_product_count_exact') -ne $true -or [bool](V $sj 'publication_receipt_runtime_revalidation') -ne $true -or [bool](V $sj 'publication_future_timestamp_fail_closed') -ne $true -or [bool](V $sj 'publication_tampered_lineage_unlinked') -ne $true -or [bool](V $sj 'publication_legacy_v3_preprint_compatible') -ne $true -or [bool](V $sj 'publication_prepackage_timestamp_fail_closed') -ne $true -or [bool](V $sj 'package_gate_content_authority_fail_closed') -ne $true -or [bool](V $sj 'publication_channel_marketplace_authority') -ne $true -or [bool](V $sj 'publication_profile_valid_at_publish_required') -ne $true -or [bool](V $sj 'publication_legacy_v3_existing_zip_compatible') -ne $true -or [bool](V $sj 'check_evidence_nonempty_ref_guard') -ne $true -or [bool](V $sj 'check_evidence_source_time_revalidated') -ne $true -or [bool](V $sj 'check_evidence_not_required_ref_guard') -ne $true -or [bool](V $sj 'policy_listing_hash_stale_fail_closed') -ne $true -or [bool](V $sj 'live_policy_listing_exact_match_guard') -ne $true -or [bool](V $sj 'policy_profile_binding_stale_fail_closed') -ne $true -or [bool](V $sj 'live_policy_profile_exact_match_guard') -ne $true -or [bool](V $sj 'first_live_shared_authority_helper') -ne $true -or [bool](V $sj 'first_live_requires_exact_job_authority') -ne $true -or [bool](V $sj 'first_live_requires_local_artwork_copy') -ne $true -or [bool](V $sj 'first_live_requires_local_artwork_provenance') -ne $true -or [bool](V $sj 'future_outbox_timestamp_fail_closed') -ne $true -or [bool](V $sj 'future_job_worker_pre_dispatch_fail_closed') -ne $true -or [bool](V $sj 'future_attempt_timestamp_fail_closed') -ne $true -or [bool](V $sj 'amazon_profile_time_order_fail_closed') -ne $true -or [bool](V $sj 'first_live_temporal_authority_fail_closed') -ne $true -or [bool](V $sj 'generation_import_requires_materialized_local_copy') -ne $true -or [bool](V $sj 'generation_import_requires_exact_local_provenance') -ne $true -or [bool](V $sj 'generation_import_requires_local_artwork_root') -ne $true){Stop-Preflight 48 'Provider pipeline self-test contract failed.'};$co=[ordered]@{schema='forge.provider_pipeline_preflight_cache.v1';integrity_sha256=$integritySha;status='PASS';tested_at=[DateTime]::UtcNow.ToString('o')};$utf8=New-Object Text.UTF8Encoding -ArgumentList $false;[IO.File]::WriteAllText($cache,($co|ConvertTo-Json -Depth 6),$utf8)}catch{Stop-Preflight 48 ('Provider pipeline self-test failed: '+$_.Exception.Message)}finally{Remove-Item -LiteralPath $tmp -Force -ErrorAction SilentlyContinue}}
    }
    $script:PreflightStage='complete'
    Write-PreflightLine ("PRECHECK PASS: {0} integrity files; {1} PowerShell files; XAML load OK." -f $files.Count,$psFiles.Count);exit 0
}catch{Stop-Preflight 99 ($_.Exception.GetType().FullName+': '+$_.Exception.Message)}
