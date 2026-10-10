# Merch Forge · Generation provider registry / local credential boundary
# Provider availability and owner-local configuration only. External dispatch is performed by the separate worker.
. (Join-Path $PSScriptRoot 'Forge.GenerationAuthority.ps1')
function Initialize-GenerationProviderRegistry {
    if(-not(Test-Path -LiteralPath $script:GenerationProvidersPath -PathType Leaf)){throw 'Generation provider contract is missing.'}
    $contract=Get-Content -LiteralPath $script:GenerationProvidersPath -Raw -Encoding UTF8|ConvertFrom-Json
    if([string](Get-PropertyValue $contract 'schema') -ne 'forge.generation_providers.v6'){throw 'Unsupported generation provider contract.'}
    $seen=@{};$manual=$null
    foreach($p in @($contract.providers)){
        $key=([string](Get-PropertyValue $p 'provider_key')).Trim();if([string]::IsNullOrWhiteSpace($key)){throw 'Generation provider key is missing.'}
        if($seen.ContainsKey($key)){throw ('Duplicate generation provider key: '+$key)};$seen[$key]=$true
        if($key -eq 'manual_artwork_bridge' -and [bool](Get-PropertyValue $p 'available')){$manual=$p}
    }
    if($null -eq $manual){throw 'Manual artwork bridge is unavailable.'}
    $script:GenerationProviderRegistry=$contract
    $script:LocalGenerationProviderMode='manual_artwork_bridge'
    $null=Get-GenerationProviderRuntimeConfig
    return $contract
}
function Get-GenerationProviderDefinition([string]$ProviderKey) {
    foreach($p in @((Get-PropertyValue $script:GenerationProviderRegistry 'providers'))){if([string](Get-PropertyValue $p 'provider_key') -eq $ProviderKey){return $p}}
    return $null
}
function Get-GenerationProviderProfile($Definition,[string]$ProfileKey) {
    if($null -eq $Definition){return $null}
    foreach($p in @((Get-PropertyValue $Definition 'profiles'))){if([string](Get-PropertyValue $p 'profile_key') -eq $ProfileKey){return $p}}
    return $null
}
function Get-GenerationProviderTextSha256([string]$Text) {
    $sha=[Security.Cryptography.SHA256]::Create();try{$bytes=[Text.Encoding]::UTF8.GetBytes($Text);return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
}
function Get-GenerationProviderConfigFingerprint($Cfg) {
    if($null -eq $Cfg){return ''}
    $canonical=(@(
      [string](Get-PropertyValue $Cfg 'provider_key'),[string](Get-PropertyValue $Cfg 'profile_key'),[string](Get-PropertyValue $Cfg 'model'),[string](Get-PropertyValue $Cfg 'size'),
      [string](Get-PropertyValue $Cfg 'quality'),[string](Get-PropertyValue $Cfg 'background'),[string](Get-PropertyValue $Cfg 'output_format'),([string]([int](Get-PropertyValue $Cfg 'output_count'))),([string]([int](Get-PropertyValue $Cfg 'daily_request_limit')))
    ) -join '|');return Get-GenerationProviderTextSha256 $canonical
}
function ConvertTo-GenerationProviderConfigV3($Cfg) {
    if($null -eq $Cfg){return $null}
    $schema=[string](Get-PropertyValue $Cfg 'schema');if($schema -eq 'forge.local_generation_provider_config.v3'){return $Cfg}
    if($schema -notin @('forge.local_generation_provider_config.v1','forge.local_generation_provider_config.v2')){throw 'Unsupported local provider config.'}
    $key=[string](Get-PropertyValue $Cfg 'provider_key');$def=Get-GenerationProviderDefinition $key;$profileKey=[string](Get-PropertyValue $Cfg 'profile_key');if([string]::IsNullOrWhiteSpace($profileKey)){$profileKey='legacy_custom'}
    $daily=if($schema -eq 'forge.local_generation_provider_config.v2'){[int](Get-PropertyValue $Cfg 'daily_request_limit')}else{5};if($daily-lt1){$daily=5}
    $model=[string](Get-PropertyValue $Cfg 'model');$size=[string](Get-PropertyValue $Cfg 'size');$quality=[string](Get-PropertyValue $Cfg 'quality');$background=[string](Get-PropertyValue $Cfg 'background');$fmt=[string](Get-PropertyValue $Cfg 'output_format');$count=[int](Get-PropertyValue $Cfg 'output_count')
    if($null -ne $def -and $profileKey -in @('smoke','draft','final')){$profile=Get-GenerationProviderProfile $def $profileKey;if($null -ne $profile){$model=[string](Get-PropertyValue $profile 'model');$size=[string](Get-PropertyValue $profile 'size');$quality=[string](Get-PropertyValue $profile 'quality');$background=[string](Get-PropertyValue $profile 'background');$fmt=[string](Get-PropertyValue $profile 'output_format');$count=[int](Get-PropertyValue $profile 'output_count')}}
    return [pscustomobject]@{schema='forge.local_generation_provider_config.v3';provider_key=$key;enabled=[bool](Get-PropertyValue $Cfg 'enabled');profile_key=$profileKey;model=$model;size=$size;quality=$quality;background=$background;output_format=$fmt;output_count=$count;daily_request_limit=$daily;updated_at=[string](Get-PropertyValue $Cfg 'updated_at');migrated_from=$schema}
}
function Get-GenerationProviderRuntimeConfig {
    $fallback=[pscustomobject]@{schema='forge.local_generation_provider_config.v3';provider_key='manual_artwork_bridge';enabled=$false;profile_key='';model='';size='';quality='';background='';output_format='';output_count=0;daily_request_limit=5;updated_at=''}
    if(-not(Test-Path -LiteralPath $script:ProviderConfigPath -PathType Leaf)){$script:GenerationProviderConfig=$fallback;return $fallback}
    try {
        $raw=Get-Content -LiteralPath $script:ProviderConfigPath -Raw -Encoding UTF8|ConvertFrom-Json;$cfg=ConvertTo-GenerationProviderConfigV3 $raw
        $def=Get-GenerationProviderDefinition ([string](Get-PropertyValue $cfg 'provider_key'));if($null -eq $def){throw 'Configured generation provider is unknown.'}
        $script:GenerationProviderConfig=$cfg;return $cfg
    } catch {Write-AppLog 'WARN' ('Generation provider config ignored: '+$_.Exception.Message);$script:GenerationProviderConfig=$fallback;return $fallback}
}
function Get-OpenAIProviderKey {
    $envKey=([string]$env:OPENAI_API_KEY).Trim();if(-not [string]::IsNullOrWhiteSpace($envKey)){return $envKey}
    if(-not(Test-Path -LiteralPath $script:ProviderSecretPath -PathType Leaf)){return ''}
    try {
        $enc=(Get-Content -LiteralPath $script:ProviderSecretPath -Raw -Encoding UTF8).Trim();if([string]::IsNullOrWhiteSpace($enc)){return ''}
        $secure=$enc|ConvertTo-SecureString;$ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        try{return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)}finally{[Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr)}
    } catch {Write-AppLog 'WARN' ('Generation credential could not be decrypted for this Windows user: '+$_.Exception.Message);return ''}
}
function Get-GenerationProviderDailyAttemptCount([string]$ProviderKey,[DateTime]$UtcDate=[DateTime]::UtcNow.Date) {
    if([string]::IsNullOrWhiteSpace($ProviderKey) -or -not(Test-Path -LiteralPath $script:GenerationAttemptRoot)){return 0}
    try{$files=@(Get-ChildItem -LiteralPath $script:GenerationAttemptRoot -Filter '*.attempt.json' -File -ErrorAction Stop)}catch{throw ('Provider attempt journal directory cannot be read safely. Paid generation is blocked: '+$_.Exception.Message)}
    $count=0
    foreach($f in $files){
        try{$a=Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8|ConvertFrom-Json}catch{throw ('Provider attempt journal is unreadable. Paid generation is blocked: '+$f.Name)}
        $schema=[string](Get-PropertyValue $a 'schema');$jobId=[string](Get-PropertyValue $a 'job_id');$provider=[string](Get-PropertyValue $a 'provider_key');$requestCount=[int](Get-PropertyValue $a 'provider_request_count')
        if($schema -ne 'forge.generation_attempt.v1' -or $jobId -notmatch '^gen-[0-9a-f]{32}$' -or [IO.Path]::GetFileName($f.FullName) -ne ($jobId+'.attempt.json') -or [string]::IsNullOrWhiteSpace($provider) -or $requestCount -ne 1){throw ('Provider attempt journal is malformed. Paid generation is blocked: '+$f.Name)}
        try{$dt=[DateTime]::Parse([string](Get-PropertyValue $a 'dispatch_started_at')).ToUniversalTime()}catch{throw ('Provider attempt journal has an invalid dispatch timestamp. Paid generation is blocked: '+$f.Name)}
        if($dt -gt [DateTime]::UtcNow.AddMinutes(10)){throw ('Provider attempt journal has a future dispatch timestamp. Paid generation is blocked: '+$f.Name)}
        if($provider -eq $ProviderKey -and $dt.Date -eq $UtcDate.Date){$count++}
    }
    return $count
}

