# Merch Forge · shared generation authority validators
# Pure local validation only. No network calls and no provider dispatch.
function Get-ForgeAuthorityProperty($Object,[string]$Name) {
    if($null -eq $Object){return $null}
    $p=$Object.PSObject.Properties[$Name]
    if($null -eq $p){return $null}
    return $p.Value
}
function Get-ForgeAuthorityFileSha256([string]$Path) {
    if([string]::IsNullOrWhiteSpace($Path) -or -not(Test-Path -LiteralPath $Path -PathType Leaf)){return ''}
    return (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant()
}
function Get-ForgeAuthorityTextSha256([string]$Text) {
    $sha=[Security.Cryptography.SHA256]::Create()
    try{$bytes=[Text.Encoding]::UTF8.GetBytes([string]$Text);return ([BitConverter]::ToString($sha.ComputeHash($bytes))).Replace('-','').ToLowerInvariant()}finally{$sha.Dispose()}
}
function Test-ForgeAuthorityPathWithinRoot([string]$Path,[string]$Root) {
    if([string]::IsNullOrWhiteSpace($Path) -or [string]::IsNullOrWhiteSpace($Root)){return $false}
    try{$full=[IO.Path]::GetFullPath($Path);$rootFull=[IO.Path]::GetFullPath($Root).TrimEnd([char[]]@([IO.Path]::DirectorySeparatorChar,[IO.Path]::AltDirectorySeparatorChar));$prefix=$rootFull+[IO.Path]::DirectorySeparatorChar;return $full.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)}catch{return $false}
}
function Test-ForgeGenerationJobEnvelope($Job,[string]$LeafName='') {
    if($null -eq $Job){return $false}
    $jobId=[string](Get-ForgeAuthorityProperty $Job 'job_id')
    if([string](Get-ForgeAuthorityProperty $Job 'schema') -ne 'forge.generation_job.v4' -or $jobId -notmatch '^gen-[0-9a-f]{32}$'){return $false}
    if(-not[string]::IsNullOrWhiteSpace($LeafName) -and $LeafName -ne ($jobId+'.json')){return $false}
    try{$created=[DateTime]::Parse([string](Get-ForgeAuthorityProperty $Job 'created_at')).ToUniversalTime()}catch{return $false}
    if($created.Year -lt 2020 -or $created -gt [DateTime]::UtcNow.AddMinutes(10)){return $false}
    $kind=[string](Get-ForgeAuthorityProperty $Job 'request_kind')
    if($kind -notin @('generate','regenerate')){return $false}
    foreach($name in @('concept_key','source_revision_id','provider_key','provider_contract_version','prompt_compiler_version')){if([string]::IsNullOrWhiteSpace([string](Get-ForgeAuthorityProperty $Job $name))){return $false}}
    if([string](Get-ForgeAuthorityProperty $Job 'source_revision_hash') -notmatch '^[0-9a-fA-F]{64}$' -or
       [string](Get-ForgeAuthorityProperty $Job 'provider_registry_sha256') -notmatch '^[0-9a-fA-F]{64}$' -or
       [string](Get-ForgeAuthorityProperty $Job 'provider_config_fingerprint') -notmatch '^[0-9a-fA-F]{64}$' -or
       [string](Get-ForgeAuthorityProperty $Job 'prompt_template_sha256') -notmatch '^[0-9a-fA-F]{64}$' -or
       [string](Get-ForgeAuthorityProperty $Job 'prompt_sha256') -notmatch '^[0-9a-fA-F]{64}$'){return $false}
    if([string](Get-ForgeAuthorityProperty $Job 'prompt_compiler_version') -ne 'forge.prompt.apparel.v2'){return $false}
    $prompt=[string](Get-ForgeAuthorityProperty $Job 'prompt')
    if([string]::IsNullOrWhiteSpace($prompt) -or $prompt.Length -gt 32000 -or (Get-ForgeAuthorityTextSha256 $prompt) -ne ([string](Get-ForgeAuthorityProperty $Job 'prompt_sha256')).ToLowerInvariant()){return $false}
    $render=Get-ForgeAuthorityProperty $Job 'render'
    if($null -eq $render){return $false}
    foreach($name in @('model','size','quality','background','output_format')){if([string]::IsNullOrWhiteSpace([string](Get-ForgeAuthorityProperty $render $name))){return $false}}
    if([string](Get-ForgeAuthorityProperty $render 'size') -notmatch '^\d{3,4}x\d{3,4}$'){return $false}
    try{$count=[int](Get-ForgeAuthorityProperty $render 'output_count')}catch{return $false}
    if($count -lt 1 -or $count -gt 4){return $false}
    $names=@($Job.PSObject.Properties.Name)
    if($names -contains 'provider_profile'){if([string]::IsNullOrWhiteSpace([string](Get-ForgeAuthorityProperty $Job 'provider_profile'))){return $false}}
    if($names -contains 'owner_action_id'){if([string]::IsNullOrWhiteSpace([string](Get-ForgeAuthorityProperty $Job 'owner_action_id'))){return $false}}
    if($names -contains 'explicit_owner_action'){if([bool](Get-ForgeAuthorityProperty $Job 'explicit_owner_action') -ne $true){return $false}}
    if($names -contains 'external_submission_authorized'){if([bool](Get-ForgeAuthorityProperty $Job 'external_submission_authorized') -ne $false){return $false}}
    if($names -contains 'max_provider_requests'){try{$maxReq=[int](Get-ForgeAuthorityProperty $Job 'max_provider_requests')}catch{return $false};if($maxReq -ne 1){return $false}}
    if($names -contains 'automatic_retry'){if([bool](Get-ForgeAuthorityProperty $Job 'automatic_retry') -ne $false){return $false}}
    if($names -contains 'ambiguity_policy'){if([string](Get-ForgeAuthorityProperty $Job 'ambiguity_policy') -ne 'explicit_owner_action_required'){return $false}}
    if($names -contains 'prior_job_id'){$prior=([string](Get-ForgeAuthorityProperty $Job 'prior_job_id')).Trim();if($prior -and $prior -notmatch '^gen-[0-9a-f]{32}$'){return $false}}
    if($names -contains 'unresolved_ambiguous_ancestor_count'){try{$ancestorCount=[int](Get-ForgeAuthorityProperty $Job 'unresolved_ambiguous_ancestor_count')}catch{return $false};if($ancestorCount -lt 0){return $false}}
    if($names -contains 'daily_request_limit'){try{$limit=[int](Get-ForgeAuthorityProperty $Job 'daily_request_limit')}catch{return $false};if($limit -lt 1 -or $limit -gt 20){return $false}}
    if($names -contains 'paid_requests_today_before'){try{$used=[int](Get-ForgeAuthorityProperty $Job 'paid_requests_today_before')}catch{return $false};if($used -lt 0){return $false}}
    return $true
}
function Test-ForgeFirstLiveAuthority([string]$StateRoot,[string]$ProviderKey='openai_image_api') {
    if([string]::IsNullOrWhiteSpace($StateRoot) -or [string]::IsNullOrWhiteSpace($ProviderKey)){return $false}
    $generationRoot=Join-Path $StateRoot 'generation-v1'
    $attemptRoot=Join-Path $generationRoot 'attempts';$resultRoot=Join-Path $generationRoot 'results';$receiptRoot=Join-Path $generationRoot 'receipts';$outboxRoot=Join-Path $generationRoot 'outbox'
    $corePath=Join-Path (Join-Path $StateRoot 'local-core-v1') 'state.json'
    if(-not(Test-Path -LiteralPath $attemptRoot -PathType Container) -or -not(Test-Path -LiteralPath $corePath -PathType Leaf)){return $false}
    try{$core=Get-Content -LiteralPath $corePath -Raw -Encoding UTF8|ConvertFrom-Json}catch{return $false}
    if([string](Get-ForgeAuthorityProperty $core 'schema') -ne 'forge.local_core.v2'){return $false}
    $concepts=@(Get-ForgeAuthorityProperty $core 'concepts')
    try{$attemptFiles=@(Get-ChildItem -LiteralPath $attemptRoot -Filter '*.attempt.json' -File -ErrorAction Stop)}catch{return $false}
    foreach($f in $attemptFiles){
        try{$attempt=Get-Content -LiteralPath $f.FullName -Raw -Encoding UTF8|ConvertFrom-Json}catch{continue}
        if([string](Get-ForgeAuthorityProperty $attempt 'schema') -ne 'forge.generation_attempt.v1' -or
           [string](Get-ForgeAuthorityProperty $attempt 'provider_key') -ne $ProviderKey -or
           [bool](Get-ForgeAuthorityProperty $attempt 'internal_mock') -or
           -not [bool](Get-ForgeAuthorityProperty $attempt 'billable') -or
           [int](Get-ForgeAuthorityProperty $attempt 'provider_request_count') -ne 1 -or
           [string](Get-ForgeAuthorityProperty $attempt 'phase') -ne 'completed'){continue}
        try{$attemptStarted=[DateTime]::Parse([string](Get-ForgeAuthorityProperty $attempt 'dispatch_started_at')).ToUniversalTime();$attemptCompleted=[DateTime]::Parse([string](Get-ForgeAuthorityProperty $attempt 'completed_at')).ToUniversalTime()}catch{continue}
        if($attemptStarted -gt [DateTime]::UtcNow.AddMinutes(10) -or $attemptCompleted -gt [DateTime]::UtcNow.AddMinutes(10) -or $attemptCompleted -lt $attemptStarted){continue}
        $jobId=[string](Get-ForgeAuthorityProperty $attempt 'job_id');$resultSha=[string](Get-ForgeAuthorityProperty $attempt 'result_sha256')
        if($jobId -notmatch '^gen-[0-9a-f]{32}$' -or [IO.Path]::GetFileName($f.FullName) -ne ($jobId+'.attempt.json') -or $resultSha -notmatch '^[0-9a-f]{64}$'){continue}
        $jobPath=Join-Path $outboxRoot ($jobId+'.json');$resultPath=Join-Path $resultRoot ($jobId+'.result.json');$receiptPath=Join-Path $receiptRoot ($jobId+'.imported.json')
        if(-not(Test-Path -LiteralPath $jobPath -PathType Leaf) -or -not(Test-Path -LiteralPath $resultPath -PathType Leaf) -or -not(Test-Path -LiteralPath $receiptPath -PathType Leaf)){continue}
        $jobSha=Get-ForgeAuthorityFileSha256 $jobPath;$actualResultSha=Get-ForgeAuthorityFileSha256 $resultPath;$attemptSha=Get-ForgeAuthorityFileSha256 $f.FullName
        if($jobSha -notmatch '^[0-9a-f]{64}$' -or $actualResultSha -ne $resultSha -or $attemptSha -notmatch '^[0-9a-f]{64}$' -or [string](Get-ForgeAuthorityProperty $attempt 'job_sha256') -ne $jobSha){continue}
        try{$job=Get-Content -LiteralPath $jobPath -Raw -Encoding UTF8|ConvertFrom-Json;$result=Get-Content -LiteralPath $resultPath -Raw -Encoding UTF8|ConvertFrom-Json;$receipt=Get-Content -LiteralPath $receiptPath -Raw -Encoding UTF8|ConvertFrom-Json}catch{continue}
        if(-not(Test-ForgeGenerationJobEnvelope $job ([IO.Path]::GetFileName($jobPath)))){continue}
        if([string](Get-ForgeAuthorityProperty $job 'provider_key') -ne $ProviderKey -or [string](Get-ForgeAuthorityProperty $job 'job_id') -ne $jobId){continue}
        if([string](Get-ForgeAuthorityProperty $job 'provider_profile') -ne 'smoke' -or [int](Get-ForgeAuthorityProperty (Get-ForgeAuthorityProperty $job 'render') 'output_count') -ne 1){continue}
        if([bool](Get-ForgeAuthorityProperty $job 'explicit_owner_action') -ne $true -or [int](Get-ForgeAuthorityProperty $job 'max_provider_requests') -ne 1 -or [bool](Get-ForgeAuthorityProperty $job 'automatic_retry') -ne $false -or [bool](Get-ForgeAuthorityProperty $job 'external_submission_authorized') -ne $false){continue}
        if([int](Get-ForgeAuthorityProperty $job 'daily_request_limit') -ne 1){continue}
        if([string](Get-ForgeAuthorityProperty $result 'schema') -ne 'forge.generation_result.v4' -or [string](Get-ForgeAuthorityProperty $result 'job_id') -ne $jobId -or [string](Get-ForgeAuthorityProperty $result 'job_sha256') -ne $jobSha -or [string](Get-ForgeAuthorityProperty $result 'status') -ne 'completed' -or [string](Get-ForgeAuthorityProperty $result 'provider_key') -ne $ProviderKey -or [bool](Get-ForgeAuthorityProperty $result 'internal_mock') -or -not [bool](Get-ForgeAuthorityProperty $result 'billable') -or -not [bool](Get-ForgeAuthorityProperty $result 'network_call')){continue}
        try{$resultStarted=[DateTime]::Parse([string](Get-ForgeAuthorityProperty $result 'started_at')).ToUniversalTime();$resultCompleted=[DateTime]::Parse([string](Get-ForgeAuthorityProperty $result 'completed_at')).ToUniversalTime()}catch{continue}
        if($resultStarted -gt [DateTime]::UtcNow.AddMinutes(10) -or $resultCompleted -gt [DateTime]::UtcNow.AddMinutes(10) -or $resultCompleted -lt $resultStarted){continue}
        if([string](Get-ForgeAuthorityProperty $result 'provider_profile') -ne 'smoke' -or [string](Get-ForgeAuthorityProperty $result 'model') -ne [string](Get-ForgeAuthorityProperty (Get-ForgeAuthorityProperty $job 'render') 'model')){continue}
        if([string](Get-ForgeAuthorityProperty $attempt 'provider_profile') -ne 'smoke' -or [int](Get-ForgeAuthorityProperty $attempt 'daily_request_limit') -ne 1 -or [bool](Get-ForgeAuthorityProperty $attempt 'automatic_retry') -ne $false -or -not [bool](Get-ForgeAuthorityProperty $attempt 'network_call')){continue}
        if([string](Get-ForgeAuthorityProperty $receipt 'schema') -ne 'forge.generation_import_receipt.v4' -or [string](Get-ForgeAuthorityProperty $receipt 'job_id') -ne $jobId -or [string](Get-ForgeAuthorityProperty $receipt 'job_sha256') -ne $jobSha -or [string](Get-ForgeAuthorityProperty $receipt 'result_sha256') -ne $actualResultSha -or [string](Get-ForgeAuthorityProperty $receipt 'attempt_sha256') -ne $attemptSha -or [string](Get-ForgeAuthorityProperty $receipt 'provider_key') -ne $ProviderKey){continue}
        try{$receiptImported=[DateTime]::Parse([string](Get-ForgeAuthorityProperty $receipt 'imported_at')).ToUniversalTime()}catch{continue}
        if($receiptImported -gt [DateTime]::UtcNow.AddMinutes(10) -or $receiptImported -lt $resultCompleted){continue}
        $lineageOk=$true
        foreach($name in @('provider_contract_version','provider_registry_sha256','provider_config_fingerprint','prompt_compiler_version','prompt_template_sha256','prompt_sha256')){
            $want=[string](Get-ForgeAuthorityProperty $receipt $name)
            if([string]::IsNullOrWhiteSpace($want) -or $want -ne [string](Get-ForgeAuthorityProperty $job $name) -or $want -ne [string](Get-ForgeAuthorityProperty $result $name) -or $want -ne [string](Get-ForgeAuthorityProperty $attempt $name)){$lineageOk=$false;break}
        }
        if(-not $lineageOk){continue}
        foreach($name in @('provider_profile','provider_request_id')){$want=[string](Get-ForgeAuthorityProperty $receipt $name);if($want -ne [string](Get-ForgeAuthorityProperty $result $name) -or $want -ne [string](Get-ForgeAuthorityProperty $attempt $name)){$lineageOk=$false;break}}
        if(-not $lineageOk){continue}
        if([string](Get-ForgeAuthorityProperty $receipt 'provider_model') -ne [string](Get-ForgeAuthorityProperty $result 'model') -or [string](Get-ForgeAuthorityProperty $receipt 'provider_model') -ne [string](Get-ForgeAuthorityProperty $attempt 'model')){continue}
        $conceptKey=[string](Get-ForgeAuthorityProperty $job 'concept_key');$revisionId=[string](Get-ForgeAuthorityProperty $job 'source_revision_id');$revisionHash=[string](Get-ForgeAuthorityProperty $job 'source_revision_hash')
        if([string](Get-ForgeAuthorityProperty $result 'concept_key') -ne $conceptKey -or [string](Get-ForgeAuthorityProperty $result 'source_revision_id') -ne $revisionId -or [string](Get-ForgeAuthorityProperty $result 'source_revision_hash') -ne $revisionHash){continue}
        $concept=$null;foreach($c in $concepts){if([string](Get-ForgeAuthorityProperty $c 'concept_key') -eq $conceptKey){$concept=$c;break}}
        if($null -eq $concept){continue}
        $resultAssets=@(Get-ForgeAuthorityProperty $result 'assets');$receiptAssets=@(Get-ForgeAuthorityProperty $receipt 'asset_sha256')
        if($resultAssets.Count -lt 1 -or $receiptAssets.Count -ne $resultAssets.Count){continue}
        $resultSet=@{};$assetOk=$true
        foreach($ra in $resultAssets){$sha=([string](Get-ForgeAuthorityProperty $ra 'sha256')).ToLowerInvariant();if($sha -notmatch '^[0-9a-f]{64}$' -or $resultSet.ContainsKey($sha)){$assetOk=$false;break};$resultSet[$sha]=$true}
        if(-not $assetOk){continue}
        $seen=@{}
        foreach($rawSha in $receiptAssets){
            $sha=([string]$rawSha).ToLowerInvariant();if($sha -notmatch '^[0-9a-f]{64}$' -or $seen.ContainsKey($sha) -or -not $resultSet.ContainsKey($sha)){$assetOk=$false;break};$seen[$sha]=$true
            $art=$null;foreach($v in @(Get-ForgeAuthorityProperty $concept 'artwork')){
                if([string](Get-ForgeAuthorityProperty $v 'concept_revision_id') -ne $revisionId -or ([string](Get-ForgeAuthorityProperty $v 'asset_sha256')).ToLowerInvariant() -ne $sha){continue}
                if([string](Get-ForgeAuthorityProperty $v 'source_revision_hash') -ne $revisionHash -or [string](Get-ForgeAuthorityProperty $v 'generation_request_id') -ne $jobId -or [string](Get-ForgeAuthorityProperty $v 'provider_key') -ne $ProviderKey -or [string](Get-ForgeAuthorityProperty $v 'generation_method') -ne 'local_provider_worker'){continue}
                if([string](Get-ForgeAuthorityProperty $v 'provider_profile') -ne [string](Get-ForgeAuthorityProperty $receipt 'provider_profile') -or
                   [string](Get-ForgeAuthorityProperty $v 'provider_model') -ne [string](Get-ForgeAuthorityProperty $receipt 'provider_model') -or
                   [string](Get-ForgeAuthorityProperty $v 'provider_contract_version') -ne [string](Get-ForgeAuthorityProperty $receipt 'provider_contract_version') -or
                   [string](Get-ForgeAuthorityProperty $v 'provider_registry_sha256') -ne [string](Get-ForgeAuthorityProperty $receipt 'provider_registry_sha256') -or
                   [string](Get-ForgeAuthorityProperty $v 'provider_config_fingerprint') -ne [string](Get-ForgeAuthorityProperty $receipt 'provider_config_fingerprint') -or
                   [string](Get-ForgeAuthorityProperty $v 'prompt_compiler_version') -ne [string](Get-ForgeAuthorityProperty $receipt 'prompt_compiler_version') -or
                   [string](Get-ForgeAuthorityProperty $v 'prompt_template_sha256') -ne [string](Get-ForgeAuthorityProperty $receipt 'prompt_template_sha256') -or
                   [string](Get-ForgeAuthorityProperty $v 'provider_request_id') -ne [string](Get-ForgeAuthorityProperty $receipt 'provider_request_id') -or
                   [string](Get-ForgeAuthorityProperty $v 'generation_result_sha256') -ne $actualResultSha -or
                   [string](Get-ForgeAuthorityProperty $v 'generation_attempt_sha256') -ne $attemptSha -or
                   [string](Get-ForgeAuthorityProperty $v 'prompt_sha256') -ne [string](Get-ForgeAuthorityProperty $receipt 'prompt_sha256')){continue}
                $art=$v;break
            }
            if($null -eq $art){$assetOk=$false;break}
            $localPath=[string](Get-ForgeAuthorityProperty $art 'local_file_path');$artRoot=Join-Path (Join-Path $StateRoot 'local-core-v1') 'artwork';if(-not(Test-ForgeAuthorityPathWithinRoot $localPath $artRoot) -or -not(Test-Path -LiteralPath $localPath -PathType Leaf) -or (Get-ForgeAuthorityFileSha256 $localPath) -ne $sha){$assetOk=$false;break}
        }
        if($assetOk -and $seen.Count -eq $resultSet.Count){return $true}
    }
    return $false
}
