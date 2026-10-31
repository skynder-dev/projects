. (Join-Path $PSScriptRoot 'Forge.GenerationCapability.ps1')
# Merch Forge · generation spool retention/quota maintenance
function Get-GenerationSpoolPolicy {
    try{$reg=Get-Content -LiteralPath $script:GenerationProvidersPath -Raw -Encoding UTF8|ConvertFrom-Json;$p=Get-PropertyValue $reg 'spool_policy';if($null-ne$p){return $p}}catch{}
    return [pscustomobject]@{max_asset_bytes=2147483648;imported_asset_retention_days=30;minimum_asset_retention_days=7;delete_unimported_assets=$false;delete_ambiguous_assets=$false}
}
function Test-GenerationAssetBackedByLocalCore([string]$Sha) {
    if($Sha-notmatch'^[0-9a-f]{64}$'){return $false};try{$s=Read-LocalCoreState}catch{return $false};foreach($c in @($s.concepts)){foreach($a in @((Get-PropertyValue $c 'artwork'))){if(([string](Get-PropertyValue $a 'asset_sha256')).ToLowerInvariant()-eq$Sha){$p=[string](Get-PropertyValue $a 'local_file_path');if((Test-ForgeAuthorityPathWithinRoot $p $script:LocalCoreArtworkRoot) -and (Test-Path -LiteralPath $p -PathType Leaf)){try{if((Get-FileSha256Hex $p)-eq$Sha){return $true}}catch{}}}}};return $false
}
function Test-GenerationJobGloballyImported([string]$JobId) {
    if($JobId-notmatch'^gen-[0-9a-f]{32}$'){return $false}
    $jp=Get-LocalGenerationJobPath $JobId;$ip=Get-LocalGenerationReceiptPath $JobId
    if(-not(Test-Path -LiteralPath $jp -PathType Leaf) -or -not(Test-Path -LiteralPath $ip -PathType Leaf)){return $false}
    try{$j=Get-Content -LiteralPath $jp -Raw -Encoding UTF8|ConvertFrom-Json;$i=Get-Content -LiteralPath $ip -Raw -Encoding UTF8|ConvertFrom-Json}catch{return $false}
    if([string](Get-PropertyValue $j 'job_id')-ne$JobId -or [string](Get-PropertyValue $i 'job_id')-ne$JobId){return $false}
    if(-not(Test-LocalGenerationJobJournalEnvelope $j ([IO.Path]::GetFileName($jp)))){return $false}
    $concept=[string](Get-PropertyValue $j 'concept_key');$revision=[string](Get-PropertyValue $j 'source_revision_id');$revisionHash=[string](Get-PropertyValue $j 'source_revision_hash')
    if([string]::IsNullOrWhiteSpace($concept) -or [string]::IsNullOrWhiteSpace($revision) -or $revisionHash-notmatch'^[0-9a-f]{64}$'){return $false}
    if(-not(Test-LocalGenerationReceiptSatisfied $ip $concept $revision $revisionHash)){return $false}
    $want=@(Get-PropertyValue $i 'asset_sha256');$seen=@{}
    foreach($s in $want){$k=([string]$s).ToLowerInvariant();if($k-notmatch'^[0-9a-f]{64}$' -or $seen.ContainsKey($k) -or -not(Test-GenerationAssetBackedByLocalCore $k)){return $false};$seen[$k]=$true}
    return ($seen.Count -eq $want.Count -and $seen.Count -gt 0)
}
function Invoke-GenerationSpoolMaintenance {
    throw (New-LocalGenerationUnavailableError 'spool_maintenance')
    $policy=Get-GenerationSpoolPolicy;$max=[int64](Get-PropertyValue $policy 'max_asset_bytes');$ret=[int](Get-PropertyValue $policy 'imported_asset_retention_days');$min=[int](Get-PropertyValue $policy 'minimum_asset_retention_days');if($max-lt104857600){$max=2147483648};if($ret-lt7){$ret=30};if($min-lt1){$min=7};$files=@(Get-ChildItem -LiteralPath $script:GenerationResultRoot -Filter 'gen-*.png' -File -ErrorAction SilentlyContinue|Sort-Object LastWriteTimeUtc);$total=[int64]0;foreach($sz in $files){$total+=[int64]$sz.Length};$before=$total;$deleted=@();$now=[DateTime]::UtcNow
    foreach($f in $files){$age=($now-$f.LastWriteTimeUtc).TotalDays;if($age-lt$min){continue};$m=[regex]::Match($f.Name,'^(gen-[0-9a-f]{32})-\d{2}\.png$');if(-not$m.Success){continue};$job=$m.Groups[1].Value;if(-not(Test-GenerationJobGloballyImported $job)){continue};$eligible=($age-ge$ret -or $total-gt$max);if(-not$eligible){continue};$sha=Get-FileSha256Hex $f.FullName;try{$len=$f.Length;Remove-Item -LiteralPath $f.FullName -Force;$total-=$len;$deleted+=,[pscustomobject]@{file=$f.Name;sha256=$sha;size_bytes=$len;age_days=[Math]::Round($age,1);job_id=$job}}catch{}
    }
    $mroot=Join-Path $script:GenerationRoot 'maintenance';Ensure-Dir $mroot;$report=[ordered]@{schema='forge.generation_spool_maintenance.v1';ran_at=[DateTime]::UtcNow.ToString('o');asset_bytes_before=$before;asset_bytes_after=$total;max_asset_bytes=$max;imported_asset_retention_days=$ret;minimum_asset_retention_days=$min;deleted=@($deleted);deleted_count=$deleted.Count;unimported_or_unverified_deleted=0;metadata_json_deleted=0};$path=Join-Path $mroot 'last.json';$tmp=$path+'.tmp.'+[Guid]::NewGuid().ToString('N');$utf8=New-Object Text.UTF8Encoding -ArgumentList $false;[IO.File]::WriteAllText($tmp,($report|ConvertTo-Json -Depth 20),$utf8);Move-Item -LiteralPath $tmp -Destination $path -Force;return [pscustomobject]$report
}