function Test-GenerationProviderFirstLiveCompleted([string]$ProviderKey='openai_image_api') {
    $stateRoot=Split-Path -Parent $script:GenerationRoot
    return (Test-ForgeFirstLiveAuthority $stateRoot $ProviderKey)
}
function Get-GenerationProviderLocalReadiness {
    $cfg=Get-GenerationProviderRuntimeConfig;$key=[string](Get-PropertyValue $cfg 'provider_key');$firstLive=Test-GenerationProviderFirstLiveCompleted 'openai_image_api'
    if(-not [bool](Get-PropertyValue $cfg 'enabled')){return [pscustomobject]@{ready=$false;code='disabled';provider_key=$key;credential_present=$false;paid_requests_today=0;daily_request_limit=[int](Get-PropertyValue $cfg 'daily_request_limit');first_live_completed=$firstLive;first_live_guard_active=(-not $firstLive)}}
    $def=Get-GenerationProviderDefinition $key;if($null -eq $def){return [pscustomobject]@{ready=$false;code='unknown_provider';provider_key=$key;credential_present=$false;paid_requests_today=0;daily_request_limit=0;first_live_completed=$firstLive;first_live_guard_active=(-not $firstLive)}}
    if(-not [bool](Get-PropertyValue $def 'available') -or -not [bool](Get-PropertyValue $def 'production_image_generation')){return [pscustomobject]@{ready=$false;code='not_production_capable';provider_key=$key;credential_present=$false;paid_requests_today=0;daily_request_limit=0;first_live_completed=$firstLive;first_live_guard_active=(-not $firstLive)}}
    try{$null=Assert-GenerationProviderConfigSafe}catch{return [pscustomobject]@{ready=$false;code='unsafe_config';provider_key=$key;credential_present=$false;detail=$_.Exception.Message;paid_requests_today=0;daily_request_limit=[int](Get-PropertyValue $cfg 'daily_request_limit');first_live_completed=$firstLive;first_live_guard_active=(-not $firstLive)}}
    $limit=[int](Get-PropertyValue $cfg 'daily_request_limit');try{$used=Get-GenerationProviderDailyAttemptCount $key}catch{return [pscustomobject]@{ready=$false;code='attempt_journal_unreadable';provider_key=$key;credential_present=(-not [string]::IsNullOrWhiteSpace((Get-OpenAIProviderKey)));detail=$_.Exception.Message;paid_requests_today=$null;daily_request_limit=$limit;first_live_completed=$firstLive;first_live_guard_active=(-not $firstLive)}}
    if($used -ge $limit){return [pscustomobject]@{ready=$false;code='daily_request_limit_reached';provider_key=$key;credential_present=(-not [string]::IsNullOrWhiteSpace((Get-OpenAIProviderKey)));paid_requests_today=$used;daily_request_limit=$limit;first_live_completed=$firstLive;first_live_guard_active=(-not $firstLive)}}
    if($key -eq 'openai_image_api'){$present=-not [string]::IsNullOrWhiteSpace((Get-OpenAIProviderKey));if(-not $present){return [pscustomobject]@{ready=$false;code='credential_missing';provider_key=$key;credential_present=$false;paid_requests_today=$used;daily_request_limit=$limit;first_live_completed=$firstLive;first_live_guard_active=(-not $firstLive)}};return [pscustomobject]@{ready=$true;code='ready_local';provider_key=$key;credential_present=$true;paid_requests_today=$used;daily_request_limit=$limit;profile_key=[string](Get-PropertyValue $cfg 'profile_key');model=[string](Get-PropertyValue $cfg 'model');size=[string](Get-PropertyValue $cfg 'size');quality=[string](Get-PropertyValue $cfg 'quality');output_count=[int](Get-PropertyValue $cfg 'output_count');first_live_completed=$firstLive;first_live_guard_active=(-not $firstLive)}}
    return [pscustomobject]@{ready=$false;code='unsupported_worker_provider';provider_key=$key;credential_present=$false;paid_requests_today=$used;daily_request_limit=$limit;first_live_completed=$firstLive;first_live_guard_active=(-not $firstLive)}
}
function Test-LocalProductionProviderReady { return [bool](Get-PropertyValue (Get-GenerationProviderLocalReadiness) 'ready') }
function Get-ActiveGenerationProviderKey { if(Test-LocalProductionProviderReady){return [string](Get-PropertyValue (Get-GenerationProviderRuntimeConfig) 'provider_key')};return 'manual_artwork_bridge' }
function Get-GenerationProviderCapabilities {
    $cfg=Get-GenerationProviderRuntimeConfig;$r=Get-GenerationProviderLocalReadiness
    return [pscustomobject]@{manual_artwork_bridge=$true;external_generation_configured=[bool](Get-PropertyValue $r 'ready');external_dispatch_authorized=[bool](Get-PropertyValue $r 'ready');active_provider=if([bool](Get-PropertyValue $r 'ready')){[string](Get-PropertyValue $cfg 'provider_key')}else{'manual_artwork_bridge'};config_provider=[string](Get-PropertyValue $cfg 'provider_key');profile_key=[string](Get-PropertyValue $cfg 'profile_key');paid_requests_today=[int](Get-PropertyValue $r 'paid_requests_today');daily_request_limit=[int](Get-PropertyValue $r 'daily_request_limit');first_live_completed=[bool](Get-PropertyValue $r 'first_live_completed');first_live_guard_active=[bool](Get-PropertyValue $r 'first_live_guard_active')}
}
function Get-GenerationDispatchPreview {
    $cfg=Get-GenerationProviderRuntimeConfig;$r=Get-GenerationProviderLocalReadiness
    return [pscustomobject]@{ready=[bool](Get-PropertyValue $r 'ready');readiness_code=[string](Get-PropertyValue $r 'code');provider_key=[string](Get-PropertyValue $cfg 'provider_key');profile_key=[string](Get-PropertyValue $cfg 'profile_key');model=[string](Get-PropertyValue $cfg 'model');size=[string](Get-PropertyValue $cfg 'size');quality=[string](Get-PropertyValue $cfg 'quality');background=[string](Get-PropertyValue $cfg 'background');output_format=[string](Get-PropertyValue $cfg 'output_format');output_count=[int](Get-PropertyValue $cfg 'output_count');paid_requests_today=[int](Get-PropertyValue $r 'paid_requests_today');daily_request_limit=[int](Get-PropertyValue $r 'daily_request_limit');pre_request_dollar_cost='not_deterministic';max_provider_requests_for_job=1;automatic_retry=$false;first_live_completed=[bool](Get-PropertyValue $r 'first_live_completed');first_live_guard_active=[bool](Get-PropertyValue $r 'first_live_guard_active')}
}
function Assert-GenerationProviderConfigSafe {
    $cfg=Get-GenerationProviderRuntimeConfig;if(-not [bool](Get-PropertyValue $cfg 'enabled')){return $true};$key=[string](Get-PropertyValue $cfg 'provider_key');$def=Get-GenerationProviderDefinition $key;if($null -eq $def){throw 'Configured generation provider is unavailable.'}
    if($key -eq 'openai_image_api'){
        $endpoint=[string](Get-PropertyValue $def 'endpoint');if($endpoint -ne 'https://api.openai.com/v1/images/generations'){throw 'OpenAI image endpoint is outside the pinned provider contract.'}
        $profileKey=[string](Get-PropertyValue $cfg 'profile_key');if([string]::IsNullOrWhiteSpace($profileKey)){throw 'Generation profile is missing.'};$profile=$null;if($profileKey -ne 'legacy_custom'){$profile=Get-GenerationProviderProfile $def $profileKey;if($null -eq $profile){throw 'Generation profile is outside the provider contract.'}}
        $model=[string](Get-PropertyValue $cfg 'model');if([string]::IsNullOrWhiteSpace($model)){$model=[string](Get-PropertyValue $def 'model')};if(-(@((Get-PropertyValue $def 'allowed_models')) -contains $model)){throw 'Configured OpenAI image model is outside the provider allowlist.'}
        $q=[string](Get-PropertyValue $cfg 'quality');if([string]::IsNullOrWhiteSpace($q)){$q=[string](Get-PropertyValue $def 'quality')};if(-(@((Get-PropertyValue $def 'allowed_quality')) -contains $q)){throw 'Configured image quality is invalid.'}
        $fmt=[string](Get-PropertyValue $cfg 'output_format');if([string]::IsNullOrWhiteSpace($fmt)){$fmt=[string](Get-PropertyValue $def 'output_format')};if(-(@((Get-PropertyValue $def 'allowed_output_format')) -contains $fmt)){throw 'Configured image format is invalid.'}
        $background=[string](Get-PropertyValue $cfg 'background');if([string]::IsNullOrWhiteSpace($background)){$background=[string](Get-PropertyValue $def 'background')};if($background -ne 'transparent' -or $fmt -ne 'png'){throw 'Configured provider must use transparent PNG output.'}
        $size=[string](Get-PropertyValue $cfg 'size');if([string]::IsNullOrWhiteSpace($size)){$size=[string](Get-PropertyValue $def 'size')};$sm=[regex]::Match($size,'^(\d{3,4})x(\d{3,4})$');if(-not $sm.Success){throw 'Configured image size is invalid.'};$width=[int]$sm.Groups[1].Value;$height=[int]$sm.Groups[2].Value;$pixels=[int64]$width*[int64]$height;$ratio=[double]$width/[double]$height;if(($width%16)-ne0 -or ($height%16)-ne0 -or $width-gt3840 -or $height-gt3840 -or $pixels-lt655360 -or $pixels-gt8294400 -or $ratio-lt(1.0/3.0) -or $ratio-gt3.0){throw 'Configured image size is outside the provider contract.'}
        $count=[int](Get-PropertyValue $cfg 'output_count');if($count-lt1 -or $count-gt4){throw 'Configured output count must be between 1 and 4.'};if($null -ne $profile){if($model -ne [string](Get-PropertyValue $profile 'model') -or $size -ne [string](Get-PropertyValue $profile 'size') -or $q -ne [string](Get-PropertyValue $profile 'quality') -or $background -ne [string](Get-PropertyValue $profile 'background') -or $fmt -ne [string](Get-PropertyValue $profile 'output_format') -or $count -ne [int](Get-PropertyValue $profile 'output_count')){throw 'Configured render values do not match the selected provider profile.'}}
        $limit=[int](Get-PropertyValue $cfg 'daily_request_limit');if($limit-lt1 -or $limit-gt20){throw 'Daily paid-request limit must be between 1 and 20.'};$firstLive=Test-GenerationProviderFirstLiveCompleted 'openai_image_api';if(-not $firstLive){if($profileKey -ne 'smoke' -or $count -ne 1 -or $limit -ne 1){throw 'First live generation safety is active. Use Smoke profile with exactly 1 output and daily request limit 1 until one exact billable live result is successfully imported.'}}
    }
    return $true
}
